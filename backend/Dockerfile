# backend/Dockerfile
# 多阶段构建：先安装依赖，再复制代码，减小镜像体积

# ── 阶段1：安装依赖
FROM python:3.11-slim AS builder
WORKDIR /app

# 先复制依赖文件（利用 Docker 层缓存：依赖没变就不重新安装）
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ── 阶段2：运行时镜像
FROM python:3.11-slim
WORKDIR /app

# 从 builder 阶段复制已安装的包
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# 复制应用代码
COPY ./app ./app

# 创建上传目录和向量库目录
RUN mkdir -p uploads chroma_db

# 不以 root 运行（安全最佳实践）
RUN useradd -m appuser && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

# 生产环境：不用 --reload，用多个 worker 提高并发
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]