// src/app/(inspection)/page.tsx
// 这是巡检系统的 “用户操作界面 + 实时仪表盘”
// 输入服务器名 → 开始巡检
// 显示实时进度条
// 显示每一步执行日志
// 显示发现的问题
// 展示最终 Markdown 报告
// 完全对接你后端：
// FastAPI WebSocket → LangGraph 巡检 Agent
'use client'
import { useState } from 'react'
import { useInspection } from '@/hooks/useInspection'
import ReactMarkdown from 'react-markdown'
import { clsx } from 'clsx'

export default function InspectionPage() {
  const [serverName, setServerName] = useState('DB01')
  const [customRequest, setCustomRequest] = useState('')
  const { status, steps, report, issues, error, startInspection, stopInspection, isRunning } = useInspection()

  const progressPct = steps.length > 0 ? Math.min((steps.length / 5) * 100, 95) : 0

  return (
    <div className='min-h-screen bg-gray-50 p-6'>
      <div className='max-w-4xl mx-auto space-y-6'>

        {/* 页面标题 */}
        <div>
          <h1 className='text-2xl font-bold text-gray-900'>🔍 自动巡检</h1>
          <p className='text-gray-500 mt-1'>AI 自动完成多步骤数据库巡检，实时查看执行进度</p>
        </div>

        {/* 巡检控制面板 */}
        <div className='bg-white rounded-xl border p-6 space-y-4'>
          <div className='flex gap-3'>
            <input
              value={serverName}
              onChange={e => setServerName(e.target.value)}
              placeholder='服务器名（如 DB01）'
              disabled={isRunning}
              className='flex-1 border rounded-lg px-3 py-2 text-sm'
            />
            <input
              value={customRequest}
              onChange={e => setCustomRequest(e.target.value)}
              placeholder='自定义请求（可选，默认：巡检服务器）'
              disabled={isRunning}
              className='flex-2 border rounded-lg px-3 py-2 text-sm w-64'
            />
            {isRunning ? (
              <button onClick={stopInspection}
                className='px-4 py-2 bg-red-500 text-white rounded-lg text-sm'>
                停止
              </button>
            ) : (
              <button
                onClick={() => startInspection(serverName, customRequest || undefined)}
                disabled={!serverName.trim()}
                className='px-4 py-2 bg-blue-600 text-white rounded-lg text-sm disabled:opacity-50'>
                开始巡检
              </button>
            )}
          </div>

          {/* 进度条 */}
          {status !== 'idle' && (
            <div>
              <div className='flex justify-between text-xs text-gray-500 mb-1'>
                <span>{status === 'completed' ? '巡检完成' : '巡检中...'}</span>
                <span>{status === 'completed' ? '100' : Math.round(progressPct)}%</span>
              </div>
              <div className='h-2 bg-gray-100 rounded-full overflow-hidden'>
                <div
                  className={clsx('h-full rounded-full transition-all duration-500',
                    status === 'completed' ? 'bg-green-500' : 'bg-blue-500'
                  )}
                  style={{ width: status === 'completed' ? '100%' : `${progressPct}%` }}
                />
              </div>
            </div>
          )}
        </div>

        {/* 错误提示 */}
        {error && (
          <div className='bg-red-50 border border-red-200 rounded-xl p-4 text-red-700 text-sm'>
            ⚠️ {error}
          </div>
        )}

        {/* 执行步骤列表 */}
        {steps.length > 0 && (
          <div className='bg-white rounded-xl border p-6'>
            <h2 className='font-semibold text-gray-900 mb-4'>执行步骤</h2>
            <div className='space-y-2'>
              {steps.map((step, i) => (
                <div key={i} className='flex items-start gap-3 text-sm'>
                  <span className='text-gray-400 text-xs mt-0.5 w-12 shrink-0'>
                    {step.timestamp.toLocaleTimeString()}
                  </span>
                  <span className={clsx(
                    step.message.startsWith('🚫') ? 'text-red-600' :
                    step.message.startsWith('⚠️') ? 'text-orange-600' :
                    'text-gray-700'
                  )}>
                    {step.message}
                  </span>
                </div>
              ))}
              {isRunning && (
                <div className='flex items-center gap-2 text-sm text-gray-400'>
                  <span className='animate-pulse'>●</span>
                  <span>执行中...</span>
                </div>
              )}
            </div>
          </div>
        )}

        {/* 问题汇总 */}
        {issues.length > 0 && (
          <div className='bg-orange-50 border border-orange-200 rounded-xl p-6'>
            <h2 className='font-semibold text-orange-800 mb-3'>⚠️ 发现 {issues.length} 个问题</h2>
            <ul className='space-y-1'>
              {issues.map((issue, i) => (
                <li key={i} className='text-sm text-orange-700'>{issue}</li>
              ))}
            </ul>
          </div>
        )}

        {/* 巡检报告 */}
        {report && (
          <div className='bg-white rounded-xl border p-6'>
            <h2 className='font-semibold text-gray-900 mb-4'>📋 巡检报告</h2>
            <div className='prose prose-sm max-w-none'>
              <ReactMarkdown>{report}</ReactMarkdown>
            </div>
          </div>
        )}

      </div>
    </div>
  )
}