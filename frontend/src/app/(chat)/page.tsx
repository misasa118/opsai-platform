// src/app/(chat)/page.tsx
// 这是整个聊天系统的「总装车间」
// 把所有组件、逻辑全部拼在一起，形成完整页面！**
// 它自己不写任何复杂逻辑，只做一件事：
// 把 useChat 的数据，分发给各个子组件。

// Next.js 强制要求：
// 只要页面有交互、有 useState/useEffect，必须加这一行！
// 告诉 Next.js：这是客户端组件，在浏览器运行。
'use client'  // 这个页面有交互，必须在客户端渲染

// 把所有组件全部导入，准备拼装。
import { useChat } from '@/hooks/useChat' // 导入自定义 Hook useChat，管理聊天的所有状态和逻辑
import { ChatWindow } from '@/components/chat/ChatWindow' // 消息展示组件，负责显示消息列表和自动滚动
import { ChatInput } from '@/components/chat/ChatInput' // 输入组件，负责用户输入和发送消息
import { ModeSelector } from '@/components/chat/ModeSelector' // 模式选择组件，负责切换不同的聊天模式（专家角色）
import { Button } from '@/components/ui/button' // UI 组件库里的按钮组件
import { Trash2 } from 'lucide-react' // 图标组件，Trash2 是垃圾桶图标，用在清空对话按钮上
import { CHAT_MODES } from '@/types/chat' // 聊天模式的配置，包含每个模式的图标和标签，用在顶部显示当前模式和模式选择组件里

export default function ChatPage() {
  const {
    messages,
    isStreaming,
    currentMode,
    setCurrentMode,
    error,
    sendMessage,
    clearMessages,
  } = useChat() // 拿到聊天大脑（useChat）的所有数据和函数，准备分发给子组件 所有状态、所有方法，全部从 useChat 拿！ 页面只管分发，不管逻辑。

  // 页面结构（从上到下）顶部标题栏 + 清空按钮  模式选择栏（切专家角色）错误提示（有错误时显示）消息展示区（ChatWindow）输入区（ChatInput）
  return (
    <div className='flex flex-col h-screen bg-gray-50'>
      {/* 顶部导航栏 */} 
      <header className='flex items-center justify-between px-6 py-3 bg-white border-b shadow-sm'>
        <div className='flex items-center gap-3'>
          <span className='text-xl font-bold text-gray-900'>OpsAI Platform</span>
          <span className='text-xs text-gray-400 bg-gray-100 px-2 py-0.5 rounded-full'>
            {CHAT_MODES[currentMode].icon} {CHAT_MODES[currentMode].label}
          </span>
        </div>
        <Button
          variant='ghost'
          size='sm'
          onClick={clearMessages}
          disabled={isStreaming || messages.length === 0}
          className='text-gray-400 hover:text-red-500'
        >
          <Trash2 className='h-4 w-4 mr-1' />
          清空对话
        </Button>
      </header>

      {/* 模式选择栏 */}
      <div className='px-6 py-2 bg-white border-b'>
        <ModeSelector
          currentMode={currentMode}
          onChange={setCurrentMode}
          disabled={isStreaming}
        />
      </div>

      {/* 错误提示 */}
      {error && (
        <div className='mx-6 mt-2 px-4 py-2 bg-red-50 border border-red-200 rounded-lg text-sm text-red-600'>
          ⚠️ {error}
        </div>
      )}

      {/* 消息区域 */}
      <ChatWindow messages={messages} isStreaming={isStreaming} />

      {/* 输入框 */}
      <ChatInput
        onSend={sendMessage}
        isStreaming={isStreaming}
        placeholder={`向 ${CHAT_MODES[currentMode].label} 提问，Enter 发送...`}
      />
    </div>
  )
}