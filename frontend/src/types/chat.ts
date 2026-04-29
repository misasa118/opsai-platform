// src/types/chat.ts
// 这是 TypeScript 的类型定义文件，专门给前端代码 “定规矩”：
// 数据长什么样、有哪些字段、能填什么值，防止写错、报错、乱传数据。

// 对应后端 app/models/chat.py 的 ChatMode 枚举 聊天只能是这 4 种模式之一，不能乱写！
export type ChatMode = 'general' | 'sql' | 'dba' | 'oci'

// 对应后端 app/models/chat.py 的 Message 类 Message 消息结构
export interface Message {
  id: string           // 前端生成的唯一 ID，用于 React key
  role: 'user' | 'assistant'
  content: string
  isStreaming?: boolean // 是否正在流式生成（前端状态，后端没有）
  createdAt: Date
}

// 对应后端 app/models/chat.py 的 ChatRequest 类 ChatRequest 发给后端的请求格式 前端发给后端的格式必须长这样：
export interface ChatRequest {
  messages: Pick<Message, 'role' | 'content'>[]  // 只取 role 和 content
  session_id?: string
  mode: ChatMode
}

// SSE 每条数据的格式（对应后端 sse_generator 里的 payload）SSEChunk 流式消息格式
export interface SSEChunk {
  content: string
  done: boolean
  error?: string
}

// 聊天会话（侧边栏用）
export interface ChatSession { // 对应后端 app/models/chat.py 的 ChatSession 类
  id: string
  title: string
  mode: ChatMode
  createdAt: Date
}

// 模式的显示配置 CHAT_MODES 模式配置（显示用）
export const CHAT_MODES: Record<ChatMode, { label: string; description: string; icon: string }> = { // 这个配置可以用来在 UI 上显示不同模式的名称、描述和图标
  general: { label: '通用助手', description: 'IT 运维通用问题', icon: '🤖' },
  sql:     { label: 'SQL 优化', description: 'Oracle SQL 性能分析', icon: '🔍' },
  dba:     { label: 'DBA 专家', description: 'Oracle 数据库管理', icon: '🗄️' },
  oci:     { label: 'OCI 架构', description: 'Oracle Cloud 配置', icon: '☁️' },
}