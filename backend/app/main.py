# opsai-platform/backend/app/main.py
# 1.创建 FastAPI 应用
# 2.打开跨域（让前端能调用）
# 3.注册 chat 路由（把那 3 个接口挂上来）
# 4.提供一个根路径用于检查服务是否活着
# 把所有模块拼在一起 → 启动服务！

from fastapi import FastAPI # 导入 FastAPI 类，用于创建 FastAPI 应用实例 导入 FastAPI 核心
from fastapi.middleware.cors import CORSMiddleware # 导入 CORSMiddleware，用于处理跨域资源共享（CORS）问题，允许前端应用访问后端 API
from .config import settings # 从当前包的 config 模块导入 settings 对象，这个对象包含了应用的配置项，比如 CORS_ORIGINS 等
from .routers import chat # 从当前包的 routers 模块导入 chat 模块，这个模块定义了与聊天相关的 API 路由

app = FastAPI( # 创建 FastAPI 应用实例，设置一些基本的 API 文档信息
    title='OpsAI Platform API',
    description='Oracle 运维 AI 助手后端服务',
    version='0.1.0',
    docs_url='/docs',           # Swagger UI 地址
    redoc_url='/redoc',         # ReDoc 地址 另一种更漂亮的文档页面
)

# ── CORS 配置（允许前端跨域请求） 允许前端调用后端 没有这个，前端会报错 “跨域不允许”
# 开发环境允许 localhost:3000，生产环境改为你的域名
app.add_middleware( # 添加 CORS 中间件，允许前端应用跨域访问后端 API
    CORSMiddleware, #  使用 CORSMiddleware 处理 CORS 问题
    allow_origins=settings.CORS_ORIGINS, # 允许访问的来源列表，从配置中读取，开发环境通常是 ['http://localhost:3000']，生产环境应该改为你的前端域名
    allow_credentials=True, # 允许携带认证信息（如 cookies）
    allow_methods=['*'], # 允许所有 HTTP 方法（GET、POST、PUT、DELETE 等）
    allow_headers=['*'], # 允许所有 HTTP 头部
)

# ── 注册路由
app.include_router(chat.router) # 将 chat 模块中的路由注册到 FastAPI 应用中，这样定义在 chat.router 中的接口就可以被访问了 注册到主程序里，让外部可以访问。 把 chat.py 里的接口 → 插接到 main.py 总入口

# ── 根路由（确认服务在运行）
@app.get('/') # 定义一个 GET 路由，路径是根路径 /，这个接口用于确认服务在运行，返回一些基本的服务信息
async def root(): # 定义一个异步函数来处理根路径的请求，这个函数将返回一个包含服务名称、版本和文档地址的 JSON 对象，前端或监控系统可以通过访问这个接口来确认后端服务是否正常运行
    return { # 返回一个 JSON 对象，包含服务名称、版本和文档地址等基本信息，前端或监控系统可以通过访问这个接口来确认后端服务是否正常运行
        'service': 'OpsAI Platform',
        'version': '0.1.0',
        'docs': '/docs'
    }

# 在 main.py 中添加日志中间件
from fastapi import Request # 导入 Request 类，用于处理 HTTP 请求对象，日志中间件需要访问请求信息来记录日志
import time, logging # 导入 time 模块用于测量请求处理时间，导入 logging 模块用于记录日志信息

logging.basicConfig( # 配置日志记录的基本设置，设置日志级别为 INFO，日志格式包含时间、日志级别、模块名称和消息内容
    level=logging.INFO, # 设置日志级别为 INFO，表示记录 INFO 级别及以上的日志（DEBUG 级别的日志将被忽略）
    format='%(asctime)s %(levelname)s %(name)s %(message)s' # 设置日志格式，包含时间戳（asctime）、日志级别（levelname）、记录器名称（name）和日志消息（message）
)
logger = logging.getLogger('opsai') # 创建一个名为 'opsai' 的日志记录器，后续在代码中使用这个 logger 来记录日志信息，方便调试和监控

# 请求日志中间件 定义中间件：所有HTTP请求都会走这里，记录请求信息和处理时间
@app.middleware('http') # 定义一个 HTTP 中间件，这个函数将在每个请求处理前后被调用，用于记录请求的相关信息和处理时间
async def log_requests(request: Request, call_next): # 定义一个异步函数来处理请求日志，接收一个 Request 对象和一个 call_next 函数作为参数，Request 对象包含了请求的相关信息，call_next 函数用于调用下一个中间件或最终的请求处理函数
    t0 = time.time() # 记录当前时间，作为请求开始处理的时间点
    response = await call_next(request) # 调用 call_next 函数来继续处理请求，等待处理完成并获取响应对象，这个函数会调用下一个中间件或最终的请求处理函数，直到得到响应结果
    elapsed = (time.time() - t0) * 1000 # 计算请求处理的总耗时，作为当前时间减去开始时间，并转换为毫秒单位
    logger.info( # 记录一条 INFO 级别的日志，包含请求方法、请求路径、响应状态码和处理时间等信息，方便调试和监控
        f'{request.method} {request.url.path} → {response.status_code} ({elapsed:.1f}ms)' # 格式化日志消息，包含请求方法（GET、POST 等）、请求路径、响应状态码和处理时间，使用箭头符号 → 分隔请求信息和响应信息，通过这个日志可以清晰地看到每个请求的处理情况和性能指标
    ) 
    return response

# 全局异常处理（避免 500 错误暴露内部信息） 捕获所有全局异常，记录异常信息，并返回一个统一的错误响应，避免暴露内部错误细节
# 用户只能看到 “服务内部错误，请稍后重试”，而不会看到具体的异常信息，除非在开发环境中才会返回详细的异常信息以便调试
# 后台可以看到具体的异常信息和堆栈跟踪，方便开发人员排查问题
from fastapi.responses import JSONResponse # 导入 JSONResponse 类，用于返回 JSON 格式的 HTTP 响应，异常处理函数需要使用这个类来构建错误响应

@app.exception_handler(Exception) # 定义一个全局异常处理器，这个函数将在处理请求时发生未捕获的异常时被调用，用于记录异常信息并返回一个统一的错误响应，避免暴露内部错误细节
async def global_exception_handler(request: Request, exc: Exception): # 定义一个异步函数来处理全局异常，接收一个 Request 对象和一个 Exception 对象作为参数，Request 对象包含了请求的相关信息，Exception 对象包含了发生的异常信息
    logger.error(f'Unhandled exception: {exc}', exc_info=True) # 记录一条 ERROR 级别的日志，包含异常信息和堆栈跟踪（exc_info=True），方便调试和排查问题
    return JSONResponse( # 返回一个 JSON 格式的 HTTP 响应，包含错误信息，状态码为 500，提示用户服务内部错误，同时在开发环境中可以返回详细的异常信息以便调试
        status_code=500, # 设置 HTTP 状态码为 500，表示服务器内部错误
        content={'error': '服务内部错误，请稍后重试', 'detail': str(exc) if settings.APP_ENV == 'development' else None} # 设置响应内容，包含一个 error 字段提示用户服务内部错误，如果当前环境是 development，则返回一个 detail 字段包含异常的详细信息（字符串形式），否则不返回详细信息以避免暴露敏感信息
    )

# backend/app/main.py 里追加知识库相关接口
from app.routers import chat, knowledge
app.include_router(knowledge.router)