# opsai-platform/backend/tests/test_chat.py
# AI 聊天接口的全自动测试脚本，用来验证你的后端能不能正常工作
import pytest # pytest-asyncio 用于支持异步测试
import httpx # httpx 是一个支持异步的 HTTP 客户端库，类似于 requests，但更适合 async/await 语法
import json # 用于解析流式接口返回的 JSON 数据

BASE_URL = 'http://localhost:8000' 

# ── 测试健康检查
@pytest.mark.asyncio # 标记这是一个异步测试函数
async def test_health_check(): # 使用 httpx.AsyncClient 发送 GET 请求到健康检查接口
    async with httpx.AsyncClient() as c: # 创建一个异步 HTTP 客户端
        r = await c.get(f'{BASE_URL}/api/v1/chat/health') # 发送 GET 请求到 /api/v1/chat/health
    assert r.status_code == 200 # 断言响应状态码是 200，表示接口正常
    assert r.json()['status'] == 'ok' # 断言响应 JSON 中的 status 字段是 'ok'

# ── 测试同步接口 （一次性返回完整回答）
# 必须返回 200
# 必须有 content
# 内容不能为空
@pytest.mark.asyncio #  标记这是一个异步测试函数
async def test_chat_sync(): #  使用 httpx.AsyncClient 发送 POST 请求到同步聊天接口
    async with httpx.AsyncClient(timeout=30) as c: # 创建一个异步 HTTP 客户端，设置超时时间为 30 秒
        r = await c.post(f'{BASE_URL}/api/v1/chat/sync', json={ # 发送 POST 请求到 /api/v1/chat/sync，携带 JSON 数据
            'messages': [{'role': 'user', 'content': 'Oracle 有多少种索引类型？用一句话回答'}], # 消息内容是一个用户提问，询问 Oracle 的索引类型
            'mode': 'dba' # 模式设置为 'dba'，表示这是一个数据库管理员相关的问题
        })
    assert r.status_code == 200 # 断言响应状态码是 200，表示接口正常
    data = r.json() # 解析响应 JSON 数据
    assert 'content' in data # 断言响应 JSON 中包含 'content' 字段，表示有回答内容
    assert len(data['content']) > 10  # 回答不应该是空的
    print(f'\n同步接口响应: {data["content"][:100]}...') # 打印回答的前 100 个字符，方便调试

# ── 测试流式接口（打字机效果）
# 必须收到多个 chunk
# 必须返回 session_id
# 内容能拼接成完整回答
@pytest.mark.asyncio # 标记这是一个异步测试函数
async def test_chat_stream(): # 使用 httpx.AsyncClient 发送 POST 请求到流式聊天接口，并逐行读取响应
    chunks_received = 0 # 统计收到的 chunk 数量
    full_content = '' # 用于拼接完整的回答内容

    async with httpx.AsyncClient(timeout=30) as c: # 创建一个异步 HTTP 客户端，设置超时时间为 30 秒
        async with c.stream('POST', f'{BASE_URL}/api/v1/chat/stream/save', json={ # 发送 POST 请求到 /api/v1/chat/stream，携带 JSON 数据
            'messages': [{'role': 'user', 'content': '什么是 Oracle RAC？'}], # 消息内容是一个用户提问，询问 Oracle RAC 是什么
            'mode': 'dba'
        }) as resp:
            assert resp.status_code == 200 # 断言响应状态码是 200，表示接口正常
            async for line in resp.aiter_lines(): # 逐行读取响应内容，流式接口会分多次发送数据，每次一行
                if not line.startswith('data: '): continue # 过滤掉非数据行
                data = json.loads(line[6:]) # 解析 JSON 数据，去掉 'data: ' 前缀
                if data.get('done'): break # 如果 data 中有 done 字段，表示回答结束，跳出循环
                chunks_received += 1 # 统计收到的 chunk 数量
                full_content += data['content'] # 拼接回答内容

    assert chunks_received > 5, '流式输出应该有多个 chunk'
    assert 'session_id' in data  # 响应里有 session_id
    print(f'\n收到 {chunks_received} 个 chunk，总长度 {len(full_content)} 字')

# ── 测试输入校验（空消息会不会报错） 必须返回 422 错误
@pytest.mark.asyncio # 标记这是一个异步测试函数
async def test_validation_empty_content(): # 使用 httpx.AsyncClient 发送 POST 请求到同步聊天接口，测试输入校验逻辑
    async with httpx.AsyncClient() as c: # 创建一个异步 HTTP 客户端
        r = await c.post(f'{BASE_URL}/api/v1/chat/sync', json={ # 发送 POST 请求到 /api/v1/chat/sync，携带 JSON 数据，其中消息内容为空
            'messages': [{'role': 'user', 'content': ''}] # 消息内容是一个用户提问，但内容为空，测试接口的输入校验逻辑
        })
    assert r.status_code == 422  # Unprocessable Entity" 表示请求数据格式正确，但内容不符合要求，接口应该返回这个状态码来提示输入错误