// src/components/chat/ModeSelector.tsx
// 聊天界面顶部的【模式切换按钮组】  （通用助手、SQL 优化、DBA 专家、OCI 架构）
// 它就是一个 “模式切换器”：
// 展示 4 种 AI 角色
// 点击切换
// 切换时通知父组件
// 流式生成时禁用点击
// 选中变蓝，不选变白
import { ChatMode, CHAT_MODES } from '@/types/chat' // 那 4 种模式的配置（图标、名字）
import { Badge } from '@/components/ui/badge' // UI 组件库里的小徽章组件（用来显示模式图标）
import { clsx } from 'clsx' // clsx：根据条件拼接样式（选中 / 不选中）

// 接收 Props
interface Props {
  currentMode: ChatMode // 当前选中的模式
  onChange: (mode: ChatMode) => void // 切换模式时告诉父组件
  disabled?: boolean  // 流式生成时禁用切换
}

// 组件主体 作用：渲染 4 个模式按钮
export function ModeSelector({ currentMode, onChange, disabled }: Props) {
  return (
    <div className='flex gap-2 flex-wrap'>
      {(Object.keys(CHAT_MODES) as ChatMode[]).map((mode) => { // 循环渲染 4 个按钮 把 CHAT_MODES 里的 4 个模式循环出来，生成 4 个按钮
        const config = CHAT_MODES[mode] // 每个按钮的内容 拿到图标、标签 判断是否是当前选中的模式
        const isActive = mode === currentMode

        return (
          <button
            key={mode}
            onClick={() => !disabled && onChange(mode)} // 按钮点击 切换时调用 onChange 告诉父组件
            disabled={disabled}
            className={clsx( // 按钮样式 基础样式 + 选中 / 不选中样式 + 禁用样式
              'flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-medium',
              'transition-all duration-200 border',
              isActive
                ? 'bg-blue-600 text-white border-blue-600' // 选中：蓝色 
                : 'bg-white text-gray-600 border-gray-200 hover:border-blue-400', // 不选中：白色
              disabled && 'opacity-50 cursor-not-allowed' // 禁用：变灰
            )}
          >
            <span>{config.icon}</span>
            <span>{config.label}</span>
          </button>
        )
      })}
    </div>
  )
}