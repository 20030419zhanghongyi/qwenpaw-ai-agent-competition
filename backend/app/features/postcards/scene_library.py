"""Pre-generated postcard scenes by POI and time-of-day.

Layout::

    data/postcard_scenes/{poi_id}/{morning|midday|dusk|night}.svg

Visit time (Asia/Macau) selects the slot. Missing slots fall back to a nearby
slot, then any available file for that POI.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

from app.core.config import settings

MACAU_TZ = ZoneInfo("Asia/Macau")

# 早 / 中 / 傍晚 / 晚
TIME_SLOTS: tuple[str, ...] = ("morning", "midday", "dusk", "night")

_SLOT_HOURS: dict[str, tuple[int, int]] = {
    # [start_hour, end_hour) in local Macau time
    "morning": (5, 11),
    "midday": (11, 15),
    "dusk": (15, 19),
    "night": (19, 5),  # wraps midnight
}

_SLOT_LIGHT: dict[str, str] = {
    "morning": "soft morning light, cool blue sky, gentle golden rim light",
    "midday": "bright midday sun, clear shadows, vivid azulejo colors",
    "dusk": "warm dusk / golden hour, long shadows, peach and terracotta sky",
    "night": "night scene, soft lantern glow, deep blue sky, illuminated facades",
}

_SLOT_LABEL_ZH: dict[str, str] = {
    "morning": "早晨",
    "midday": "午间",
    "dusk": "傍晚",
    "night": "夜晚",
}


def scenes_root() -> Path:
    return settings.data_dir / "postcard_scenes"


def slot_for_datetime(when: datetime | None) -> str:
    """Map a timestamp to morning/midday/dusk/night (Macau local)."""
    if when is None:
        when = datetime.now(tz=MACAU_TZ)
    elif when.tzinfo is None:
        when = when.replace(tzinfo=timezone.utc).astimezone(MACAU_TZ)
    else:
        when = when.astimezone(MACAU_TZ)
    hour = when.hour
    for slot, (start, end) in _SLOT_HOURS.items():
        if start < end:
            if start <= hour < end:
                return slot
        else:
            # night wraps midnight
            if hour >= start or hour < end:
                return slot
    return "midday"


def scene_path(poi_id: str, slot: str) -> Path:
    if slot not in TIME_SLOTS:
        raise ValueError(f"unknown time slot: {slot}")
    return scenes_root() / poi_id / f"{slot}.svg"


def list_available_slots(poi_id: str) -> list[str]:
    root = scenes_root() / poi_id
    if not root.is_dir():
        return []
    found: list[str] = []
    for slot in TIME_SLOTS:
        if (root / f"{slot}.svg").is_file():
            found.append(slot)
    return found


def _neighbor_slots(preferred: str) -> list[str]:
    order = list(TIME_SLOTS)
    if preferred not in order:
        return order
    idx = order.index(preferred)
    # Prefer exact, then adjacent times, then the rest.
    ranked = [preferred]
    for delta in (1, -1, 2, -2):
        candidate = order[(idx + delta) % len(order)]
        if candidate not in ranked:
            ranked.append(candidate)
    for slot in order:
        if slot not in ranked:
            ranked.append(slot)
    return ranked


def load_pregenerated_svg(
    poi_id: str,
    *,
    when: datetime | None = None,
    slot: str | None = None,
) -> tuple[str, str] | None:
    """Return ``(slot_used, svg_text)`` or None if nothing on disk."""
    preferred = slot or slot_for_datetime(when)
    for candidate in _neighbor_slots(preferred):
        path = scene_path(poi_id, candidate)
        if not path.is_file():
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except OSError:
            continue
        if "<svg" not in text.lower():
            continue
        return candidate, text
    return None


def build_slot_prompt(
    *,
    poi_name: str,
    district: str | None,
    slot: str,
    language: str = "zh-CN",
    landmarks: str | None = None,
    ref_image_path: str | None = None,
) -> str:
    place = district or ("Macau" if language.startswith("en") or language == "pt" else "澳门")
    light = _SLOT_LIGHT.get(slot, _SLOT_LIGHT["midday"])
    label = _SLOT_LABEL_ZH.get(slot, slot)
    parts = [
        f"地点：{poi_name}（{place}，澳门）",
        f"时段：{label}（{slot}）—— {light}",
        "任务：画一张 Macau AI tourism assistant 明信片插画。"
        "只输出完整 SVG，不要 Markdown、不要解释。",
        "风格：premium flat vector；暖米色纸感 + 墨绿强调；粉彩葡式立面；"
        "优雅克制、有细节，像现代文化旅游 App 插画。",
        "构图：前景街灯/盆栽/游客剪影（可含手持手机与简洁 AI 导航 UI）；"
        "中景为本地点历史建筑；背景柔和天空（远景地标仅在合理时点缀）。"
        "AI 元素要自然：淡路线虚线/定位点，不要科幻全息。",
        "禁止：空洞画面、通用现代玻璃楼、未来城、清晰人脸、画面文字、logo。",
    ]
    if landmarks:
        parts.append(
            "固定景观锚点（早/中/傍晚/晚必须同一地点与构图主体，只改光线）：\n"
            f"{landmarks.strip()}"
        )
    if ref_image_path:
        parts.append(
            f"参考实景图本地路径：{ref_image_path}\n"
            "请先调用 view_image 查看该图，关键建筑/铺地/立面色必须来自参考图。"
        )
    else:
        parts.append("无参考图时严格按景观锚点绘制，禁止胡编无关建筑或动物。")
    parts.append(
        "硬性要求：\n"
        "1) 根元素 <svg xmlns=\"http://www.w3.org/2000/svg\" viewBox=\"0 0 960 720\"> 且必须闭合 </svg>；\n"
        "2) 体现时段光线，建筑主体不变；\n"
        "3) 色板以暖米色与墨绿为主，粉彩与花砖点缀；\n"
        "4) 无文字/人脸/logo/水印；无 script/事件属性/foreignObject；\n"
        "5) 控制复杂度（建议 <12KB），路径简洁，确保一次输出完整闭合。\n"
    )
    return "\n".join(parts) + "\n"
