// src/hooks/useChat.ts
import { useState, useCallback, useRef } from 'react'
import { Message, ChatMode } from '@/types/chat'
import { streamMessage } from '@/lib/api'

const genId = () => `${Date.now()}-${Math.random().toString(36).slice(2, 7)}`

export function useChat() {
  const [messages, setMessages]     = useState<Message[]>([])
  const [isStreaming, setIsStreaming] = useState(false)
  const [currentMode, setCurrentMode] = useState<ChatMode>('general')
  const [error, setError]            = useState<string | null>(null)
  const [sessionId, setSessionId]    = useState<string | undefined>()

  // ======================
  // 【你指定：新增 RAG 状态】
  // ======================
  const [useRag, setUseRag] = useState(false)

  const aiMsgIdRef = useRef<string>('')

  const sendMessage = useCallback(async (userInput: string) => {
    if (!userInput.trim() || isStreaming) return
    setError(null)

    const userMsg: Message = {
      id: genId(),
      role: 'user',
      content: userInput,
      createdAt: new Date(),
    }

    const aiMsgId = genId()
    aiMsgIdRef.current = aiMsgId
    const aiMsg: Message = {
      id: aiMsgId,
      role: 'assistant',
      content: '',
      isStreaming: true,
      createdAt: new Date(),
    }

    setMessages(prev => [...prev, userMsg, aiMsg])
    setIsStreaming(true)

    const requestMessages = [...messages, userMsg].map(m => ({
      role: m.role,
      content: m.content,
    }))

    // ================================
    // 【你指定：只修改这里】
    // ================================
    await streamMessage(
      {
        messages: requestMessages,
        mode: currentMode,
        session_id: sessionId,
        use_rag: useRag,  // 【你指定：新增】
      },

      (chunk: string) => {
        setMessages(prev =>
          prev.map(m =>
            m.id === aiMsgIdRef.current
              ? { ...m, content: m.content + chunk }
              : m
          )
        )
      },

      // ====================================================
      // 【你指定：onDone 现在携带 sources 参数】
      // ====================================================
      (sources?: string[]) => {
        setMessages(prev =>
          prev.map(m =>
            m.id === aiMsgIdRef.current
              ? { ...m, isStreaming: false, sources: sources ?? [] }
              : m
          )
        )
        setIsStreaming(false)
      },

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
  }, [messages, isStreaming, currentMode, sessionId, useRag]) // 【你指定：加 useRag】

  const clearMessages = useCallback(() => {
    setMessages([])
    setSessionId(undefined)
    setError(null)
  }, [])

  return {
    messages,
    isStreaming,
    currentMode,
    setCurrentMode,
    error,
    sendMessage,
    clearMessages,

    // ================================
    // 【你指定：新增返回值】
    // ================================
    useRag,
    setUseRag,
  }
}