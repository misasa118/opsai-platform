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


// 在 src/lib/api.ts 末尾添加以下函数

// ── 文件上传
export async function uploadFile(file: File): Promise<{ fileId: string; filename: string }> {
  const formData = new FormData()
  formData.append('file', file)

  const response = await fetch(`${API_BASE}/api/v1/knowledge/upload`, {
    method: 'POST',
    body: formData,
    // 注意：不要手动设置 Content-Type
    // 浏览器会自动设置 multipart/form-data 并附带 boundary
  })

  if (!response.ok) {
    const error = await response.json()
    throw new Error(error.detail ?? '上传失败')
  }

  const data = await response.json()
  return { fileId: data.file_id, filename: data.filename }
}

// ── 轮询文件处理状态
export async function getFileStatus(fileId: string) {
  const response = await fetch(`${API_BASE}/api/v1/knowledge/status/${fileId}`)
  if (!response.ok) throw new Error('查询状态失败')
  return response.json()
}

// ── 获取知识库文档列表
export async function listDocuments() {
  const response = await fetch(`${API_BASE}/api/v1/knowledge/list`)
  if (!response.ok) throw new Error('获取列表失败')
  return response.json()
}

// ── 流式接口（核心） streamMessage AI 流式打字输出
// onChunk: 每收到一个 token 时的回调
// onDone:  流结束时的回调
// onError: 出错时的回调
// ── 更新 streamMessage：支持 use_rag 参数和 sources 回调 AI 流式对话 + RAG 来源接收
// 内部做了 4 件事：
// 向后端发请求
// 接收 SSE 流式文字（一个字一个字来）
// 解析来源 sources
// 把文字和来源交给页面显示
export async function streamMessage(
  request: ChatRequest & { use_rag?: boolean },
  onChunk: (chunk: string) => void,
  onDone: (sources?: string[]) => void,  // 更新：onDone 携带来源
  onError: (error: string) => void,
): Promise<void> {
  console.log('streamMessage request:', JSON.stringify(request))
  const response = await fetch(`${API_BASE}/api/v1/chat/stream/save`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(request),
  })

  if (!response.ok) { onError(`API 错误: ${response.status}`); return }

  const reader = response.body!.getReader()
  const decoder = new TextDecoder('utf-8')
  let collectedSources: string[] = []

  try {
    while (true) {
      const { done, value } = await reader.read()
      if (done) break

      const text = decoder.decode(value, { stream: true })
      const lines = text.split('\n')

      for (const line of lines) {
        if (!line.startsWith('data: ')) continue
        try {
          const chunk: SSEChunk = JSON.parse(line.slice(6))
          if (chunk.error) { onError(chunk.error); return }
          if (chunk.sources) { collectedSources = chunk.sources }
          if (chunk.done) { onDone(collectedSources); return }
          if (chunk.content) { onChunk(chunk.content) }
        } catch { /* 忽略解析失败的空行 */ }
      }
    }
  } finally {
    reader.releaseLock()
  }
}