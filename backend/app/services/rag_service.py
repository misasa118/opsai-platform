# backend/app/services/rag_service.py
# 1. 用户问问题
# 2. 把问题变成向量
# 3. 去 Chroma 向量库找最相似的文档片段
# 4. 把“问题 + 查到的资料”一起发给大模型
# 5. 大模型流式输出回答
# 6. 最后附上资料来源
from typing import AsyncGenerator
from .knowledge_service import get_collection, embedding_model # 拿向量库 向量模型
from .llm_service import client, MODEL # 大模型（GPT/Claude/Gemini）
import json

# 函数定义：RAG 流式对话 query：用户问题 history：历史聊天记录 top_k=4：最多找 4 条相关资料
async def rag_stream_chat(
    query: str,
    history: list[dict],
    mode: str = 'general',
    top_k: int = 4,
) -> AsyncGenerator[str, None]:
    '''
    RAG 增强的流式对话：
    1. 检索相关文档片段
    2. 组装增强 Prompt
    3. 流式生成回答
    4. 附上来源引用
    '''
    # ── 步骤1：检索相关文档 把用户的问题 变成向量 去向量库里搜索最相似的内容
    collection = get_collection()
    sources = []
    context = ''

    if collection.count() > 0:
        query_embedding = embedding_model.embed_query(query)
        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=min(top_k, collection.count()),
            include=['documents', 'metadatas', 'distances']
        )

        # 只用相似度足够高的结果（距离 < 0.5 表示余弦相似度 > 0.5） 过滤：只保留 “足够相关” 的资料 距离越小 = 越相关
        docs = results['documents'][0]
        metas = results['metadatas'][0]
        distances = results['distances'][0]

        relevant = [
            (doc, meta)
            for doc, meta, dist in zip(docs, metas, distances)
            if dist < 0.5
        ]

        if relevant:
            context_parts = []
            seen_sources = set()
            for doc, meta in relevant:
                src = meta.get('source', '未知文档')
                page = meta.get('page', '')
                context_parts.append(f'[来源：{src}]\n{doc}')
                source_key = f'{src}（第{page+1}页）' if page != '' else src
                seen_sources.add(source_key)

            context = '\n\n---\n\n'.join(context_parts)
            sources = list(seen_sources)

    # ── 步骤2：组装 Prompt 告诉 AI：先看资料，再回答！
    if context:
        system_content = f'''你是专业的 Oracle/OCI 运维专家。
请基于以下参考资料回答问题。如果参考资料不足以完整回答，
可以补充你的专业知识，但要明确区分哪些来自文档，哪些是补充。

参考资料：
{context}'''
    else:
        system_content = '你是专业的 Oracle/OCI 运维专家，用中文给出可操作的建议。'

    messages = [{'role': 'system', 'content': system_content}]
    messages += history
    messages.append({'role': 'user', 'content': query})

    # ── 步骤3：流式输出回答 一点点把文字返回给前端
    stream = await client.chat.completions.create(
        model=MODEL,
        messages=messages,
        stream=True,
        temperature=0.3,
    )

    async for chunk in stream:
        delta = chunk.choices[0].delta.content
        if delta is not None:
            yield delta

    # ── 步骤4：附上来源引用（用特殊格式，前端解析用）
    if sources:
        sources_json = json.dumps(sources, ensure_ascii=False)
        yield f'\n\n__SOURCES__{sources_json}__END_SOURCES__'