# opsai-platform/backend/app/models/chat.py
# 前端请求 → FastAPI 接口（接收 ChatRequest）→ 调用 llm_service.py（传 messages/mode）→ AI 生成回答 → FastAPI 按 ChatSyncResponse 格式返回 → 前端接收

# Pydantic 模型：定义 API 的请求和响应格式
from pydantic import BaseModel, Field # 用于定义数据模型和字段验证
from typing import List, Optional, Literal # 用于类型注解，List 表示列表类型，Optional 表示可选类型，Literal 表示字面量类型
from datetime import datetime # 用于处理日期和时间

# Message 模型 定义 “一条聊天消息” 的标准格式：必须有 role（谁发的）和 content（发了啥）；
class Message(BaseModel): # 定义一个消息模型，表示聊天中的一条消息
    role: Literal['user', 'assistant', 'system'] # 消息的角色，必须是 'user'（用户）、'assistant'（助手）或 'system'（系统）之一
    content: str = Field(min_length=1, max_length=10000) # 消息的内容，必须是一个长度在 1 到 10000 字符之间的字符串

# ChatRequest 模型：前端发请求的 “总规矩”
class ChatRequest(BaseModel): # 定义一个聊天请求模型，表示前端发送给后端的聊天请求数据结构
    messages: List[Message] = Field(min_length=1) # 消息列表，必须至少包含一条消息
    mode: Literal['general', 'sql', 'dba', 'oci'] = 'general' # 模式参数，必须是 'general'（通用）、'sql'（SQL 专家）、'dba'（数据库管理员）或 'oci'（Oracle 云专家）之一，默认为 'general'
    session_id: Optional[str] = None # 可选的会话 ID，用于关联同一用户的多轮对话，如果不提供则默认为 None session_id 是实现 “上下文对话” 的关键，前端在每次发送请求时都带上同一个 session_id，后端就能知道这些请求属于同一个会话，从而在生成回答时考虑之前的对话内容，实现连续对话的效果。

    class Config: # Pydantic 模型的配置类，用于设置模型的行为和属性
        json_schema_extra = {   # API 文档里的示例
            'example': { # 提供一个示例数据，帮助前端开发者理解请求的格式和内容
                'messages': [{'role': 'user', 'content': 'ORA-01555 怎么处理？'}],
                'mode': 'dba',
                'session_id': 'sess_abc123'
            }
        }

# ChatSyncResponse 模型：后端返回响应的 “总规矩”
class ChatSyncResponse(BaseModel): # 定义一个同步聊天响应模型，表示后端返回给前端的聊天响应数据结构
    content: str # 生成的回答内容，字符串类型
    session_id: Optional[str] # 可选的会话 ID，表示这条回答所属的会话，如果前端在请求中提供了 session_id，则响应中也会包含相同的 session_id，方便前端关联多轮对话
    mode: str # 模式参数，表示生成回答时使用的模式，字符串类型
    created_at: datetime = Field(default_factory=datetime.utcnow) # 创建时间，默认为当前 UTC 时间，使用 default_factory 来动态生成默认值

# 升级 models/chat.py：加入更严格的校验
# 这是 Pydantic 数据模型的强化版，不仅规定请求长什么样，还会自动拦截非法请求、恶意注入、不符合聊天逻辑的参数，保护你的 AI 服务安全稳定。Pydantic：FastAPI 专用的数据校验工具，定义了更严格的 Message 和 ChatRequest 模型，添加了字段验证器来防止常见的 AI 提示词注入攻击，并确保消息列表的最后一条消息必须是用户角色，这样可以大大提升后端服务的安全性和稳定性，避免被恶意用户利用特殊输入来干扰系统的正常行为，例如试图让模型忽略之前的对话历史或者冒充系统角色等攻击行为。
# 长度超标 → 拒收
# 恶意内容 → 拒收
# 格式错误 → 拒收
# 不符合聊天逻辑 → 拒收
# 所有非法请求，在进入 AI 服务前就被直接拦截！
from pydantic import BaseModel, Field, field_validator # 导入 field_validator 用于定义字段级别的验证器，可以在模型中添加自定义的验证逻辑来检查字段的值是否符合特定的规则，例如防止注入攻击、确保消息列表的最后一条消息是用户角色等
from typing import List, Optional, Literal # 导入 Literal 用于定义字段的字面量类型，可以限制字段只能取特定的字符串值，例如 role 字段只能是 'user'、'assistant' 或 'system'，mode 字段只能是 'general'、'sql'、'dba' 或 'oci'

