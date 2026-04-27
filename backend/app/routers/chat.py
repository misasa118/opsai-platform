# opsai-platform/backend/app/routers/chat.py
# FastAPI 的路由层（routers/chat.py）
# 对外暴露可访问的 API 接口（流式 / 同步 / 健康检查），把前端请求转发给 AI 服务层（llm_service.py），并按规范返回结果（流式用 SSE 协议，同步用 JSON）。
# 前端请求 → /api/v1/chat/stream → FastAPI 解析为 ChatRequest 模型 → 转字典 → 调用 llm_service.stream_chat → 接收 AI 流式 token → 封装成 SSE 格式 → 实时返回给前端
# 前端请求 → /api/v1/chat/sync → FastAPI 解析为 ChatRequest 模型 → 转字典 → 调用 llm_service.complete → 接收完整回答 → 封装成 ChatSyncResponse → 一次性返回给前端
# 这段代码定义了三个接口。
# 1./stream定义为流式，对应llm_service的stream_chat函数，实际场景就是和用户聊天，一个一个字的输出。需调用AI服务。/stream 接口用了 SSE（Server-Sent Events）协议（media_type='text/event-stream'），不是普通的流式响应 —— 这是前端处理 “实时聊天” 的标准方案，比普通流式更适配前端（能自动处理断连重连、识别结束信号），能让用户边看回答边等待完整结果，提升体验。
# 2./sync定义为非流式，对应llm_service的complete函数，测试的时候用。需调用AI服务。
# 3./health，用于健康检查这是新的函数。不需要调用AI服务。

from fastapi import APIRouter, HTTPException # 导入 FastAPI 的 APIRouter 用于创建路由器，HTTPException 用于抛出 HTTP 错误
from fastapi.responses import StreamingResponse # 导入 StreamingResponse 用于返回流式响应
from ..models.chat import ChatRequest, ChatSyncResponse # 从 models.chat 模块导入 ChatRequest 和 ChatSyncResponse 模型，这些模型定义了 API 的请求和响应格式
from ..services.llm_service import stream_chat, complete # 从 services.llm_service 模块导入 stream_chat 和 complete 函数，这些函数用于处理聊天请求并生成回答
import json # 导入 json 模块用于处理 JSON 数据的编码和解码
from datetime import datetime # 导入 datetime 模块用于处理日期和时间

# 初始化路由：前缀 /api/v1/chat，标签 💬 对话（文档里分类用）
# APIRouter：FastAPI 的路由拆分工具（把聊天相关接口集中管理，避免主文件杂乱）；
# prefix='/api/v1/chat'：所有接口的基础路径（比如流式接口最终路径是 /api/v1/chat/stream）；
# tags=['💬 对话']：在 /docs 页面给接口分类，更易读。
router = APIRouter(prefix='/api/v1/chat', tags=['💬 对话']) 

