# opsai-platform/backend/app/routers/chat.py
# FastAPI 的路由层（routers/chat.py）
# 对外暴露可访问的 API 接口（流式 / 同步 / 健康检查），把前端请求转发给 AI 服务层（llm_service.py），并按规范返回结果（流式用 SSE 协议，同步用 JSON）。
# 前端请求 → /api/v1/chat/stream → FastAPI 解析为 ChatRequest 模型 → 转字典 → 调用 llm_service.stream_chat → 接收 AI 流式 token → 封装成 SSE 格式 → 实时返回给前端
# 前端请求 → /api/v1/chat/sync → FastAPI 解析为 ChatRequest 模型 → 转字典 → 调用 llm_service.complete → 接收完整回答 → 封装成 ChatSyncResponse → 一次性返回给前端
# 这段代码定义了四个接口：
# 1./stream      流式，测试用，不存数据库，支持 RAG
# 2./stream/save 流式，前端实际使用，存数据库 + 支持 RAG（Week 4 升级）
# 3./sync        非流式，curl 测试用
# 4./health      健康检查，不调用 AI

from fastapi import APIRouter, Depends # 导入 FastAPI 的 APIRouter 用于创建路由器，Depends 用于依赖注入
from fastapi.responses import StreamingResponse # 导入 StreamingResponse 用于返回流式响应
from sqlalchemy.ext.asyncio import AsyncSession # 导入 SQLAlchemy 的异步会话类，用于执行数据库操作
from ..models.chat import ChatRequest, ChatSyncResponse # 从 models.chat 模块导入 ChatRequest 和 ChatSyncResponse 模型，这些模型定义了 API 的请求和响应格式
from ..services.llm_service import stream_chat, complete # 从 services.llm_service 模块导入 stream_chat 和 complete 函数，这些函数用于处理聊天请求并生成回答
from ..services.chat_history_service import create_session, add_message, get_session_history # 从当前包的 services.chat_history_service 模块导入 create_session、add_message 和 get_session_history 函数，用于管理聊天历史记录，包括创建会话、添加消息和获取历史消息
from ..database import get_db # 从当前包的 database 模块导入 get_db 函数，用于获取数据库会话对象
import json # 导入 json 模块用于处理 JSON 数据的编码和解码
import uuid # 导入 uuid 模块用于处理 UUID 类型的主键
from datetime import datetime # 导入 datetime 模块用于处理日期和时间

# 初始化路由：前缀 /api/v1/chat，标签 💬 对话（文档里分类用）
# APIRouter：FastAPI 的路由拆分工具（把聊天相关接口集中管理，避免主文件杂乱）；
# prefix='/api/v1/chat'：所有接口的基础路径（比如流式接口最终路径是 /api/v1/chat/stream）；
# tags=['💬 对话']：在 /docs 页面给接口分类，更易读。
router = APIRouter(prefix='/api/v1/chat', tags=['💬 对话'])


# ── 流式接口（测试用，不存数据库）
# 直接调用 sse_generator，支持 RAG 模式，但不保存对话历史到数据库
# 适合开发调试，不适合生产使用
@router.post('/stream', summary='流式聊天（SSE，测试用不存数据库）')
async def chat_stream(request: ChatRequest):
    '''
    Server-Sent Events 流式聊天接口（测试用）。
    每个 data 块格式：{"content": "...", "done": false}
    结束时发送：{"content": "", "done": true}
    '''
    messages = [m.model_dump() for m in request.messages] # 将请求中的消息列表转换为字典列表，使用 Pydantic 模型的 model_dump 方法将每个 Message 对象转换为一个普通的字典
    return StreamingResponse(
        sse_generator(messages, request.mode, request.use_rag), # 直接调用 sse_generator，传入 use_rag 参数
        media_type='text/event-stream', # 告诉前端这是 SSE 流式响应，不要超时
        headers={
            'Cache-Control': 'no-cache, no-transform',
            'X-Accel-Buffering': 'no',  # 告诉 Nginx 不要缓冲
            'Connection': 'keep-alive',
        }
    )


