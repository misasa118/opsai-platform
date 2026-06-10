// next.config.ts
import type { NextConfig } from 'next'

const nextConfig: NextConfig = {
  output: 'standalone',
  async rewrites() {
    return [
      {
        // 前端请求 /api/* 时，自动转发到后端
        // 这样前端代码里用 /api/v1/chat/stream 而不是 http://localhost:8000/...
        source: '/backend/:path*',
        destination: 'http://localhost:8000/:path*',
      },
    ]
  },
}

export default nextConfig

// 使用后，api.ts 里的 API_BASE 改为：
// const API_BASE = ''  // 空字符串，使用相对路径
// fetch('/backend/api/v1/chat/stream', ...)