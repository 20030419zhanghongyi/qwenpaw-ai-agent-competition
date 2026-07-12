"""QwenPaw 连通性 / agent 层 HTTP 接口（P0）。

ping 只用 GET 探测，不触发 LLM 调用 —— 即连接基座的静态验证入口。
"""

from __future__ import annotations

import logging
import time

from fastapi import APIRouter

from app.agents.qwenpaw_client import QwenPawClient, QwenPawError
from app.core.config import settings
from app.observability.trace import record_trace

logger = logging.getLogger("macau_storywalk.agents")

router = APIRouter(prefix="/api/v1/agents", tags=["agents"])


@router.get("/ping")
def ping() -> dict:
    """探测本地 QwenPaw 实例连通性 + agent 列表（只读，不发消息）。"""
    t0 = time.perf_counter()
    client = QwenPawClient()
    try:
        result = client.ping()
        record_trace(
            kind="agents.ping",
            status="ok",
            latency_ms=int((time.perf_counter() - t0) * 1000),
            extra={"qwenpaw_version": result.get("qwenpaw_version")},
        )
        return result
    except QwenPawError as exc:
        logger.warning("QwenPaw ping 失败：%s", exc)
        record_trace(kind="agents.ping", status="error", latency_ms=int((time.perf_counter() - t0) * 1000),
                     extra={"error": str(exc)})
        return {
            "reachable": False,
            "base_url": settings.qwenpaw_base_url,
            "error": str(exc),
        }
