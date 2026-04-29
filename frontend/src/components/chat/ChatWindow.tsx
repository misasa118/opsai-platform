// src/components/chat/ChatWindow.tsx
// 这是聊天的「消息展示窗口」
// 负责：显示所有消息气泡 + 新消息来时自动滚到底部
import { useEffect, useRef } from 'react' // React 的核心 Hook 用来处理副作用（自动滚动）和存储 DOM 引用
import { Message } from '@/types/chat' // 导入消息类型定义
import { MessageBubble } from './MessageBubble' // 消息气泡组件，负责显示每条消息的内容和样式

// 接收参数 从 useChat 拿到消息，负责展示。
interface Props { // 接收父组件传来的 props
  messages: Message[] // 消息列表，父组件传进来，ChatWindow 负责把它们渲染成消息气泡
  isStreaming: boolean // 是否正在流式生成，父组件传进来，ChatWindow 可以根据它来显示不同的 UI（比如输入提示）或者控制滚动行为
}

export function ChatWindow({ messages, isStreaming }: Props) { // 组件主体 作用：渲染消息列表，自动滚动到底部，显示空状态提示
  const bottomRef = useRef<HTMLDivElement>(null) // 动到底部的关键：bottomRef 作用：指向页面最底部的一个小 div 用来实现：来新消息自动滚到底部。每次 messages 变化时，useEffect 触发，调用 bottomRef.current.scrollIntoView() 滚动到那个 div，从而实现自动滚底的效果。 存一个对底部 div 的引用，自动滚动用。这个 div 是消息列表最后一个元素，我们把它当成滚动锚点，每次消息更新时，滚动到这个 div 就能保证看到最新消息了。

  // 每次消息更新时，自动滚动到底部 滚
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' }) // 每当消息变化 → 自动平滑滚到最底部 滚动到 bottomRef 指向的元素（消息列表最后一个 div），behavior: 'smooth' 让滚动有动画效果，更自然
  }, [messages])  // messages 变化时触发

  if (messages.length === 0) { // 没有消息时显示的空状态提示 没有消息时显示欢迎页
    return (
      <div className='flex-1 flex items-center justify-center text-gray-400'> 
        <div className='text-center space-y-2'> 
          <p className='text-4xl'>🗄️</p> 
          <p className='text-lg font-medium'>OpsAI 运维助手</p>
          <p className='text-sm'>选择专家模式，开始提问</p>
        </div>
      </div>
    )
  }

  return ( // 有消息时渲染列表
    <div className='flex-1 overflow-y-auto px-4 py-4 space-y-4'>
      {messages.map(message => (
        <MessageBubble key={message.id} message={message} />
      ))}
      {/* 空 div 作为滚动锚点 */}
      <div ref={bottomRef} />
    </div>
  )
}