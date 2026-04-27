# opsai-platform/backend/app/database.py
# FastAPI 后端连接 PostgreSQL 数据库的「总开关」
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker # 导入 SQLAlchemy 的异步引擎创建函数、异步会话类和异步会话工厂
from sqlalchemy.orm import DeclarativeBase # 导入 SQLAlchemy 的声明式基类，用于定义 ORM 模型
from .config import settings # 从当前包的 config.py 模块导入 settings 对象，包含数据库连接字符串和应用环境等配置项

# 创建异步数据库引擎 创建数据库引擎（连接池） 管理数据库连接，连接字符串来自配置项 settings.DATABASE_URL，开发环境会打印 SQL 语句，连接池大小为 10，最大溢出连接数为 20
engine = create_async_engine( # 创建一个异步数据库引擎，连接到 settings.DATABASE_URL 指定的数据库
    settings.DATABASE_URL, # 数据库连接字符串，格式通常是 "postgresql+asyncpg://user:password@host:port/dbname"
    echo=settings.APP_ENV == 'development',  # 开发环境打印 SQL
    pool_size=10,           # 连接池大小（类比 Oracle 的 connection pool） 最多保持10个连接
    max_overflow=20, # 连接池外最多创建的连接数（总连接数 = pool_size + max_overflow） 高峰期最多再开20个
)

# Session 工厂  创建会话工厂（每次请求一个会话） 使用上面创建的异步引擎，生成 AsyncSession 实例，并设置 expire_on_commit=False 以避免提交后对象过期
# 工厂 = 生产数据库会话
# 每来一个接口请求 → 新开一个会话
# 请求结束 → 自动关闭
AsyncSessionLocal = async_sessionmaker( # 创建一个异步会话工厂，使用上面创建的异步引擎，生成 AsyncSession 实例，并设置 expire_on_commit=False 以避免提交后对象过期
    engine, # 使用上面创建的异步引擎
    class_=AsyncSession, # 指定会话类为 AsyncSession，支持异步操作
    expire_on_commit=False # 提交后不自动过期对象，保持对象状态可用，适合 Web 应用中每个请求一个会话的模式
)

# SQLAlchemy 基类
# 模型基类 = 所有 ORM 数据表模型的「爸爸」
# 所有你定义的表（比如聊天记录、用户表），都必须继承它，才能被 SQLAlchemy 识别成数据库表。
# 所有数据库表（ORM 模型）都要继承这个 Base
# 它让 Python 类 ↔ 数据库表 自动映射
# 这就是 ORM 的核心
# 所有表都共用同一个基类！
# 这样 SQLAlchemy 才能统一管理所有表，一次性创建、更新。
class Base(DeclarativeBase): # 定义一个 SQLAlchemy 的声明式基类，所有 ORM 模型都应该继承这个基类，以便 SQLAlchemy 能够正确地映射数据库表
    pass # 这个基类目前没有添加任何属性或方法，但它是定义 ORM 模型的基础，未来可以在这里添加一些通用的字段或方法，例如 id、created_at、updated_at 等

# FastAPI 依赖注入：每个请求用一个 Session，结束自动关闭 FastAPI 依赖注入 get_db () 给接口提供自动管理的数据库会话
# 自动创建会话
# 自动提交
# 自动回滚
# 自动关闭
# 完全不用手动管理
async def get_db(): # 定义一个异步生成器函数，用于 FastAPI 的依赖注入，提供一个数据库会话对象给每个请求使用，并在请求结束后自动提交或回滚事务
    async with AsyncSessionLocal() as session: # 使用 async with 语句创建一个异步会话对象，确保在使用完毕后会话能够正确关闭，避免连接泄漏
        try: # 在请求处理过程中，使用 yield 语句将会话对象提供给请求处理函数，当请求处理完成后，继续执行 yield 之后的代码来提交或回滚事务
            yield session # 将会话对象提供给请求处理函数，允许它们执行数据库操作
            await session.commit() # 请求处理完成后，尝试提交事务，如果没有异常发生，则提交成功；如果发生异常，则会进入 except 块进行回滚
        except Exception: # 如果在请求处理过程中发生任何异常，都会执行 except 块中的代码来回滚事务，确保数据库保持一致性，并且不会因为未提交的事务而导致连接问题
            await session.rollback() # 回滚事务，撤销在请求处理过程中对数据库所做的任何更改，确保数据库保持一致性
            raise # 重新抛出异常，让 FastAPI 的异常处理机制来处理这个异常，例如返回 500 错误响应等