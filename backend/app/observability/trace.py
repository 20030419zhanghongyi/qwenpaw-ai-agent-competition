"""调用 trace —— P0 轻量版，为 P4 可观测/落库打底。

每次 QwenPaw 调用记录一条结构化事件，追加到 `harness/results/traces/traces.jsonl`。
P4 再升级为 DB 落库（对齐 `ethics/实施清单.md §3` 审计日志）。

用法：
    from app.observability.trace import record_trace
    record_trace(kind="route.adjust", agent_id="route", status="ok", latency_ms=320)
"""

from __future__ import annotations

import json
import logging
import threading
import hashlib
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.core.config import settings

logger = logging.getLogger("macau_storywalk.trace")

# 单进程内线程安全的追加写。P0 不做轮转/容量上限，P4 落库后可移除。
_lock = threading.Lock()


def _trace_path() -> Path:
    """trace 文件路径（harness/results/traces/traces.jsonl）。"""
    return settings.repo_root / "harness" / "results" / "traces" / "traces.jsonl"


def record_trace(
    *,
    kind: str,
    agent_id: str | None = None,
    chat_id: str | None = None,
    input_summary: str | None = None,
    output_summary: str | None = None,
    latency_ms: int | None = None,
    tokens: dict[str, int] | None = None,
    status: str = "ok",
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Record de-identified operational trace metadata.

    The legacy summary arguments are accepted for compatibility but are reduced
    to character counts and a non-reversible digest before persistence.
    """
    event: dict[str, Any] = {
        "ts": datetime.now(timezone.utc).isoformat(timespec="milliseconds"),
        "kind": kind,
        "status": status,
        "agent_id": agent_id,
        "chat_id_hash": _digest(chat_id),
        "input_chars": len(input_summary) if input_summary else None,
        "input_hash": _digest(input_summary),
        "output_chars": len(output_summary) if output_summary else None,
        "output_hash": _digest(output_summary),
        "latency_ms": latency_ms,
        "tokens": tokens,
    }
    if extra:
        event.update(extra)

    # 去掉值为 None 的可选字段，保持 jsonl 紧凑
    event = {k: v for k, v in event.items() if v is not None}

    try:
        path = _trace_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        line = json.dumps(event, ensure_ascii=False)
        with _lock:
            with path.open("a", encoding="utf-8") as f:
                f.write(line + "\n")
    except OSError as exc:
        # trace 落盘失败不应影响主流程
        logger.warning("trace 落盘失败：%s", exc)

    return event


def _digest(value: str | None) -> str | None:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:16] if value else None
