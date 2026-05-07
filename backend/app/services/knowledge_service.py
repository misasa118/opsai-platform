# backend/app/services/knowledge_service.py
import os, uuid, asyncio
from pathlib import Path
from typing import Optional
from enum import Enum
import chromadb # 连接向量库
from langchain_community.document_loaders import PyPDFLoader, TextLoader # 读取 PDF
from langchain_text_splitters import RecursiveCharacterTextSplitter # 文本切块
from langchain_google_genai import GoogleGenerativeAIEmbeddings # 转向量
from ..config import settings # 读取配置（GOOGLE_API_KEY）

# 文件状态（上传中 / 处理中 / 完成 / 失败）
class FileStatus(str, Enum):
    UPLOADING  = 'uploading'
    PROCESSING = 'processing'
    READY      = 'ready'
    ERROR      = 'error'

# 内存中存储文件处理状态（生产环境应存数据库）
# key: file_id, value: {status, filename, chunk_count, error}
_file_status: dict[str, dict] = {}

# ── 目录配置
# 上传文件存在这里
UPLOAD_DIR = Path('uploads')
# 向量库存在这里
CHROMA_DIR = Path('chroma_db')
UPLOAD_DIR.mkdir(exist_ok=True)
CHROMA_DIR.mkdir(exist_ok=True)

# ── ChromaDB 客户端（单例） 向量库客户端 本地持久化向量库，重启服务不丢失数据。
chroma_client = chromadb.PersistentClient(path=str(CHROMA_DIR))
COLLECTION_NAME = 'opsai_knowledge'

# ── Embedding 模型
embedding_model = GoogleGenerativeAIEmbeddings(
    model='models/gemini-embedding-001',
    google_api_key=settings.GOOGLE_API_KEY
)

def get_collection():
    '''获取或创建向量库集合'''
    return chroma_client.get_or_create_collection(
        name=COLLECTION_NAME,
        metadata={'hnsw:space': 'cosine'}  # 使用余弦相似度
    )

def get_file_status(file_id: str) -> Optional[dict]:
    return _file_status.get(file_id)

def set_file_status(file_id: str, status: FileStatus, **kwargs):
    _file_status[file_id] = {'status': status, **kwargs}

# 最核心函数：ingest_document
async def ingest_document(file_id: str, file_path: str, filename: str):
    '''
    后台任务：加载文档 → 切块 → Embedding → 存入 ChromaDB
    这个函数由 BackgroundTasks 异步调用，不阻塞 HTTP 响应
    '''
    set_file_status(file_id, FileStatus.PROCESSING, filename=filename)
    try:
        # 步骤1：根据文件类型选择加载器 步骤 1：加载文件（PDF / TXT） 读取文件内容。
        if filename.lower().endswith('.pdf'):
            loader = PyPDFLoader(file_path)
        else:
            loader = TextLoader(file_path, encoding='utf-8')

        docs = loader.load()

        # 步骤2：切块
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=500,
            chunk_overlap=50,
            separators=['\n\n', '\n', '。', '；', '，', ' ', ''],
        )
        chunks = splitter.split_documents(docs)

        if not chunks:
            raise ValueError('文档内容为空，无法处理')

        # 步骤3：Embedding（批量处理）把所有块转向量
        texts = [c.page_content for c in chunks]
        # Google Embedding API 有速率限制，分批处理
        batch_size = 20
        all_embeddings = []
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i+batch_size]
            batch_embeddings = embedding_model.embed_documents(batch)
            all_embeddings.extend(batch_embeddings)
            await asyncio.sleep(0.5)  # 避免触发速率限制

        # 步骤4：存入 ChromaDB 存入向量库
        collection = get_collection()
        ids = [f'{file_id}_{i}' for i in range(len(chunks))]
        metadatas = [
            {
                'source': filename,
                'file_id': file_id,
                'chunk_index': i,
                'page': c.metadata.get('page', 0),
            }
            for i, c in enumerate(chunks)
        ]

        collection.add(
            ids=ids,
            documents=texts,
            embeddings=all_embeddings,
            metadatas=metadatas,
        )
        # 步骤 5：更新状态为 “处理完成”
        set_file_status(
            file_id, FileStatus.READY,
            filename=filename,
            chunk_count=len(chunks)
        )
        print(f'文件 {filename} 处理完成，共 {len(chunks)} 个片段')

    except Exception as e:
        set_file_status(file_id, FileStatus.ERROR, filename=filename, error=str(e))
        print(f'文件 {filename} 处理失败: {e}')