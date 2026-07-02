from fastapi import APIRouter

from app.core.config import settings

router = APIRouter(tags=["health"])


@router.get("/api/v1/health")
def health() -> dict:
    """健康检查，同时用于本地验证配置是否正确加载。"""
    return {
        "status": "ok",
        "env": settings.app_env,
        # 仅暴露「是否已配置」，绝不暴露 key 本身
        "dashscope_configured": bool(settings.dashscope_api_key),
        "amap_configured": bool(settings.amap_api_key),
    }
