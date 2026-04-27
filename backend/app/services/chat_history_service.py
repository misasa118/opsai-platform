# opsai-platform/backend/app/services/chat_history_service.py  （新增文件）
#   
# 负责：创建会话、保存消息、查询历史。 它不涉及接口、不涉及 AI 流式输出，只专心管数据库。
# 开新会话
# 存用户消息
# 存 AI 消息
# 查历史给 AI 上下文 **
from sqlalchemy.ext.asyncio import AsyncSession # 导入 SQLAlchemy 的异步会话类，用于执行数据库操作
from sqlalchemy import select # 导入 SQLAlchemy 的 select 函数，用于构建查询语句
from ..models.db_models import ChatSession, ChatMessage # 从当前包的 models.db_models 模块导入 ChatSession 和 ChatMessage ORM 模型，分别表示聊天会话表和聊天消息表
from typing import List, Optional # 导入 Python 的 typing 模块中的 List 和 Optional 类型，用于类型注解，List 表示一个列表，Optional 表示一个可选值（可以是 None）
import uuid # 导入 Python 的 uuid 模块，用于处理 UUID 类型的主键

# 用户开始新聊天 → 自动创建一个新会话（chat_sessions 表加一行）
async def create_session(db: AsyncSession, mode: str = 'general') -> ChatSession: # 定义一个异步函数 create_session，用于创建一个新的聊天会话，接受一个 AsyncSession 对象和一个可选的 mode 参数，返回一个 ChatSession 对象
    session = ChatSession(mode=mode) # 创建一个 ChatSession 实例，设置 mode 字段为传入的 mode 参数，其他字段使用默认值，例如 user_id 默认为 'default'，title 默认为 None，created_at 和 updated_at 会自动设置为当前时间
    db.add(session) # 将这个新的 ChatSession 实例添加到数据库会话中，等待提交到数据库
    await db.flush()  # 获取生成的 UUID，但不 commit
    return session # 返回这个新的 ChatSession 对象，调用者可以通过 session.id 来获取这个会话的 UUID 主键

# 把用户问题 / AI 回答 存进 chat_messages 表
async def add_message( # 定义一个异步函数 add_message，用于向一个聊天会话中添加一条新的消息，接受一个 AsyncSession 对象、一个 session_id 参数表示这个消息属于哪个聊天会话、一个 role 参数表示消息的角色（例如 'user'、'assistant' 等）和一个 content 参数表示消息的内容，返回一个 ChatMessage 对象
    db: AsyncSession, # 数据库会话对象，用于执行数据库操作
    session_id: uuid.UUID, # 消息所属的聊天会话的 UUID 主键，类型为 uuid.UUID
    role: str, # 消息的角色，例如 'user'、'assistant' 等，类型为字符串
    content: str # 消息的内容，类型为字符串
) -> ChatMessage: # 函数返回一个 ChatMessage 对象，表示新添加的聊天消息
    # 自动设置 session 标题（取第一条 user 消息的前 50 字） 用户发第一条消息时，自动把消息前 50 字设为会话标题！
    if role == 'user': # 如果这个消息的角色是 'user'，表示这是用户发送的消息，那么我们可以使用这个消息的内容来自动设置聊天会话的标题，取这个消息内容的前 50 个字符作为标题，这样就不需要用户手动输入标题了
        session = await db.get(ChatSession, session_id) # 使用数据库会话的 get 方法来查询这个消息所属的聊天会话对象，传入 ChatSession 类和 session_id 主键，如果找到了这个会话对象，就返回它，否则返回 None
        if session and not session.title: # 如果找到了这个会话对象，并且它的 title 字段还没有设置（为 None 或空字符串），那么我们就可以使用这个消息的内容来设置它的标题了
            session.title = content[:50] # 将这个消息内容的前 50 个字符赋值给会话对象的 title 字段，这样就自动设置了这个会话的标题，方便用户识别这个会话的主题

    msg = ChatMessage(session_id=session_id, role=role, content=content) # 创建一个 ChatMessage 实例，设置 session_id、role 和 content 字段为传入的参数，其他字段使用默认值，例如 token_count 默认为 0，created_at 会自动设置为当前时间
    db.add(msg) # 将这个新的 ChatMessage 实例添加到数据库会话中，等待提交到数据库
    return msg # 返回这个新的 ChatMessage 对象，调用者可以通过 msg.id 来获取这个消息的 UUID 主键

# 获取一个会话的所有历史消息，给 AI 做上下文
# 按时间倒序取最近 20 条
# 最后反转 → 变成正序
# 防止超出 LLM 的上下文长度
async def get_session_history( # 定义一个异步函数 get_session_history，用于获取一个聊天会话的历史消息，接受一个 AsyncSession 对象、一个 session_id 参数表示要查询哪个聊天会话的历史消息，以及一个可选的 limit 参数表示要限制返回多少条消息（默认值为 20），返回一个 ChatMessage 对象的列表，按照消息的创建时间正序排列
    db: AsyncSession, # 数据库会话对象，用于执行数据库操作
    session_id: uuid.UUID, # 要查询哪个聊天会话的历史消息，类型为 uuid.UUID
    limit: int = 20  # 只取最近 20 条，避免超出 context window
) -> List[ChatMessage]: # 函数返回一个 ChatMessage 对象的列表，表示这个聊天会话的历史消息，按照消息的创建时间正序排列
    result = await db.execute( # 使用数据库会话的 execute 方法来执行一个查询语句，查询这个聊天会话的历史消息，查询语句使用 SQLAlchemy 的 select 函数来构建，查询 ChatMessage 表，过滤条件是 session_id 等于传入的 session_id 参数，按照 created_at 字段降序排列，并且限制返回的结果数量为 limit 参数的值，这样就可以获取这个聊天会话的最近 limit 条消息了
        select(ChatMessage) # 查询 ChatMessage 表
        .where(ChatMessage.session_id == session_id) # 过滤条件：session_id 等于传入的 session_id 参数
        .order_by(ChatMessage.created_at.desc()) # 按照 created_at 字段降序排列，这样就可以获取最近的消息了
        .limit(limit) # 限制返回的结果数量为 limit 参数的值，默认值为 20，这样就可以避免返回过多的消息导致超出模型的 context window 了
    )
    msgs = result.scalars().all() # 使用 scalars() 方法来获取查询结果中的 ChatMessage 对象列表，并且使用 all() 方法将它们转换成一个普通的 Python 列表，存储在 msgs 变量中，这个列表中的消息是按照 created_at 字段降序排列的，也就是最近的消息在前面
    return list(reversed(msgs))  # 反转为正序