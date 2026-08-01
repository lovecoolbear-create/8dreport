FROM python:3.11-slim

WORKDIR /app

# 先拷贝依赖文件并安装，利用 Docker 缓存加速构建
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 拷贝后端所有代码
COPY . .

# 暴露 FastAPI 端口
EXPOSE 8000

# 启动服务
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
