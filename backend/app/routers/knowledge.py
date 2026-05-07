# backend/app/routers/knowledge.py
# 这是 FastAPI 后端接口文件，专门给前端提供：
# 上传文件、查状态、列知识库、删文件 四个功能！
# 你可以把它理解成：
# 前端和知识库之间的 “大门”
# knowledge.py（接口） ←→ knowledge_service.py（真正干活）
# knowledge.py：负责接收前端请求
# knowledge_service.py：负责真正读取 PDF、切块、向量化、存库
# 接口只管收发，服务只管干活
from fastapi import APIRouter, UploadFile, File, BackgroundTasks, HTTPException
from pydantic import BaseModel
from typing import Optional
import uuid, shutil
from ..services.knowledge_service import (
    ingest_document, get_file_status, get_collection,
    UPLOAD_DIR, FileStatus
)

# 所有知识库相关的接口，都放这里
router = APIRouter(prefix='/api/v1/knowledge', tags=['knowledge']) 

class UploadResponse(BaseModel):
    file_id: str
    filename: str
    status: str
    message: str

class StatusResponse(BaseModel):
    file_id: str
    status: str
    filename: Optional[str] = None
    chunk_count: Optional[int] = None
    error: Optional[str] = None

# 上传文件 → /api/v1/knowledge/upload 前端传 PDF → 后端保存 → 后台悄悄处理成向量库 不卡界面，立刻返回 file_id
@router.post('/upload', response_model=UploadResponse)
async def upload_file(
    file: UploadFile = File(...),
    background_tasks: BackgroundTasks = BackgroundTasks(),
):
    '''
    上传文档并在后台异步向量化。
    立即返回 file_id，前端用此 ID 轮询处理状态。
    '''
    # 验证文件格式
    allowed_types = {'.pdf', '.txt', '.md'}
    suffix = '.' + file.filename.split('.')[-1].lower() if '.' in file.filename else ''
    if suffix not in allowed_types:
        raise HTTPException(400, f'不支持的文件格式，仅支持: {allowed_types}')

    # 限制文件大小（10MB）
    MAX_SIZE = 10 * 1024 * 1024
    content = await file.read()
    if len(content) > MAX_SIZE:
        raise HTTPException(400, f'文件过大，最大支持 10MB')

    # 生成唯一文件名并保存
    file_id = str(uuid.uuid4())
    safe_filename = f'{file_id}_{file.filename}'
    file_path = str(UPLOAD_DIR / safe_filename)

    with open(file_path, 'wb') as f:
        f.write(content)

    # 后台异步处理（不阻塞当前请求）
    background_tasks.add_task(
        ingest_document, file_id, file_path, file.filename
    )

    return UploadResponse(
        file_id=file_id,
        filename=file.filename,
        status=FileStatus.PROCESSING,
        message='文件上传成功，正在后台处理中',
    )

# 查询处理状态 → /api/v1/knowledge/status/{file_id} 前端每 2 秒问一次：“处理完了吗？”返回：processing /ready/error
@router.get('/status/{file_id}', response_model=StatusResponse)
async def get_status(file_id: str):
    '''查询文件处理状态，前端每 2 秒轮询一次'''
    status_info = get_file_status(file_id)
    if not status_info:
        raise HTTPException(404, f'file_id {file_id} 不存在')
    return StatusResponse(file_id=file_id, **status_info)

# 列出知识库所有文件 → /api/v1/knowledge/list 显示：总块数/上传了哪些文件/每个文件切了几块
@router.get('/list')
async def list_documents():
    '''列出知识库中已有的所有文档'''
    collection = get_collection()
    count = collection.count()
    # 获取所有唯一的文件来源
    if count == 0:
        return {'total_chunks': 0, 'documents': []}

    results = collection.get(include=['metadatas'])
    sources = {}
    for meta in results['metadatas']:
        src = meta.get('source', '未知')
        if src not in sources:
            sources[src] = {'filename': src, 'chunks': 0}
        sources[src]['chunks'] += 1

    return {
        'total_chunks': count,
        'documents': list(sources.values())
    }

# 删除某个文档 → /api/v1/knowledge/document/{文件名} 把某个文件从向量库彻底删掉
@router.delete('/document/{filename}')
async def delete_document(filename: str):
    '''从知识库删除指定文档的所有向量'''
    collection = get_collection()
    # 查找该文件的所有 chunk
    results = collection.get(
        where={'source': filename},
        include=['metadatas']
    )
    if not results['ids']:
        raise HTTPException(404, f'文档 {filename} 不存在')

    collection.delete(ids=results['ids'])
    return {'deleted': filename, 'chunks_removed': len(results['ids'])}