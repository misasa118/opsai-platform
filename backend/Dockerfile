# opsai-platform/backend/Dockerfile
# 使用官方 Python 3.11 的精简版作为基础镜像
FROM python:3.11-slim

# 在容器里创建并进入 /app 目录
WORKDIR /app 

# 先复制依赖文件（利用 Docker 构建缓存）
# 先复制 requirements.txt
# 安装所有 Python 包（FastAPI、SQLAlchemy、uvicorn、psycopg2 等）
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 再复制代码
COPY . .

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]