# opsai-platform/backend/app/services/llm_service.py
# 为 OpsAI 平台封装 AI 能力 —— 给 AI 定义 4 种专业角色（general/sql/dba/oci）并制定对应的回答规范
# 同时提供「流式实时回答（stream_chat）」和「完整一次性回答（complete）」两种调用方式，让 FastAPI 接口能直接复用这些 AI 能力。

from openai import AsyncOpenAI # 导入 GROQ 的 AsyncOpenAI 客户端，用于异步调用 LLM 接口
from typing import AsyncGenerator, List # 导入类型提示，AsyncGenerator 用于标注异步生成器函数的返回类型，List 用于标注列表类型
from ..config import settings # 从配置模块导入 settings 对象，获取 GROQ_API_KEY 等配置项

# ── 客户端初始化（模块加载时执行一次）
client = AsyncOpenAI( # 创建一个 AsyncOpenAI 客户端实例，使用配置中的 GROQ_API_KEY 进行认证，base_url 指定 GROQ 的 API 端点
    api_key=settings.GROQ_API_KEY, # 从配置对象中获取 GROQ_API_KEY，确保安全地管理密钥
    base_url='https://api.groq.com/openai/v1' # GROQ 的 API 端点，注意不是 OpenAI 的默认端点
)

# ── 专家角色 System Prompt 库
# 注意：这里的 Prompt 是工程设计，不是随手写的
# 每个 Prompt 都包含：角色定义 + 输出约束 + 思考框架
SYSTEM_PROMPTS = { # 定义不同模式下的系统提示，指导 LLM 以特定角色和思维方式回答问题
    'general': '''你是 OpsAI 平台的 IT 运维助手，专注于：
- Oracle Database：性能调优、故障排查、备份恢复
- OCI/AWS 云平台：服务配置、网络设计、成本优化
- Linux 系统：命令操作、性能监控、日志分析

回答原则：
1. 优先给出可执行的命令或 SQL，而非只讲理论
2. 涉及生产操作时，主动提醒风险和前置检查步骤
3. 不确定的内容，明确说「建议进一步验证」''',

    'sql': '''你是 Oracle SQL 性能优化专家。
分析 SQL 性能问题时，必须按以下结构回答：

## 问题识别
（列出 SQL 中的具体性能问题）

## 根因分析
（解释为什么这是问题，涉及哪个执行计划操作）

## 优化方案
（给出改写后的 SQL 或 DDL，必须可直接执行）

## 验证方法
（如何验证优化效果，用 EXPLAIN PLAN 或 DBMS_XPLAN）''',

    'dba': '''你是资深 Oracle DBA，专注于数据库稳定性和性能。
遇到问题时的思考框架：
1. 定位：是哪层出了问题（SQL / 等待事件 / 资源 / 配置）？
2. 量化：问题有多严重（影响范围 / 持续时间 / 趋势）？
3. 处理：临时缓解措施 vs 根本解决方案
4. 预防：如何避免再次发生

每次回答都尽量覆盖这四个维度。''',

    'oci': '''你是 OCI 认证架构师。
回答时遵循 OCI Well-Architected Framework 的五大支柱：
安全性 / 可靠性 / 性能效率 / 成本优化 / 卓越运营
给出服务推荐时，注明免费层限制和付费估算。''',
}

# ── 核心方法：异步流式生成  就是一个个打字的效果 边生成边返回，前端实时显示（用户体验好）；
# yield：Python 里的关键字，作用是 “逐个往外吐数据”（不是一次性返回所有数据）。
async def stream_chat( # 定义一个异步生成器函数，接收用户消息列表、模式和温度参数，返回一个异步生成器，逐个 yield LLM 生成的 token
    messages: List[dict], # 用户的对话历史，每条消息是一个字典，包含 role（system/user/assistant）和 content（消息内容）
    mode: str = 'general', # 模式参数，决定使用哪个系统提示，默认为 'general'，可以是 'sql'、'dba'、'oci' 等
    temperature: float = 0.3 # 生成文本的随机程度，默认为 0.3，数值越高输出越随机，适合需要创造性的回答；数值越低输出越确定，适合需要准确性的回答
) -> AsyncGenerator[str, None]: # 返回一个异步生成器，yield 的类型是 str，表示每次生成的文本片段，第二个 None 表示没有 send() 方法（不接受外部输入）
    '''
    流式调用 LLM，逐个 yield token。
    调用方用 async for chunk in stream_chat(...) 接收。
    '''
    system_prompt = SYSTEM_PROMPTS.get(mode, SYSTEM_PROMPTS['general']) # 根据 mode 参数获取对应的系统提示，如果 mode 不在 SYSTEM_PROMPTS 中，则使用 'general' 模式的提示作为默认值
    full_messages = [ # 构建完整的消息列表，第一条是系统提示，后面是用户的对话历史
        {'role': 'system', 'content': system_prompt}, # 系统提示作为第一条消息，指导 LLM 的行为
        *messages   # 解包用户的对话历史 
    ]

    stream = await client.chat.completions.create( # 调用 GROQ 的 chat.completions.create 方法，传入模型名称、完整消息列表、流式参数、温度和最大 token 数量，返回一个异步迭代器（stream）
        model='llama-3.3-70b-versatile', # 使用 GROQ 提供的 LLaMA 3.3 版本，70B 参数量，适合多种任务的通用模型
        messages=full_messages, #   传入构建好的完整消息列表，包含系统提示和用户历史
        stream=True, #  启用流式输出，LLM 会逐个 token 生成并返回，而不是等到完整回答生成完才返回
        temperature=temperature, # 传入温度参数，控制生成文本的随机程度
        max_tokens=2048, # 设置最大生成 token 数量，防止生成过长的回答，2048 是一个合理的上限，根据实际需求可以调整
    )

    async for chunk in stream: # 异步迭代器，逐个接收 LLM 生成的 token，每个 chunk 代表一个生成事件，包含 choices 列表，每个 choice 包含 delta（增量内容）
        delta = chunk.choices[0].delta.content # 从第一个 choice 中提取 delta.content，即本次生成的文本增量
        if delta:           # delta 为 None 时跳过（流结束信号）
            yield delta # 将生成的文本增量通过 yield 返回给调用方，调用方可以在 async for 循环中实时接收和处理这些增量

# ── 非流式版本（用于不需要流式的场景，如 Agent 工具调用）生成完再返回，拿到完整文本（适合程序处理）；
async def complete( # 定义一个异步函数，接收用户消息列表、模式和温度参数，返回完整的 LLM 回答字符串
    messages: List[dict], # 用户的对话历史，每条消息是一个字典，包含 role（system/user/assistant）和 content（消息内容）
    mode: str = 'general', # 模式参数，决定使用哪个系统提示，默认为 'general'，可以是 'sql'、'dba'、'oci' 等
    temperature: float = 0.1     # Agent 决策用低 temperature
) -> str: # 返回一个字符串，表示 LLM 生成的完整回答
    full_response = '' # 初始化一个空字符串，用于累积 LLM 生成的回答
    async for chunk in stream_chat(messages, mode, temperature): # 调用前面定义的 stream_chat 函数，传入用户消息列表、模式和温度参数，异步迭代接收生成的文本增量
        full_response += chunk # 将每个接收到的文本增量累积到 full_response 中，最终得到完整的回答字符串
    return full_response # 返回完整的回答字符串，调用方可以直接使用这个字符串进行后续处理，如发送给前端或作为 Agent 的决策依据