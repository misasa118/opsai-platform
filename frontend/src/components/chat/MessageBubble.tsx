// src/components/chat/MessageBubble.tsx
// 这是你聊天界面里的MessageBubble 「消息气泡组件」
// 负责显示：用户消息（蓝色右边） + AI 消息（灰色左边 + markdown + 打字光标）
// .tsx 文件 = 可以写 HTML + TypeScript 的 React 组件文件
import ReactMarkdown from 'react-markdown' // 让 AI 消息支持 代码块、表格、加粗、列表
import { Message } from '@/types/chat' // 导入types/chat.ts里定义的消息类型
import { clsx } from 'clsx' // 根据条件拼接 class（Tailwind 必备）

// 接收 props 父组件把一条消息传给我，我负责把它画成气泡
interface Props {
  message: Message
}

export function MessageBubble({ message }: Props) {
  const isUser = message.role === 'user' // 判断是用户还是 AI

  // 最外层布局（左右对齐）用户消息 → justify-end → 靠右 AI 消息 → justify-start → 靠左
    // 气泡样式 用户消息 → 蓝色背景、白字、右边圆角 AI 消息 → 灰色背景、黑字、左边圆角
    // AI 消息内容 → 用 ReactMarkdown 渲染，支持 Markdown 格式
    // 流式生成时 → 在消息末尾显示一个闪烁的竖线（光标动画）
  return (
    <div className={clsx('flex w-full', isUser ? 'justify-end' : 'justify-start')}> 
      <div className={clsx(
        'max-w-[80%] rounded-2xl px-4 py-3 text-sm',
        isUser
          ? 'bg-blue-600 text-white rounded-br-sm'  // 用户消息：蓝色右对齐 
          : 'bg-gray-100 text-gray-900 rounded-bl-sm' // AI 消息：灰色左对齐
      )}>
        {isUser ? (
          // 用户消息：直接显示文本
          <p className='whitespace-pre-wrap'>{message.content}</p>
        ) : (
          // AI 消息：用 Markdown 渲染（支持代码块、列表等） prose 类 Tailwind 专门给 markdown 排版用的样式，让代码、标题、列表都好看。
          <div className='prose prose-sm max-w-none prose-pre:bg-gray-800 prose-pre:text-green-400'>
            <ReactMarkdown>{message.content}</ReactMarkdown>
            {/* 流式生成时显示光标动画 */}
            {message.isStreaming && (
              <span className='inline-block w-0.5 h-4 bg-gray-600 animate-pulse ml-0.5' />
            )}
          </div>
        )}
      </div>
    </div>
  )
}