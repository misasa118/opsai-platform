// src/components/chat/ChatInput.tsx
// 这是聊天界面底部的输入框 + 发送按钮
// 负责：打字、回车发送、自动长高、流式中禁用按钮
import { useState, KeyboardEvent } from 'react' // React 的核心 Hook 用来管理输入框状态、处理键盘事件
import { Button } from '@/components/ui/button' // UI 组件库里的按钮组件
import { Send, Square } from 'lucide-react' // 图标组件，Send 是发送图标，Square 是停止图标（流式生成时显示）

interface Props { // 接收父组件传来的 props
  onSend: (message: string) => void // 把用户输入的文字交给 useChat 发请求 发送消息的函数，父组件传进来，ChatInput 负责调用它把用户输入的消息发出去
  isStreaming: boolean // AI 正在回复时禁止发送 是否正在流式生成，父组件传进来，ChatInput 根据它来禁用输入和切换按钮，以及显示不同的图标
  placeholder?: string // 输入框灰色提示文字 输入框的占位文本，父组件可以传，也可以不传，不传就用默认的提示语
}

export function ChatInput({ onSend, isStreaming, placeholder }: Props) { // 组件主体 作用：渲染输入框和发送按钮，处理用户输入和发送消息的逻辑
  const [input, setInput] = useState('') // 输入框的状态，初始为空字符串，用户输入时更新这个状态 内部状态 存用户当前输入的文字

  const handleSend = () => { // 发送逻辑 发送消息的函数，点击发送按钮或按 Enter 键时调用
    if (!input.trim() || isStreaming) return // 空消息不发 流式中不发 输入为空或正在流式生成时，不发送消息
    onSend(input.trim()) // 调用父组件传进来的 onSend 函数，把用户输入的消息发出去，发送前先 trim() 去掉首尾空格
    setInput('') // 发送后清空输入框
  }

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => { // 处理键盘事件，按 Enter 发送消息，Shift+Enter 换行
    // Enter 发送，Shift+Enter 换行 
    if (e.key === 'Enter' && !e.shiftKey) { // 按 Enter 键且没有按 Shift 键时，发送消息
      e.preventDefault() // 阻止默认行为（换行），让它变成发送消息的触发条件
      handleSend() // 调用发送消息的函数，发送消息
    }
  }

  return (
    // UI 渲染（输入框 + 按钮） 输入区域的布局和样式，flex 布局让输入框和按钮在一行，gap-2 间距，items-end 底部对齐，padding 和边框
    <div className='flex gap-2 items-end p-4 border-t bg-white'> 
      <textarea
        value={input}
        onChange={e => setInput(e.target.value)}
        onKeyDown={handleKeyDown}
        placeholder={placeholder ?? '输入问题，Enter 发送，Shift+Enter 换行...'}
        rows={1}
        className='flex-1 resize-none rounded-xl border border-gray-200 px-4 py-2.5
          text-sm focus:outline-none focus:ring-2 focus:ring-blue-500
          max-h-32 overflow-y-auto'
        style={{ height: 'auto' }}
        onInput={e => {
          // 自动撑高 textarea
          const el = e.currentTarget
          el.style.height = 'auto'
          el.style.height = Math.min(el.scrollHeight, 128) + 'px'
        }}
      />
      <Button
        onClick={handleSend}
        disabled={!input.trim() || isStreaming}
        size='icon'
        className='rounded-xl h-10 w-10 shrink-0'
      >
        {isStreaming ? <Square className='h-4 w-4' /> : <Send className='h-4 w-4' />}
      </Button>
    </div>
  )
}