# ── 流式接口（完整版：RAG + 数据库保存，前端实际使用这个）
# 这是一个能记住你所有聊天记录、自动保存到 PostgreSQL、支持历史会话列表、
# 带流式输出、支持 RAG 知识库检索的 AI 聊天接口！
# Week 4 升级：把 RAG 逻辑整合进来，同时保留数据库保存功能
@router.post('/stream/save', summary='流式聊天（SSE + RAG + 存数据库）')
async def chat_stream_with_save(
    request: ChatRequest,
    db: AsyncSession = Depends(get_db) # 通过 Depends(get_db) 实现依赖注入，提供数据库会话对象
):
    # 获取或创建 session
    session_id = uuid.UUID(request.session_id) if request.session_id else None # 从请求中获取 session_id，如果请求中提供了 session_id，就将它转换为 uuid.UUID 类型，否则就设置为 None
    if not session_id: # 没有会话 ID → 自动创建新会话
        session = await create_session(db, request.mode) # 创建一个新的聊天会话对象，传入数据库会话对象和请求中的模式参数
        session_id = session.id # 将这个新的会话的 UUID 主键赋值给 session_id 变量

    # 保存用户消息到数据库
    user_content = request.messages[-1].content # 获取用户发送的最后一条消息的内容
    await add_message(db, session_id, 'user', user_content) # 将用户的消息保存到数据库中

    # 读取历史聊天记录（给 AI 做上下文）
    history = await get_session_history(db, session_id) # 获取这个会话的历史消息
    messages = [{'role': m.role, 'content': m.content} for m in history] # 将历史消息转换成字典列表，传递给 LLM

    # 收集 AI 完整回复（用于保存到数据库）
    full_reply = [] # 定义一个列表来收集 AI 回复的完整内容，流式结束后拼接保存

    async def event_generator():
        try:
            # ── RAG 或普通模式选择
            # 前端传 use_rag=true → 调用 rag_service → 先检索知识库再回答
            # 前端传 use_rag=false → 调用普通 stream_chat → 不带资料直接回答
            if request.use_rag:
                from ..services.rag_service import rag_stream_chat
                # RAG 模式：用最后一条消息作为检索查询，其余作为历史上下文
                query = messages[-1]['content'] if messages else user_content
                history_msgs = messages[:-1] if len(messages) > 1 else []
                generator = rag_stream_chat(query, history_msgs, request.mode)
            else:
                # 普通模式：直接调用 LLM，不检索知识库
                generator = stream_chat(messages, request.mode)

            full_content = '' # 累积所有 token，用于检测来源引用标记

            async for token in generator:
                full_content += token

                if '__SOURCES__' in full_content and '__END_SOURCES__' in full_content:
                    # 检测到来源引用标记，解析并单独发送，不作为聊天内容
                    # 这样前端能区分「AI 写的来源说明」和「实际来源数据」，用独立 UI 组件渲染
                    sources_raw = full_content.split('__SOURCES__')[1].split('__END_SOURCES__')[0]
                    sources = json.loads(sources_raw)
                    payload = json.dumps({'sources': sources, 'done': False}, ensure_ascii=False)
                    yield f'data: {payload}\n\n'
                    break # 来源引用是最后发送的，收到后结束循环

                elif '__SOURCES__' not in full_content:
                    # 正常 token，追加到 full_reply 并实时推送给前端
                    full_reply.append(token)
                    payload = json.dumps(
                        {'content': token, 'done': False, 'session_id': str(session_id)},
                        ensure_ascii=False
                    )
                    yield f'data: {payload}\n\n' # SSE 格式：data: {...}\n\n

            # AI 回答结束 → 保存完整回复到数据库（不含来源标记）
            ai_content = ''.join(full_reply) # 将所有 token 拼接成完整回答
            await add_message(db, session_id, 'assistant', ai_content) # 保存 AI 回复到数据库
            await db.commit() # 提交数据库事务，确保用户消息和 AI 回复都持久化

            # 发送结束信号，前端收到 done:true 后停止等待
            yield f'data: {json.dumps({"content": "", "done": True, "session_id": str(session_id)})}\n\n'

        except Exception as e:
            await db.rollback() # 回滚数据库事务，避免不完整的记录残留
            yield f'data: {json.dumps({"error": str(e), "done": True})}\n\n' # 把错误信息发给前端，前端显示错误提示

    return StreamingResponse(
        event_generator(),
        media_type='text/event-stream', # 告诉前端这是 SSE 流式响应，前端会持续接收数据而不超时
        headers={
            'Cache-Control': 'no-cache, no-transform',
            'X-Accel-Buffering': 'no', # 告诉 Nginx 不要缓冲，确保数据实时推送
            'Connection': 'keep-alive',
        }
    )