FORBIDDEN_PATTERNS = ['ignore previous', 'system:', 'you are now']  # 简单防御：拦截常见的AI提示词注入攻击 简单防注入的黑名单模式，检查消息内容中是否包含这些敏感词，如果包含则抛出验证错误，防止用户试图通过特殊输入来干扰系统的正常行为，例如试图让模型忽略之前的对话历史或者冒充系统角色等攻击行为

class Message(BaseModel): # 定义一个消息模型，表示聊天中的一条消息，包含角色和内容字段，并添加内容校验逻辑
    role: Literal['user', 'assistant', 'system'] # 消息的角色，必须是 'user'（用户）、'assistant'（助手）或 'system'（系统）之一，使用 Literal 类型来限制字段的取值范围，确保数据的规范性和一致性
    content: str = Field(min_length=1, max_length=8000) # 消息的内容，必须是一个长度在 1 到 8000 字符之间的字符串，使用 Field 来设置字段的验证规则，确保消息内容的合理长度，避免过长或过短的输入 内容：最少1个字，最多8000字（防止超长文本压垮服务器）

    @field_validator('content') # 自定义校验：检查是否有恶意注入 定义一个字段验证器，用于检查 content 字段的值是否包含不允许的内容模式，例如防止注入攻击等安全风险，如果检测到不允许的内容模式，则抛出一个 ValueError 异常，提示用户输入不合法
    @classmethod # 使用 classmethod 装饰器将这个验证器定义为类方法，这样在验证 content 字段时就可以访问类级别的属性和方法，例如 FORBIDDEN_PATTERNS 列表等
    def check_injection(cls, v: str) -> str: # 定义一个方法来检查 content 字段的值是否包含不允许的内容模式，接收一个字符串参数 v，表示消息内容，返回一个字符串，如果验证通过则返回原始内容，如果验证失败则抛出异常
        v_lower = v.lower() # 将消息内容转换为小写字母，方便进行不区分大小写的匹配检查，例如 'Ignore Previous'、'SYSTEM:'、'You are now' 等变体都能被检测到
        for pattern in FORBIDDEN_PATTERNS: # 遍历 FORBIDDEN_PATTERNS 列表中的每个模式，检查消息内容中是否包含这些模式，如果包含则说明存在潜在的注入攻击风险，需要拒绝这个输入
            if pattern in v_lower: # 检查当前模式是否在消息内容中出现，如果出现则说明消息内容包含不允许的模式，可能是用户试图通过特殊输入来干扰系统的正常行为，例如试图让模型忽略之前的对话历史或者冒充系统角色等攻击行为
                raise ValueError(f'检测到不允许的内容模式') # 如果检测到不允许的内容模式，则抛出一个 ValueError 异常，提示用户输入不合法，防止潜在的安全风险
        return v

class ChatRequest(BaseModel): # 定义一个聊天请求模型，表示前端发送给后端的聊天请求数据结构，包含消息列表、模式参数和可选的会话 ID，并添加消息列表的校验逻辑
    messages: List[Message] = Field(min_length=1, max_length=50)  # 最多50条历史
    mode: Literal['general', 'sql', 'dba', 'oci'] = 'general' # 模式参数，必须是 'general'（通用）、'sql'（SQL 专家）、'dba'（数据库管理员）或 'oci'（Oracle 云专家）之一，默认为 'general'
    session_id: Optional[str] = Field(default=None, max_length=100) # 可选的会话 ID，用于关联同一用户的多轮对话，如果不提供则默认为 None，使用 Field 来设置字段的验证规则，限制 session_id 的最大长度为 100 字符，确保会话 ID 的合理长度，避免过长的输入

    @field_validator('messages') # 定义一个字段验证器，用于检查 messages 字段的值是否符合特定的规则，例如确保消息列表的最后一条消息是用户角色，如果验证失败则抛出一个 ValueError 异常，提示用户输入不合法
    @classmethod # 使用 classmethod 装饰器将这个验证器定义为类方法，这样在验证 messages 字段时就可以访问类级别的属性和方法，例如 Message 模型等
    def last_message_must_be_user(cls, v: List[Message]) -> List[Message]: # 定义一个方法来检查 messages 字段的值是否符合特定的规则，接收一个 List[Message] 类型的参数 v，表示消息列表，返回一个 List[Message] 类型，如果验证通过则返回原始消息列表，如果验证失败则抛出异常
        if v and v[-1].role != 'user': # 检查消息列表是否非空，并且最后一条消息的角色是否是 'user'，如果不是则说明消息列表不合法，可能会导致模型生成不符合预期的回答，因为模型通常需要以用户消息结尾来触发回答生成
            raise ValueError('最后一条消息必须是 user 角色') # 如果消息列表的最后一条消息的角色不是 'user'，则抛出一个 ValueError 异常，提示用户输入不合法，确保消息列表的规范性和合理性
        return v