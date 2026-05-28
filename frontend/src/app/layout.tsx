// src/app/layout.tsx
// 这是整个项目的「外壳 / 根布局」
// 所有页面都会放在它里面，统一包裹、统一样式、统一配置！
import type { Metadata } from 'next' // Metadata：页面标题、描述等 SEO 配置
import { Inter } from 'next/font/google' // Inter：谷歌字体（让页面字体更好看）
import './globals.css' // globals.css：全局样式（整个项目通用的 CSS）

// 加载字体 加载 Inter 字体，让整个网站文字更美观。
const inter = Inter({ subsets: ['latin'] })

//  网站元信息（标题 + 描述）
// 浏览器标签页显示：OpsAI Platform
// 搜索引擎描述：Oracle 运维 AI 助手
export const metadata: Metadata = {
  title: 'OpsAI Platform',
  description: 'Oracle 运维 AI 助手',
}

// 根布局组件
// 告诉浏览器这是中文网站
// 所有页面内容都会渲染在这里！  page.tsx 就是这里的 children
// layout.tsx = 房子的地基 + 外墙
// page.tsx = 房子里的装修和家具
export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang='zh-CN'>
      <body className={inter.className}>{children}</body>
    </html>
  )
}

// 在顶部导航栏加一个链接
import Link from 'next/link'

<Link href='/inspection'
  className='text-sm text-gray-600 hover:text-blue-600 px-3 py-1'>
  🔍 巡检
</Link>