"""拍照识别 agent 封装（Phase 4）。

调用 QwenPaw ``photo`` agent：它用自带的 ``view_image`` 工具看一张本地图片，输出
``{description, candidate_poi, confidence}``。**只识别 + 描述，不讲解**（讲解交 guide agent）。

机制：QwenPaw agent **不**通过内联 image content block 看图，而是用 ``view_image`` 工具
读取其工作区内的图片文件。故本函数先用 ``QwenPawClient.upload_media`` 把（已脱敏的）图片
字节上传进 photo agent 的工作区，拿到宿主可读的引用路径，再把它发进 prompt，agent 自行
``view_image`` 后输出 JSON。与明信片 ``scene_image.stylize_photo_via_qwenpaw`` 同款交接方式
（容器化后端 ↔ 宿主 QwenPaw 必须走工作区引用，不能传容器内本地路径——宿主看不见容器路径）。

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
from functools import lru_cache
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, ValidationError

from app.agents.qwenpaw_client import QwenPawClient, QwenPawError
from app.db.data import load_pois

logger = logging.getLogger("macau_storywalk.photo_agent")

# QwenPaw 中拍照识别 agent 的 id（需手动在 Console 建，见 skills/README.md）
PHOTO_AGENT_ID = "photo"

# 提示中只放最常见且视觉锚点明确的澳门 POI，控制 token；后处理仍会用完整 pois.json 校验。
_VISUAL_CATALOG = (
    "议事亭前地：黑白葡式碎石波浪纹、粉黄建筑、喷泉；"
    "妈祖阁（妈阁庙）：牌匾、红灯笼、石狮、盘香；"
    "大三巴牌坊：石质巴洛克教堂立面、空窗、石阶；"
    "龙环葡韵：薄荷绿色葡式住宅群、白色线脚；"
    "玫瑰堂：鹅黄色巴洛克立面、白色灰泥、绿色门窗；"
    "东望洋灯塔：白色圆柱灯塔、红色灯室、旁有黄白小堂。"
)

_CANONICAL_ALIASES: dict[str, tuple[str, ...]] = {
    "议事亭前地": ("議事亭前地", "Senado Square", "Largo do Senado"),
    "妈祖阁（妈阁庙）": (
        "妈祖阁",
        "媽祖閣",
        "妈阁庙",
        "媽閣廟",
        "A-Ma Temple",
        "Templo de A-Má",
    ),
    "大三巴牌坊": (
        "大三巴",
        "聖保祿大教堂遺址",
        "圣保禄大教堂遗址",
        "Ruins of St. Paul's",
        "Ruins of Saint Paul",
    ),
    "龙环葡韵": (
        "龍環葡韻",
        "龙环葡韵住宅式博物馆",
        "龍環葡韻住宅式博物館",
        "Taipa Houses",
        "Casas-Museu da Taipa",
    ),
    "玫瑰堂": (
        "板樟堂",
        "圣多明我堂",
        "聖多明我堂",
        "St. Dominic's Church",
        "St Dominic's Church",
        "Igreja de São Domingos",
    ),
    "东望洋灯塔": (
        "東望洋燈塔",
        "东望洋炮台及灯塔",
        "東望洋炮台及燈塔",
        "松山灯塔",
        "松山燈塔",
        "Guia Lighthouse",
        "Farol da Guia",
    ),
}

_NON_SCENE_CUES = ("甘特图", "柱状图", "条形图", "饼图", "折线图", "统计图", "屏幕截图")


class PhotoRecognition(BaseModel):
    """photo agent 输出的结构化识别结果。"""

    description: str = ""
    candidate_poi: str | None = None
    confidence: float = 0.0


def _build_prompt(image_ref: str, language: str) -> str:
    """构造发给 photo agent 的 prompt（agent 自带 photo-recognize 技能为 system prompt）。

    ``image_ref`` 是 ``upload_media`` 返回的、photo agent 工作区内宿主可读的图片引用路径。
    """
    return (
        f"图片路径：{image_ref}\n"
        f"语言：{language}\n\n"
        "请按 photo-recognize 技能先调用 view_image 查看图片，并按“视觉证据 → POI 匹配”顺序判断。\n"
        f"澳门常见 POI 标准名称与视觉锚点：{_VISUAL_CATALOG}\n"
        "candidate_poi 必须使用知识库标准名称；非澳门地标、图表/截图或证据不足时必须为 null。\n"
        "同图有多个地标时，candidate_poi 选画面主体；玫瑰堂的黄白立面和绿色门窗优先于地面波浪纹。\n"
        "description 必须是不少于 20 个字的画面描述，不要改用 reasoning 或 visual_evidence 字段。\n"
        "输出严格 JSON（首字符为 {，无解释、无代码围栏）；画面文字含引号时必须正确 JSON 转义。"
    )


def _repair_unescaped_string_quotes(text: str) -> str:
    """修复 JSON 字符串值里的裸引号（如 ``内嵌有"M"徽记``）。

    仅把“字符串内部且后方不是 JSON 分隔符”的引号转义；键名结尾（后接 ``:``）和字段值
    结尾（后接 ``,``/``}``/``]``）保持不变。该修复只在标准 ``json.loads`` 失败后启用。
    """
    chars: list[str] = []
    in_string = False
    escaped = False
    length = len(text)
    for index, char in enumerate(text):
        if escaped:
            chars.append(char)
            escaped = False
            continue
        if char == "\\" and in_string:
            chars.append(char)
            escaped = True
            continue
        if char != '"':
            chars.append(char)
            continue
        if not in_string:
            in_string = True
            chars.append(char)
            continue

        next_index = index + 1
        while next_index < length and text[next_index].isspace():
            next_index += 1
        next_char = text[next_index] if next_index < length else ""
        if next_char and next_char not in ",:}]":
            chars.append('\\"')
        else:
            in_string = False
            chars.append(char)
    return "".join(chars)


def _load_json_object(text: str) -> dict[str, Any] | None:
    for candidate in (text, _repair_unescaped_string_quotes(text)):
        try:
            obj = json.loads(candidate)
        except json.JSONDecodeError:
            continue
        if isinstance(obj, dict):
            return obj
    return None


def _extract_json(text: str) -> dict[str, Any] | None:
    """从 agent 文本里抽首个 {...} 并解析；失败返回 None（与 route/intent agent 同款手法）。"""
    if not text:
        return None
    obj = _load_json_object(text)
    if obj is not None:
        return obj
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        return None
    return _load_json_object(match.group(0))


def _normalize_poi_name(value: Any) -> str:
    return "".join(char for char in str(value or "").casefold() if char.isalnum())


@lru_cache
def _poi_name_index() -> tuple[tuple[str, str], ...]:
    """完整知识库名称索引：模型不能把非澳门地标送进后续 RAG。"""
    names: dict[str, str] = {}
    for poi in load_pois():
        canonical = str(poi.get("name_zh") or "").strip()
        if not canonical:
            continue
        for field in ("name_zh", "name_en", "name_pt"):
            normalized = _normalize_poi_name(poi.get(field))
            if len(normalized) >= 3:
                names.setdefault(normalized, canonical)
    return tuple(sorted(names.items(), key=lambda item: len(item[0]), reverse=True))


def _canonicalize_candidate(value: str) -> str | None:
    normalized = _normalize_poi_name(value)
    if not normalized:
        return None

    alias_pairs: list[tuple[str, str]] = []
    for canonical, aliases in _CANONICAL_ALIASES.items():
        for alias in (canonical, *aliases):
            alias_pairs.append((_normalize_poi_name(alias), canonical))
    for alias, canonical in sorted(alias_pairs, key=lambda item: len(item[0]), reverse=True):
        if alias and (alias in normalized or normalized in alias):
            return canonical

    for known_name, canonical in _poi_name_index():
        if known_name == normalized or known_name in normalized:
            return canonical
        if len(normalized) >= 4 and normalized in known_name:
            return canonical
    return None


def _description_from_obj(obj: dict[str, Any]) -> str:
    """统一模型偶发的字段漂移，但不补写模型没有给出的视觉事实。"""
    description = str(obj.get("description") or "").strip()
    if description:
        return description

    evidence = obj.get("visual_evidence")
    parts: list[str] = []
    if isinstance(evidence, list):
        values = [str(item).strip() for item in evidence if str(item).strip()]
        if values:
            joined_evidence = "、".join(values)
            parts.append(f"视觉证据：{joined_evidence}")
    elif isinstance(evidence, str) and evidence.strip():
        parts.append(f"视觉证据：{evidence.strip()}")

    reasoning = str(obj.get("reasoning") or "").strip()
    if reasoning:
        parts.append(f"判断依据：{reasoning}")
    return "。".join(parts)


def _disambiguate_candidate(poi: str | None, description: str) -> str | None:
    """在同一街区出现多个地标时，让画面主体的专属特征优先。"""
    if poi != "议事亭前地" or "喷泉" in description:
        return poi

    dominic_cues = (
        any(cue in description for cue in ("鹅黄", "黄色")),
        "教堂" in description,
        any(cue in description for cue in ("绿色", "鲜绿", "深绿")),
        any(cue in description for cue in ("百叶窗", "巴洛克", "灰泥", "白色装饰")),
    )
    if sum(dominic_cues) >= 3:
        return "玫瑰堂"
    return poi


def _coerce(obj: dict[str, Any]) -> PhotoRecognition:
    """把 agent JSON 清洗成 PhotoRecognition（容忍命名差异 / 缺字段 / 越界值）。"""
    description = _description_from_obj(obj)

    raw_poi = obj.get("candidate_poi")
    if not isinstance(raw_poi, str) or raw_poi.strip().lower() in (
        "",
        "null",
        "none",
        "无",
        "未知",
    ):
        raw_poi = None

    try:
        confidence = float(obj.get("confidence"))
    except (TypeError, ValueError):
        confidence = 0.0
    confidence = max(0.0, min(1.0, confidence))

    poi = _canonicalize_candidate(raw_poi) if raw_poi else None
    poi = _disambiguate_candidate(poi, description)
    if any(cue in description for cue in _NON_SCENE_CUES):
        poi = None
        confidence = min(confidence, 0.1)
    elif raw_poi and poi is None:
        # 模型点名了知识库外地标：保留视觉描述，但禁止进入澳门 POI 检索。
        confidence = min(confidence, 0.3)
    elif poi is None:
        confidence = min(confidence, 0.3)

    return PhotoRecognition(description=description, candidate_poi=poi, confidence=confidence)


def recognize(
    image_bytes: bytes,
    *,
    language: str = "zh-CN",
    client: QwenPawClient | None = None,
    filename: str | None = None,
) -> PhotoRecognition | None:
    """调 photo agent 识别一张图片（原始字节）。

    先用 ``upload_media`` 把字节上传进 photo agent 工作区、拿宿主可读引用（容器化后端不能
    把容器内路径直接发给宿主 QwenPaw——宿主看不见），再把引用发进 prompt 让 agent ``view_image``。
    任一环节（上传/网络/解析/校验/模型非多模态）失败返回 None（→ 调用方降级）。
    """
    client = client or QwenPawClient()
    # 每张图独立会话，避免上一张图的描述串扰当前识别；同时用作上传文件名（不泄漏样本原名）
    session_id = f"harness-photo-{uuid4().hex[:8]}"
    upload_name = filename or f"{session_id}.jpg"
    try:
        reference = client.upload_media(image_bytes, filename=upload_name, agent_id=PHOTO_AGENT_ID)
        text = client.ask(PHOTO_AGENT_ID, _build_prompt(reference, language), session_id=session_id)
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
