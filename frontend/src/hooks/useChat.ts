// src/hooks/useChat.ts
// 整个聊天功能的「大脑」Hook
// 所有逻辑：发消息、收消息、流式打字、切换模式、清空对话
import { useState, useCallback, useRef } from 'react' // React 的核心 Hook 用来管理状态、定义函数、存储可变值
import { Message, ChatMode } from '@/types/chat' // 导入消息类型和聊天模式类型
import { streamMessage } from '@/lib/api' // 导入封装好的 API 函数 streamMessage 用来发送消息并接收流式响应

// 生成唯一 ID 的工具函数 导入 + 生成 ID 给每条消息生成唯一 ID，React 列表渲染用。
const genId = () => `${Date.now()}-${Math.random().toString(36).slice(2, 7)}`

export function useChat() { // 状态定义（聊天的所有数据） 自定义 Hook，封装聊天相关的状态和逻辑，供聊天组件使用
  const [messages, setMessages]     = useState<Message[]>([]) // 聊天消息列表，初始为空
  const [isStreaming, setIsStreaming] = useState(false) // 是否正在流式生成 AI 消息
  const [currentMode, setCurrentMode] = useState<ChatMode>('general') // 当前聊天模式，初始为 'general'
  const [error, setError]            = useState<string | null>(null) // 错误信息，初始为 null
  const [sessionId, setSessionId]    = useState<string | undefined>()  // 当前聊天会话 ID（保持上下文），初始为 undefined（新会话）

  // useRef 存储 AI 消息的 ID，在异步回调里安全访问
  // 为什么不用 useState？因为 setState 是异步的，回调里读不到最新值
  // ref 是同步、实时、可随时修改的，专门用来在异步 / 回调里存值、取值。适合存储流式生成过程中不断更新的 AI 消息 ID 
  const aiMsgIdRef = useRef<string>('')

  // 核心函数：sendMessage（发消息）
  const sendMessage = useCallback(async (userInput: string) => { // 发送消息的函数，接收用户输入的文本
    if (!userInput.trim() || isStreaming) return // 输入为空或正在流式生成时，不发送消息
    setError(null) // 发送新消息前，清除之前的错误信息

    // 1. 创建用户消息，立刻显示 创建用户消息 + AI 占位消息 先把用户消息显示出来 
    const userMsg: Message = { // 用户消息结构
      id: genId(), // 生成唯一 ID
      role: 'user', // 消息角色是用户
      content: userInput, // 消息内容是用户输入
      createdAt: new Date(), // 创建时间
    }

    // 2. 创建 AI 消息占位符（内容为空，显示光标）再放一条空的 AI 消息，显示光标闪烁，等后端流式返回内容时再更新它
    const aiMsgId = genId() // 生成 AI 消息的唯一 ID，存到 ref 里，回调里用这个 ID 来更新对应的消息内容和状态
    aiMsgIdRef.current = aiMsgId // 把 AI 消息 ID 存到 ref 里，回调里用这个 ID 来更新对应的消息内容和状态
    const aiMsg: Message = { // AI 消息结构
      id: aiMsgId, // 唯一 ID
      role: 'assistant', // 消息角色是 AI 助手
      content: '', // 内容初始为空，等流式生成时逐步更新
      isStreaming: true, // 正在流式生成，显示光标动画
      createdAt: new Date(), // 创建时间
    }

    setMessages(prev => [...prev, userMsg, aiMsg]) // 把用户消息和 AI 消息占位符一起添加到消息列表，立刻显示用户消息和 AI 消息的光标
    setIsStreaming(true) // 开始流式生成，设置状态

    // 3. 构建发给后端的请求（只取 role 和 content）构造请求体
    const requestMessages = [...messages, userMsg].map(m => ({ // 把之前的消息和当前用户消息一起发给后端，构建请求格式
      role: m.role, // 消息角色
      content: m.content, // 消息内容
    }))

    // 4. 调用流式 API
    await streamMessage( // 调用封装好的 API 函数 streamMessage，发送请求并处理流式响应
      { messages: requestMessages, mode: currentMode, session_id: sessionId }, // 请求参数：消息列表、当前模式、会话 ID

      // onChunk: 每收到一个 token，追加到 AI 消息内容 收到一段文字 → 追加显示 找到 AI 那条消息 → 追加文字 → 实时更新 UI
      (chunk: string) => { // 每收到后端返回的一段文本（一个 token），就把它追加到 AI 消息的 content 里，更新消息列表，UI 立刻显示新内容
        setMessages(prev => // 更新消息列表，找到 AI 消息（通过 ID），把新内容追加到它的 content 上
          prev.map(m => //  遍历消息列表
            m.id === aiMsgIdRef.current // 找到 AI 消息
              ? { ...m, content: m.content + chunk } // 把新内容追加到 AI 消息的 content 上
              : m // 其他消息不变
          )
        )
      },

      // onDone: 流结束，取消光标动画 结束 → 关掉光标
      () => { 
        setMessages(prev =>
          prev.map(m =>
            m.id === aiMsgIdRef.current
              ? { ...m, isStreaming: false }
              : m
          )
        )
        setIsStreaming(false)
      },

      // onError: 显示错误 报错 → 显示错误
      (err: string) => {
        setError(err)
        setMessages(prev =>
          prev.map(m =>
            m.id === aiMsgIdRef.current
              ? { ...m, content: '出错了，请重试', isStreaming: false }
              : m
          )
        )
        setIsStreaming(false)
      },
    )
  }, [messages, isStreaming, currentMode, sessionId])

  // 清空对话函数（切换模式时用） 切换模式 → 清空消息、重置会话 ID、清除错误
  const clearMessages = useCallback(() => {
    setMessages([])
    setSessionId(undefined)
    setError(null)
  }, [])

  // 把状态和方法暴露出去
  return {
    messages,
    isStreaming,
    currentMode,
    setCurrentMode,
    error,
    sendMessage,
    clearMessages,
  }
}