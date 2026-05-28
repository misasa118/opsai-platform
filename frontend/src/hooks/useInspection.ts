// src/hooks/useInspection.ts
// 这是前端对接 LangGraph 巡检 Agent 的核心 Hook
// 作用：通过 WebSocket 连接后端 → 接收实时进度 → 展示报告 → 管理状态

'use client'
import { useState, useCallback, useRef, useEffect } from 'react'

export type InspectionStatus = 'idle' | 'connecting' | 'running' | 'completed' | 'error'

export interface ProgressStep {
  message: string
  node: string
  step: number
  timestamp: Date
}

// useInspection = 前端巡检大脑
// 管理 WebSocket 连接
// 接收后端实时推送
// 存储进度、报告、错误
// 给页面提供状态和方法
// 完全对应你后端的：
// inspection.py + agent_service.py

export function useInspection() {
  const [status, setStatus]         = useState<InspectionStatus>('idle')
  const [steps, setSteps]           = useState<ProgressStep[]>([])
  const [report, setReport]         = useState<string>('')
  const [issues, setIssues]         = useState<string[]>([])
  const [error, setError]           = useState<string>('')
  const wsRef = useRef<WebSocket | null>(null)

  // 组件卸载时关闭 WebSocket（防止内存泄漏）
  useEffect(() => {
    return () => {
      wsRef.current?.close()
    }
  }, [])

  // 作用：连接后端 → 发请求 → 收消息
  const startInspection = useCallback(async (
    serverName: string,
    userRequest?: string
  ) => {
    // 重置状态
    setSteps([])
    setReport('')
    setIssues([])
    setError('')
    setStatus('connecting')

    const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000'
    const wsUrl = API_BASE.replace('http', 'ws') + '/api/v1/inspection/ws'

    const ws = new WebSocket(wsUrl)
    wsRef.current = ws

    ws.onopen = () => {
      setStatus('running')
      // 连接成功后立刻发送巡检请求
      ws.send(JSON.stringify({
        type: 'start_inspection',
        server_name: serverName,
        user_request: userRequest ?? `巡检 ${serverName}`,
      }))
    }

    ws.onmessage = (event) => {
      const data = JSON.parse(event.data)

      switch (data.type) {
        case 'progress':
          setSteps(prev => [...prev, {
            message:   data.message,
            node:      data.node,
            step:      data.step,
            timestamp: new Date(),
          }])
          break

        case 'report':
          setReport(data.content)
          setIssues(data.issues ?? [])
          break

        case 'done':
          setStatus('completed')
          ws.close()
          break

        case 'error':
          setError(data.message)
          setStatus('error')
          ws.close()
          break
      }
    }

    ws.onerror = () => {
      setError('WebSocket 连接失败，请确认后端服务正在运行')
      setStatus('error')
    }

    ws.onclose = () => {
      if (status === 'running') {
        setStatus('completed')
      }
    }
  }, [status])

  const stopInspection = useCallback(() => {
    wsRef.current?.close()
    setStatus('idle')
  }, [])

  return {
    status, steps, report, issues, error,
    startInspection, stopInspection,
    isRunning: status === 'running' || status === 'connecting',
  }
}