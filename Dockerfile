# 后端应用镜像（FastAPI + uvicorn）。
# 依赖直接从 backend/pyproject.toml 提取（tomllib），不把项目当包构建，故无需改 pyproject。
# 运行时布局须保持 /app/{backend,rag,data,background}，使 config.py 的 REPO_ROOT(parents[3])=/app
# 与 rag/*.py 的 parents[1]=/app 都能正确解析（data/、rag/ 的相对关系不能变）。
FROM python:3.13-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

# opencv-python-headless（被 app.tools.scrub 顶层 import → 启动链会强 import cv2）
# 在 slim 上缺 libglib2.0-0 会 ImportError，故装上。psycopg[binary] 自带 libpq，无需额外系统库。
RUN apt-get update \
    && apt-get install -y --no-install-recommends libglib2.0-0 fonts-noto-cjk \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# 先装依赖（缓存层）：用 stdlib tomllib 从 pyproject 抽 [project].dependencies。
COPY backend/pyproject.toml /app/backend/pyproject.toml
RUN python -c "import tomllib; \
    print('\n'.join(tomllib.load(open('/app/backend/pyproject.toml','rb'))['project']['dependencies']))" \
    > /tmp/reqs.txt \
    && pip install --no-cache-dir -r /tmp/reqs.txt

# 运行时必需目录：backend(应用) rag(RAG，被 guide 顶层 import) data(pois/routes.json 运行时硬依赖) background(xlsx，seed 用)
COPY backend /app/backend
COPY rag /app/rag
COPY data /app/data
COPY background /app/background

WORKDIR /app/backend
EXPOSE 8000

# 不带 --reload：与现有约定一致，避免双进程/文件监听问题。
CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