# ── 流式接口（前端用这个）核心：前端实际使用的接口，支持流式输出，适合聊天场景，能让用户边看回答边等待完整结果。
# SSE 协议：text/event-stream 是前端 “实时接收流式数据” 的标准协议（比普通流式更适配前端，能处理断连 / 重连）；
@router.post('/stream', summary='流式聊天（SSE）') # 定义一个 POST 路由，路径是 /stream，摘要是“流式聊天（SSE）”，这个接口将使用 Server-Sent Events (SSE) 技术实现流式聊天功能
async def chat_stream(request: ChatRequest): # 定义一个异步函数来处理聊天请求，参数 request 的类型是 ChatRequest，这个函数将接收前端发送的聊天请求数据，并返回一个流式响应
    '''
    Server-Sent Events 流式聊天接口。
    每个 data 块格式：{"content": "...", "done": false}
    结束时发送：{"content": "", "done": true}
    '''
    async def event_generator(): # 定义一个异步生成器函数，用于生成 SSE 事件流，函数内部使用 try-except 块来捕获可能发生的异常
        try:
            messages = [m.model_dump() for m in request.messages] # 将请求中的消息列表转换为字典列表，使用 Pydantic 模型的 model_dump 方法将每个 Message 对象转换为一个普通的字典，这样就可以传递给 llm_service 进行处理了
            async for chunk in stream_chat(messages, request.mode): # 调用 stream_chat 函数，传入消息列表和模式参数，使用 async for 循环逐个接收生成的文本增量，每次接收到一个文本增量时，就将它封装成一个 JSON 对象，并通过 yield 语句发送给前端
                payload = json.dumps({'content': chunk, 'done': False}, ensure_ascii=False) # 将当前的文本增量封装成一个 JSON 对象，包含 content 字段和 done 字段，content 字段是当前的文本增量，done 字段表示是否已经完成生成，使用 json.dumps 将字典转换为 JSON 字符串，ensure_ascii=False 参数确保中文字符能够正确显示
                yield f'data: {payload}\n\n' # 通过 yield 语句发送一个 SSE 事件，事件的数据部分是上面生成的 JSON 字符串，按照 SSE 的格式，每个事件以 data: 开头，后面跟着数据内容，最后以两个换行符结束，这样前端就能正确解析每个事件了
            # 流结束
            yield f'data: {json.dumps({"content": "", "done": True})}\n\n' # 当流式生成完成后，发送一个特殊的事件，表示生成已经完成了，这个事件的 content 字段是一个空字符串，done 字段是 True，前端接收到这个事件后就知道可以结束等待了
        except Exception as e: # 如果在处理过程中发生了任何异常，都会被捕获到这里，异常对象被命名为 e
            error_payload = json.dumps({'error': str(e), 'done': True}) # 将异常信息封装成一个 JSON 对象，包含 error 字段和 done 字段，error 字段是异常的字符串表示，done 字段表示生成已经完成了，前端接收到这个事件后就知道发生了错误，并且可以结束等待了
            yield f'data: {error_payload}\n\n' 

    return StreamingResponse( 
        event_generator(),
        media_type='text/event-stream', # 设置响应的媒体类型为 text/event-stream，表示这是一个 SSE 流式响应，这样前端就能正确处理这个流了 告诉前端这不是http请求，是一个SSE流式响应，前端会自动处理这个流，能边看边等待完整结果，提升体验。不要超时。
        headers={
            'Cache-Control': 'no-cache, no-transform',
            'X-Accel-Buffering': 'no',  # 告诉 Nginx 不要缓冲
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

# 升级 routers/chat.py — 加入数据库持久化
# 这是一个能记住你所有聊天记录、自动保存到 PostgreSQL、支持历史会话列表、带流式输出的 AI 聊天接口！
from fastapi import APIRouter, Depends # 导入 Depends 用于依赖注入，提供数据库会话对象
from fastapi.responses import StreamingResponse # 导入 StreamingResponse 用于返回流式响应
from sqlalchemy.ext.asyncio import AsyncSession # 导入 SQLAlchemy 的异步会话类，用于执行数据库操作
from ..database import get_db # 从当前包的 database 模块导入 get_db 函数，用于获取数据库会话对象
from ..models.chat import ChatRequest # 从当前包的 models.chat 模块导入 ChatRequest 模型，用于解析聊天请求数据
from ..services.llm_service import stream_chat # 从当前包的 services.llm_service 模块导入 stream_chat 函数，用于处理聊天请求并生成回答
from ..services.chat_history_service import create_session, add_message, get_session_history # 从当前包的 services.chat_history_service 模块导入 create_session、add_message 和 get_session_history 函数，用于管理聊天历史记录，包括创建会话、添加消息和获取历史消息
import json, uuid # 导入 json 模块用于处理 JSON 数据的编码和解码，导入 uuid 模块用于处理 UUID 类型的主键

# 接收前端请求 拿到用户问题ChatRequest 拿到数据库会话（db）
@router.post('/stream/save') # 定义一个 POST 路由，路径是 /stream，这个接口将使用 Server-Sent Events (SSE) 技术实现流式聊天功能，并且在处理聊天请求的同时，将聊天记录保存到数据库中
async def chat_stream_with_save(request: ChatRequest, db: AsyncSession = Depends(get_db)): # 定义一个异步函数来处理聊天请求，参数 request 的类型是 ChatRequest，参数 db 是一个 AsyncSession 对象，通过 Depends(get_db) 来实现依赖注入，提供一个数据库会话对象，这样我们就可以在这个函数中执行数据库操作了
    # 获取或创建 session 
    session_id = uuid.UUID(request.session_id) if request.session_id else None # 从请求中获取 session_id，如果请求中提供了 session_id，就将它转换为 uuid.UUID 类型，否则就设置为 None，这样我们就知道这是一个新的会话还是一个已有会话了
    if not session_id: # 没有会话 ID → 自动创建新会话 如果没有提供 session_id，说明这是一个新的会话请求，我们需要创建一个新的聊天会话对象，并将它保存到数据库中，create_session 函数会返回一个 ChatSession 对象，我们可以通过 session.id 来获取这个会话的 UUID 主键
        session = await create_session(db, request.mode) # 创建一个新的聊天会话对象，传入数据库会话对象和请求中的模式参数，create_session 函数会在数据库中创建一行新的 chat_sessions 记录，并返回这个新的 ChatSession 对象，我们可以通过 session.id 来获取这个会话的 UUID 主键
        session_id = session.id # 将这个新的会话的 UUID 主键赋值给 session_id 变量，这样后续的消息就知道属于哪个会话了

    # 保存用户消息到数据库
    user_content = request.messages[-1].content # 获取用户发送的最后一条消息的内容，假设这是用户最新输入的消息，我们需要将它保存到数据库中，add_message 函数会在数据库中创建一行新的 chat_messages 记录，关联到这个会话，并且设置 role 为 'user' 和 content 为这个消息的内容
    await add_message(db, session_id, 'user', user_content) # 保存用户消息到数据库 将用户的消息保存到数据库中，传入数据库会话对象、会话 ID、角色 'user' 和消息内容，这样就会在 chat_messages 表中创建一行新的记录，关联到这个会话，并且标记为用户消息
 
    # 读取历史聊天记录（给 AI 做上下文） 加载历史（提供给 LLM 的上下文）
    history = await get_session_history(db, session_id) # 获取这个会话的历史消息，传入数据库会话对象和会话 ID，get_session_history 函数会查询 chat_messages 表中这个会话的历史消息，并返回一个 ChatMessage 对象的列表，这些消息是按照创建时间正序排列的，也就是从最早的消息到最新的消息
    messages = [{'role': m.role, 'content': m.content} for m in history] # 将历史消息转换成一个字典列表，每个字典包含 role 和 content 字段，这样就可以传递给 llm_service 进行处理了，messages 列表中的消息是按照创建时间正序排列的，也就是从最早的消息到最新的消息，这样就能提供完整的上下文给模型了

    # 收集 AI 完整回复（用于保存）流式返回 AI 回复（SSE）
    full_reply = [] # 定义一个列表来收集 AI 回复的完整内容，随着 stream_chat 函数逐个生成文本增量，我们将这些增量追加到 full_reply 列表中，这样当流式生成完成后，我们就可以将 full_reply 列表中的所有文本增量连接成一个完整的回答，并保存到数据库中了

    async def event_generator(): # 定义一个异步生成器函数，用于生成 SSE 事件流，函数内部使用 try-except 块来捕获可能发生的异常
        try: # 在处理过程中，如果发生任何异常，都会被捕获到这里，异常对象被命名为 e
            async for chunk in stream_chat(messages, request.mode): # 调用 stream_chat 函数，传入历史消息列表和模式参数，使用 async for 循环逐个接收生成的文本增量，每次接收到一个文本增量时，就将它封装成一个 JSON 对象，并通过 yield 语句发送给前端
                full_reply.append(chunk) # 将当前的文本增量追加到 full_reply 列表中，这样我们就能收集到 AI 回复的完整内容了
                yield f'data: {json.dumps({"content": chunk, "done": False, "session_id": str(session_id)}, ensure_ascii=False)}\n\n' # 通过 yield 语句发送一个 SSE 事件，事件的数据部分是一个 JSON 对象，包含 content 字段、done 字段和 session_id 字段，content 字段是当前的文本增量，done 字段表示是否已经完成生成，session_id 字段是这个会话的 UUID 主键，这样前端就能正确解析每个事件了
            # AI 回答结束 → 保存完整回复到数据库 流结束后保存 AI 回复
            ai_content = ''.join(full_reply) # 将 full_reply 列表中的所有文本增量连接成一个完整的回答，得到 ai_content 变量，这个变量就是 AI 回复的完整内容了
            await add_message(db, session_id, 'assistant', ai_content) # 将 AI 的回复保存到数据库中，传入数据库会话对象、会话 ID、角色 'assistant' 和 AI 回复的完整内容，这样就会在 chat_messages 表中创建一行新的记录，关联到这个会话，并且标记为 AI 消息
            await db.commit() # 提交数据库事务，将之前添加的用户消息和 AI 回复都保存到数据库中，这样就完成了这个会话的记录了
            yield f'data: {json.dumps({"content": "", "done": True, "session_id": str(session_id)})}\n\n' # 当流式生成完成后，发送一个特殊的事件，表示生成已经完成了，这个事件的 content 字段是一个空字符串，done 字段是 True，session_id 字段是这个会话的 UUID 主键，前端接收到这个事件后就知道可以结束等待了
        except Exception as e: # 如果在处理过程中发生了任何异常，都会被捕获到这里，异常对象被命名为 e
            await db.rollback() # 回滚数据库事务，撤销之前添加的用户消息和 AI 回复，确保数据库保持一致性，避免因为异常导致数据库中出现不完整的记录
            yield f'data: {json.dumps({"error": str(e), "done": True})}\n\n' # 将异常信息封装成一个 JSON 对象，包含 error 字段和 done 字段，error 字段是异常的字符串表示，done 字段表示生成已经完成了，前端接收到这个事件后就知道发生了错误，并且可以结束等待了

    return StreamingResponse(event_generator(), media_type='text/event-stream', # 设置响应的媒体类型为 text/event-stream，表示这是一个 SSE 流式响应，这样前端就能正确处理这个流了 告诉前端这不是http请求，是一个SSE流式响应，前端会自动处理这个流，能边看边等待完整结果，提升体验。不要超时。
        headers={'Cache-Control': 'no-cache', 'X-Accel-Buffering': 'no'}) # 还可以加个 'Connection': 'keep-alive'，告诉前端保持连接不断开

# 新增：获取历史会话接口
@router.get('/sessions', summary='获取历史会话列表') # 定义一个 GET 路由，路径是 /sessions，摘要是“获取历史会话列表”，这个接口将查询数据库中的聊天会话记录，并返回一个包含会话 ID、标题、模式和更新时间的列表，这样前端就可以展示用户的历史会话了
async def get_sessions(db: AsyncSession = Depends(get_db)): # 定义一个异步函数来处理获取历史会话列表的请求，参数 db 是一个 AsyncSession 对象，通过 Depends(get_db) 来实现依赖注入，提供一个数据库会话对象，这样我们就可以在这个函数中执行数据库操作了
    from sqlalchemy import select # 导入 SQLAlchemy 的 select 函数，用于构建查询语句
    from ..models.db_models import ChatSession # 从当前包的 models.db_models 模块导入 ChatSession ORM 模型，表示聊天会话表
    result = await db.execute(select(ChatSession).order_by(ChatSession.updated_at.desc()).limit(20)) # 使用数据库会话的 execute 方法来执行一个查询语句，查询 ChatSession 表中的会话记录，按照 updated_at 字段降序排列，并且限制返回的结果数量为 20，这样就可以获取最近更新的 20 个会话了
    sessions = result.scalars().all() # 使用 scalars() 方法来获取查询结果中的 ChatSession 对象列表，并且使用 all() 方法将它们转换成一个普通的 Python 列表，存储在 sessions 变量中，这个列表中的会话是按照 updated_at 字段降序排列的，也就是最近更新的会话在前面
    return [{'id': str(s.id), 'title': s.title, 'mode': s.mode, 'updated_at': s.updated_at.isoformat()} for s in sessions] # 将会话列表转换成一个字典列表，每个字典包含 id、title、mode 和 updated_at 字段，其中 id 字段是会话的 UUID 主键转换成字符串，title 字段是会话的标题，mode 字段是会话的模式，updated_at 字段是会话的更新时间转换成 ISO 格式的字符串，这样前端就能正确解析这些数据了