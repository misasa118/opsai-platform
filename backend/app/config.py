# opsai-platform/backend/app/config.py
from pydantic_settings import BaseSettings # 用于定义配置类，支持从环境变量和 .env 文件加载配置项
from functools import lru_cache # 用于缓存函数结果，这里用来实现单例模式，确保全局只有一个 Settings 对象

class Settings(BaseSettings): # 定义一个 Settings 类，继承自 BaseSettings，用于存储应用的配置项
    # LLM 配置
    GROQ_API_KEY: str # 必填项，GROQ 的 API Key，必须在环境变量或 .env 文件中设置
    GOOGLE_API_KEY: str = ''        # Week 4 RAG 时用，现在可以留空

    # 数据库配置
    DATABASE_URL: str = 'postgresql+asyncpg://opsai:opsai123@localhost:5432/opsai' # 数据库连接 URL，默认连接本地的 PostgreSQL 数据库，用户名和密码都是 opsai，数据库名也是 opsai

    # 应用配置
    APP_ENV: str = 'development'    # development / production
    LOG_LEVEL: str = 'INFO' # 日志级别，默认为 INFO，可以在环境变量或 .env 文件中设置为 DEBUG 来启用调试日志
    CORS_ORIGINS: list = ['http://localhost:3000', 'http://127.0.0.1:3000'] # 允许跨域访问的前端地址列表，默认为本地开发环境的地址，可以在生产环境中修改为实际的前端地址

    class Config: # 内部类 Config 用于配置 BaseSettings 的行为
        env_file = '.env'           # 自动读取 .env 文件
        env_file_encoding = 'utf-8' # .env 文件的编码
        extra = 'ignore'          # 忽略 .env 文件中未定义的配置项，避免因为多余的配置项导致错误

@lru_cache()                        # 单例模式：全局只创建一次 Settings 对象
def get_settings() -> Settings: #   定义一个函数来获取 Settings 对象，使用 lru_cache 装饰器来缓存结果，确保全局只有一个 Settings 实例
    return Settings() # 调用 Settings() 来创建一个 Settings 对象，BaseSettings 会自动从环境变量和 .env 文件中加载配置项

settings = get_settings() # 在模块级别创建一个 settings 对象，其他模块可以直接导入这个对象来访问配置项，例如 from app.config import settings，然后通过 settings.GROQ_API_KEY 来访问 GROQ_API_KEY 配置项