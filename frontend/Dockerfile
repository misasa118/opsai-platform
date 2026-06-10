# frontend/Dockerfile
# 多阶段构建：构建阶段 + 运行阶段分离

# ── 阶段1：安装依赖 + 构建
FROM node:20-alpine AS builder
WORKDIR /app

# 先复制 package 文件（层缓存优化）
COPY package.json package-lock.json ./
RUN npm ci --only=production=false

# 复制源码
COPY . .

# 构建时需要知道后端地址（构建时的环境变量）
# 注意：NEXT_PUBLIC_ 变量会被打包进 JS，所以必须在构建时指定
ARG NEXT_PUBLIC_API_URL
ENV NEXT_PUBLIC_API_URL=$NEXT_PUBLIC_API_URL

RUN npm run build

# ── 阶段2：运行时（只保留构建产物）
FROM node:20-alpine AS runner
WORKDIR /app

ENV NODE_ENV=production

# 只复制运行所需的文件
COPY --from=builder /app/public ./public
COPY --from=builder /app/.next/standalone ./
COPY --from=builder /app/.next/static ./.next/static

EXPOSE 3000
CMD ["node", "server.js"]