# ── 同步接口（测试 / curl 用）
@router.post('/sync', response_model=ChatSyncResponse, summary='同步聊天（测试用）')
async def chat_sync(request: ChatRequest):
    messages = [m.model_dump() for m in request.messages]
    content = await complete(messages, request.mode)
    return ChatSyncResponse(
        content=content,
        session_id=request.session_id,
        mode=request.mode
    )


# ── 健康检查（用于 Docker 和负载均衡）
@router.get('/health', summary='服务健康检查')
async def health():
    return {'status': 'ok', 'timestamp': datetime.utcnow().isoformat()}


# ── 获取历史会话接口
@router.get('/sessions', summary='获取历史会话列表')
async def get_sessions(db: AsyncSession = Depends(get_db)): # 通过 Depends(get_db) 实现依赖注入，提供数据库会话对象
    from sqlalchemy import select # 导入 SQLAlchemy 的 select 函数，用于构建查询语句
    from ..models.db_models import ChatSession # 从当前包的 models.db_models 模块导入 ChatSession ORM 模型
    result = await db.execute(
        select(ChatSession).order_by(ChatSession.updated_at.desc()).limit(20) # 查询最近更新的 20 个会话，按更新时间降序排列
    )
    sessions = result.scalars().all() # 将查询结果转换成 ChatSession 对象列表
    return [
        {'id': str(s.id), 'title': s.title, 'mode': s.mode, 'updated_at': s.updated_at.isoformat()}
        for s in sessions
    ] # 将会话列表转换成字典列表返回给前端


# ── sse_generator（/stream 测试接口专用）
# sse_generator 是流式输出生成器，前端会一直连着它，实时接收文字。
# 前端传 use_rag=true → 调用 rag_service → 先检索知识库再带资料回答
# 前端传 use_rag=false → 调用普通聊天 → 不带资料直接回答
# 注意：这个生成器只给 /stream 测试接口用，不保存数据库
# /stream/save 有自己的 event_generator，整合了数据库保存逻辑
async def sse_generator(messages: list, mode: str, use_rag: bool = False):
    print(f"=== sse_generator called: use_rag={use_rag} ===") # 调试用，确认 use_rag 参数是否正确传入
    try:
        if use_rag:
            from ..services.rag_service import rag_stream_chat
            query = messages[-1]['content'] # 用最后一条用户消息作为检索查询
            history = messages[:-1]  # 其余消息作为历史上下文
            generator = rag_stream_chat(query, history, mode)
        else:
            generator = stream_chat(messages, mode) # 普通模式：直接调用 LLM

        async for token in generator:
            if '__SOURCES__' in token:
                break # 碰到来源标记就停，测试接口不处理来源引用
            payload = json.dumps({'content': token, 'done': False}, ensure_ascii=False)
            yield f'data: {payload}\n\n'

        yield f'data: {json.dumps({"content": "", "done": True})}\n\n' # 发送结束信号

    except Exception as e:
        yield f'data: {json.dumps({"error": str(e), "done": True})}\n\n'