// src/lib/api.ts
// 这是前端与后端对话的 “翻译官 + 快递员”
// 所有发消息、流式打字，都靠它！
// 封装了所有后端请求 
// 页面不用管 fetch、SSE、解析
// 页面只负责：调用 → 显示
// 代码干净、好维护、不易出错
// 封装
// 把「SSE 流式请求、流读取、数据解析」一堆复杂代码
// 塞进 api.ts 的 streamMessage 里藏起来。
// 回调
// 页面把「更新聊天文字、结束、报错」的逻辑，
// 写成函数传给 streamMessage；
// 后端流一段段返回数据时，api 内部回头调用你传的函数。
// 封装：外卖后厨，洗菜炒菜全在里面，你只需要点单
// 回调：你留了手机号，饭做好了老板打电话通知你取餐


import { ChatRequest, SSEChunk } from '@/types/chat' 
// 导入types/chat.ts上规定的数据传输的格式 要按照约定的格式发请求、收数据，不乱来。这个文件封装了所有和后端 API 交互的函数，前端其他地方调用这些函数来发送请求，不直接使用 fetch。 这样做的好处是：
// 1. 代码集中，易维护：所有 API 请求相关的代码都在一个文件里，修改接口只需要改这里。
// 2. 统一错误处理：可以在这里统一处理 API 错误，前端其他地方调用时不用重复写错误处理逻辑。
// 3. 隐藏实现细节：前端页面不需要关心 fetch、SSE、数据解析等细节，只需要调用函数，传入参数和回调即可。
const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000' // API 基础 URL，部署时通过环境变量设置 后端地址 本地开发用 8000，部署后自动变。

// ── 非流式接口（测试用） sendMessage（非流式）
export async function sendMessage(request: ChatRequest): Promise<string> {
  const response = await fetch(`${API_BASE}/api/v1/chat/sync`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(request),
  })

  if (!response.ok) {
    throw new Error(`API 错误: ${response.status} ${response.statusText}`)
  }

  const data = await response.json()
  return data.content as string
}

// ── 流式接口（核心） streamMessage AI 流式打字输出
// onChunk: 每收到一个 token 时的回调
// onDone:  流结束时的回调
// onError: 出错时的回调
export async function streamMessage(
  request: ChatRequest,
  // 回调通知页面
  onChunk: (chunk: string) => void, // 来一个字，显示一个字
  onDone: () => void, // 说完了
  onError: (error: string) => void, // 报错了
): Promise<void> {
// 发请求到后端
  const response = await fetch(`${API_BASE}/api/v1/chat/stream`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(request),
  })

  if (!response.ok) {
    onError(`API 错误: ${response.status}`)
    return
  }

  // response.body 是 ReadableStream，需要逐块读取 打开 “流”
  const reader = response.body!.getReader()
  const decoder = new TextDecoder('utf-8')
  // 循环读每一段
  try {
    while (true) {
      const { done, value } = await reader.read()
      if (done) break

      // 解码字节数组为字符串 解析 SSE 格式
      const text = decoder.decode(value, { stream: true })

      // 按行分割，每行可能是一条 SSE 消息
      const lines = text.split('\n')

      for (const line of lines) {
        // SSE 消息以 'data: ' 开头
        if (!line.startsWith('data: ')) continue

        try {
          const chunk: SSEChunk = JSON.parse(line.slice(6)) // 去掉 'data: '

          if (chunk.error) {
            onError(chunk.error)
            return
          }

          if (chunk.done) {
            onDone()
            return
          }

          if (chunk.content) {
            onChunk(chunk.content)
          }
        } catch {
          // 忽略解析失败的行（SSE 格式里空行是正常的）
        }
      }
    }
  } finally {
    reader.releaseLock()
  }
}