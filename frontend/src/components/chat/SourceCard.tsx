// src/components/chat/SourceCard.tsx
// 用来显示 AI 回答的参考文档来源
import { BookOpen } from 'lucide-react'

// 接收参数 接收一个字符串数组 例如：["Oracle.txt", "运维手册.pdf"]
interface Props {
  sources: string[]
}

export function SourceCard({ sources }: Props) {
  if (!sources || sources.length === 0) return null // 如果没有来源，直接不显示 没有参考资料就不渲染，避免空框框。

  return (
    <div className='mt-3 p-3 bg-blue-50 border border-blue-100 rounded-xl'>
      <div className='flex items-center gap-1.5 mb-2'>
        <BookOpen className='h-3.5 w-3.5 text-blue-500' />
        <span className='text-xs font-semibold text-blue-700'>参考来源</span>
      </div>
      <div className='flex flex-wrap gap-1.5'>
        {sources.map((source, i) => (
          <span
            key={i}
            className='inline-flex items-center px-2 py-0.5 rounded-full
              text-xs bg-white border border-blue-200 text-blue-700'
          >
            📄 {source}
          </span>
        ))}
      </div>
    </div>
  )
}