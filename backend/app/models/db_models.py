# opsai-platform/backend/app/models/db_models.py  （新增文件）
# 用 Python 类定义了 2 张数据库表
# 聊天会话表（chat_sessions）
# 聊天消息表（chat_messages）
from sqlalchemy import Column, String, Text, Integer, ForeignKey, DateTime # 导入 SQLAlchemy 的列类型和外键等工具
from sqlalchemy.dialects.postgresql import UUID # 导入 PostgreSQL 的 UUID 类型，用于定义 UUID 主键
from sqlalchemy.orm import relationship # 导入 SQLAlchemy 的关系函数，用于定义表之间的关系
from sqlalchemy.sql import func # 导入 SQLAlchemy 的 func 模块，用于使用数据库函数，例如获取当前时间等
from ..database import Base  # 注意这里 import 路径 是相对于当前文件的，导入上面定义的 Base 类，所有 ORM 模型都要继承这个 Base 类才能被 SQLAlchemy 识别成数据库表
import uuid # 导入 Python 的 uuid 模块，用于生成 UUID 主键的默认值


class ChatSession(Base): # 定义一个 ChatSession 类，继承自 Base 类，表示聊天会话表
    __tablename__ = 'chat_sessions' # 指定数据库表名为 chat_sessions，SQLAlchemy 会根据这个名字来创建和查询数据库表

    id         = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4) # 定义一个 id 列，类型为 UUID，作为主键，默认值为 uuid.uuid4() 生成的随机 UUID
    user_id    = Column(String(100), nullable=False, default='default') # 定义一个 user_id 列，类型为字符串，长度限制为 100，不能为空，默认值为 'default'，表示用户 ID，可以根据实际需求修改为更合适的类型和长度
    mode       = Column(String(20), nullable=False, default='general') # 定义一个 mode 列，类型为字符串，长度限制为 20，不能为空，默认值为 'general'，表示聊天模式，例如 'general'、'code' 等，可以根据实际需求修改为更合适的类型和长度
    title      = Column(Text) # 定义一个 title 列，类型为文本，可以存储较长的字符串，表示聊天会话的标题，可以根据实际需求修改为更合适的类型
    created_at = Column(DateTime(timezone=True), server_default=func.now()) # 定义一个 created_at 列，类型为带时区的日期时间，默认值为数据库函数 func.now() 获取当前时间，表示聊天会话的创建时间
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now()) # 定义一个 updated_at 列，类型为带时区的日期时间，默认值为数据库函数 func.now() 获取当前时间，并且在每次更新时自动设置为当前时间，表示聊天会话的更新时间
# relationship('ChatMessage') ChatSession 写 ChatMessage → 关联消息表
# back_populates='session' 关系的反向关联字段，ChatMessage 写 ChatSession → session 在chatmessage里chat_sessions叫做session
# cascade='all, delete' 级联删除，当删除一个聊天会话时，相关的聊天消息也会被自动删除，保持数据一致性
    messages = relationship('ChatMessage', back_populates='session', cascade='all, delete') # 定义一个 messages 关系，表示一个聊天会话可以有多个聊天消息，使用 relationship 函数来建立与 ChatMessage 类的关系，back_populates 参数指定了 ChatMessage 类中对应的关系名称，cascade='all, delete' 表示当删除一个聊天会话时，相关的聊天消息也会被自动删除，保持数据一致性

# relationship('ChatSession'） ChatMessage 写 ChatSession → 关联会话表
class ChatMessage(Base): # 定义一个 ChatMessage 类，继承自 Base 类，表示聊天消息表
    __tablename__ = 'chat_messages' # 指定数据库表名为 chat_messages，SQLAlchemy 会根据这个名字来创建和查询数据库表

    id          = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4) # 定义一个 id 列，类型为 UUID，作为主键，默认值为 uuid.uuid4() 生成的随机 UUID
    session_id  = Column(UUID(as_uuid=True), ForeignKey('chat_sessions.id'), nullable=False) # 定义一个 session_id 列，类型为 UUID，作为外键，引用 chat_sessions 表的 id 列，不能为空，表示这个消息属于哪个聊天会话
    role        = Column(String(20), nullable=False) # 定义一个 role 列，类型为字符串，长度限制为 20，不能为空，表示消息的角色，例如 'user'、'assistant' 等，可以根据实际需求修改为更合适的类型和长度
    content     = Column(Text, nullable=False) # 定义一个 content 列，类型为文本，不能为空，表示消息的内容，可以根据实际需求修改为更合适的类型
    token_count = Column(Integer, default=0) # 定义一个 token_count 列，类型为整数，默认值为 0，表示消息的 token 数量，可以根据实际需求修改为更合适的类型
    created_at  = Column(DateTime(timezone=True), server_default=func.now()) # 定义一个 created_at 列，类型为带时区的日期时间，默认值为数据库函数 func.now() 获取当前时间，表示消息的创建时间
# relationship('ChatSession'） ChatMessage 写 ChatSession → 关联会话表
# back_populates='messages' 关系的反向关联字段，ChatSession 写 ChatMessage → message 在chatsession里chat_message叫做messages
    session = relationship('ChatSession', back_populates='messages') # 定义一个 session 关系，表示这个消息属于哪个聊天会话，使用 relationship 函数来建立与 ChatSession 类的关系，back_populates 参数指定了 ChatSession 类中对应的关系名称，这样就可以通过 message.session 来访问这个消息所属的聊天会话，也可以通过 session.messages 来访问一个聊天会话的所有消息