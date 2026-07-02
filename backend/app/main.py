"""FastAPI 应用入口。

启动：  uvicorn app.main:app --reload --port 8000
文档：  http://localhost:8000/docs
"""

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import api_router
from app.core.config import settings

logging.basicConfig(level=settings.log_level.upper())
logger = logging.getLogger("macau_storywalk")

app = FastAPI(
    title="Macau StoryWalk API",
    description="澳跡同行 —— 基于 QwenPaw 的任务式智慧文旅导览系统",
    version="0.1.0",
)

# Phase 2 本地开发：允许 Vite 前端跨域。上线后收紧为真实域名。
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)


@app.get("/")
def root() -> dict:
    return {"name": "Macau StoryWalk API", "docs": "/docs", "health": "/api/v1/health"}
