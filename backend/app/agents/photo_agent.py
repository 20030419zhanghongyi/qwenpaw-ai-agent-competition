"""拍照识别 agent 封装（Phase 4）。

调用 QwenPaw ``photo`` agent：它用自带的 ``view_image`` 工具看一张本地图片，输出
``{description, candidate_poi, confidence}``。**只识别 + 描述，不讲解**（讲解交 guide agent）。

机制（2026-07-13 实测确认）：QwenPaw agent **不**通过内联 image content block 看图，
而是用 ``view_image`` 工具读取「本地文件路径」。故后端把脱敏图写到临时文件、把绝对路径
发给 photo agent，agent 自行 view_image 后输出 JSON。

前提：photo agent 需配**多模态模型** + 启用 ``view_image`` 工具 + 挂 ``photo-recognize``
技能（见 ``skills/README.md``）。当前纯文本模型（如 glm-5）会明确回复「不支持多模态」，
此时本函数拿不到合法 JSON → 返回 None → 调用方降级。

失败哲学：任一环节（网络/解析/校验/模型非多模态）失败返回 None，调用方据此降级，
保证 ``/guide/photo`` 永不因 agent 抖动而 500。对齐 route/intent 的纪律。
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, ValidationError

from app.agents.qwenpaw_client import QwenPawClient, QwenPawError

logger = logging.getLogger("macau_storywalk.photo_agent")

# QwenPaw 中拍照识别 agent 的 id（需手动在 Console 建，见 skills/README.md）
PHOTO_AGENT_ID = "photo"


class PhotoRecognition(BaseModel):
    """photo agent 输出的结构化识别结果。"""

    description: str = ""
    candidate_poi: str | None = None
    confidence: float = 0.0


def _build_prompt(image_path: str, language: str) -> str:
    """构造发给 photo agent 的 prompt（agent 自带 photo-recognize 技能为 system prompt）。"""
    return (
        f"图片路径：{image_path}\n"
        f"语言：{language}\n\n"
        "请按 photo-recognize 技能（先调用 view_image 工具查看上图）输出严格 JSON"
        "（首字符为 {，无解释、无代码围栏）。"
    )


def _extract_json(text: str) -> dict[str, Any] | None:
    """从 agent 文本里抽首个 {...} 并解析；失败返回 None（与 route/intent agent 同款手法）。"""
    if not text:
        return None
    try:
        obj = json.loads(text)
        if isinstance(obj, dict):
            return obj
    except json.JSONDecodeError:
        pass
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        return None
    try:
        obj = json.loads(match.group(0))
        return obj if isinstance(obj, dict) else None
    except json.JSONDecodeError:
        return None


def _coerce(obj: dict[str, Any]) -> PhotoRecognition:
    """把 agent JSON 清洗成 PhotoRecognition（容忍命名差异 / 缺字段 / 越界值）。"""
    description = str(obj.get("description") or "").strip()

    poi = obj.get("candidate_poi")
    if not isinstance(poi, str) or poi.strip().lower() in ("", "null", "none", "无", "未知"):
        poi = None
    else:
        poi = poi.strip()

    try:
        confidence = float(obj.get("confidence"))
    except (TypeError, ValueError):
        confidence = 0.0
    confidence = max(0.0, min(1.0, confidence))

    return PhotoRecognition(description=description, candidate_poi=poi, confidence=confidence)


def recognize(
    image_path: str, *, language: str = "zh-CN", client: QwenPawClient | None = None
) -> PhotoRecognition | None:
    """调 photo agent 识别一张**本地图片文件**。任一环节失败返回 None（→ 调用方降级）。"""
    client = client or QwenPawClient()
    # 每张图独立会话，避免上一张图的描述串扰当前识别
    session_id = f"harness-photo-{uuid4().hex[:8]}"
    try:
        text = client.ask(PHOTO_AGENT_ID, _build_prompt(image_path, language), session_id=session_id)
    except QwenPawError as exc:
        logger.info("photo agent 调用失败，降级：%s", exc)
        return None
    except Exception as exc:  # noqa: BLE001 - 网络/流式响应任何意外都不抛穿，降级
        logger.info("photo agent 异常，降级：%s", exc)
        return None

    obj = _extract_json(text)
    if obj is None:
        logger.info("photo agent 输出非 JSON，降级。原文：%s", (text or "")[:200])
        return None
    try:
        return _coerce(obj)
    except (ValidationError, TypeError) as exc:
        logger.info("photo agent 输出校验失败，降级：%s", exc)
        return None
