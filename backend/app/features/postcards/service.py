"""Build safe postcard captions and rendered SVG assets from completed check-ins."""

from __future__ import annotations

import base64
from datetime import datetime, timezone
from html import escape
from io import BytesIO
import logging
import re
from uuid import uuid4
from zoneinfo import ZoneInfo

from app.agents.qwenpaw_client import QwenPawClient, QwenPawError
from app.core.config import settings
from app.db.models import Postcard as PostcardRecord
from app.db.session import SessionLocal
from app.features.pois.repository import PoiRepository
from app.features.review.api import review_text
from app.features.routes.poi_metadata import get_poi_metadata
from app.features.routes.repository import get_template
from app.features.trips.models import Trip
from app.features.trips.repository import trip_repository
from app.guardrails.runtime import record_audit
from app.tools.scrub import scrub

from .models import PostcardResponse
from .repository import PostcardRepository, postcard_repository
from .scene_image import (
    SceneGenerationError,
    SUPPORTED_PHOTO_STYLES,
    generate_ai_scene,
    generate_ai_scene_via_qwenpaw,
    stylize_photo_via_qwenpaw,
)

logger = logging.getLogger("macau_storywalk.postcards")

SUPPORTED_LANGUAGES = {"zh-CN", "zh-TW", "en", "pt"}
MAX_UPLOAD_BYTES = 8 * 1024 * 1024
MACAU_TZ = ZoneInfo("Asia/Macau")
HAN_RE = re.compile(r"[\u3400-\u9fff]")

DISTRICT_NAMES = {
    "花王堂区": {
        "zh-CN": "花王堂区",
        "zh-TW": "花王堂區",
        "en": "St. Anthony Parish",
        "pt": "Freguesia de Santo António",
    },
    "望德堂区": {
        "zh-CN": "望德堂区",
        "zh-TW": "望德堂區",
        "en": "St. Lazarus Parish",
        "pt": "Freguesia de São Lázaro",
    },
    "大堂区": {
        "zh-CN": "大堂区",
        "zh-TW": "大堂區",
        "en": "Cathedral Parish",
        "pt": "Freguesia da Sé",
    },
    "风顺堂区": {
        "zh-CN": "风顺堂区",
        "zh-TW": "風順堂區",
        "en": "St. Lawrence Parish",
        "pt": "Freguesia de São Lourenço",
    },
    "圣安多尼堂区": {
        "zh-CN": "圣安多尼堂区",
        "zh-TW": "聖安多尼堂區",
        "en": "St. Anthony Parish",
        "pt": "Freguesia de Santo António",
    },
    "嘉模堂区": {
        "zh-CN": "嘉模堂区",
        "zh-TW": "嘉模堂區",
        "en": "Our Lady of Carmel Parish",
        "pt": "Freguesia de Nossa Senhora do Carmo",
    },
    "圣方济各堂区": {
        "zh-CN": "圣方济各堂区",
        "zh-TW": "聖方濟各堂區",
        "en": "St. Francis Xavier Parish",
        "pt": "Freguesia de São Francisco Xavier",
    },
    "路环": {"zh-CN": "路环", "zh-TW": "路環", "en": "Coloane", "pt": "Coloane"},
    "氹仔": {"zh-CN": "氹仔", "zh-TW": "氹仔", "en": "Taipa", "pt": "Taipa"},
}
TRADITIONAL_CHARACTERS = str.maketrans(
    {
        "门": "門",
        "园": "園",
        "题": "題",
        "线": "線",
        "区": "區",
        "场": "場",
        "馆": "館",
        "圣": "聖",
        "东": "東",
        "灯": "燈",
        "妈": "媽",
        "阁": "閣",
        "龙": "龍",
        "环": "環",
        "韵": "韻",
        "旧": "舊",
        "艺": "藝",
        "术": "術",
        "游": "遊",
        "渔": "漁",
        "码": "碼",
        "头": "頭",
        "湾": "灣",
        "关": "關",
        "书": "書",
        "楼": "樓",
        "墙": "牆",
        "遗": "遺",
        "会": "會",
        "纪": "紀",
        "当": "當",
        "业": "業",
        "厂": "廠",
        "赛": "賽",
        "车": "車",
        "广": "廣",
        "马": "馬",
        "桥": "橋",
        "风": "風",
        "顺": "順",
        "岗": "崗",
        "顶": "頂",
        "铺": "鋪",
        "炉": "爐",
        "凤": "鳳",
        "饮": "飲",
        "历": "歷",
        "史": "史",
        "认": "認",
        "知": "知",
        "无": "無",
        "脑": "腦",
        "托": "託",
        "觉": "覺",
        "观": "觀",
        "摄": "攝",
        "颜": "顏",
        "开": "開",
        "发": "發",
        "后": "後",
        "复": "復",
        "杂": "雜",
        "图": "圖",
        "与": "與",
    }
)


def _to_traditional(value: str) -> str:
    return value.translate(TRADITIONAL_CHARACTERS)


class PostcardError(ValueError):
    pass


class PostcardSceneUnavailableError(PostcardError):
    pass


class PostcardNotFoundError(LookupError):
    pass


def _fallback_caption(poi_name: str, language: str) -> str:
    templates = {
        "zh-CN": f"在{poi_name}，把这一刻留给澳门。",
        "zh-TW": f"在{poi_name}，把這一刻留給澳門。",
        "en": f"A Macau moment, kept at {poi_name}.",
        "pt": f"Um momento de Macau guardado em {poi_name}.",
    }
    return templates.get(language, templates["zh-CN"])


def _clean_agent_caption(text: str) -> str:
    cleaned = " ".join((text or "").replace("\n", " ").split()).strip(" \"'“”")
    return cleaned[:120].rstrip("，,;；")


def _agent_caption(poi_name: str, language: str) -> str | None:
    """Optional guide caption — skipped by default for create latency.

    Postcard create already felt slow when scene+caption both hit QwenPaw.
    Keep template captions unless explicitly enabled later.
    """
    if not settings.guide_agent_enabled:
        return None
    # Caption agent adds another full chat turn; prefer templates for snappy UX.
    if not getattr(settings, "postcard_ai_caption_enabled", False):
        return None
    prompt = (
        f"地点：{poi_name}\n语言：{language}\n"
        "请只输出一句不超过 40 个汉字或 100 个字符的旅行明信片文案。"
        "不得编造历史、日期、人物或事实；不要使用引号、标题、JSON 或 Markdown。"
    )
    try:
        caption = _clean_agent_caption(
            QwenPawClient(timeout=12.0).ask("guide", prompt, session_name="postcard-caption")
        )
        return caption or None
    except QwenPawError as exc:
        logger.info("postcard caption agent unavailable, using template: %s", exc)
        return None


def _caption(poi_name: str, language: str) -> tuple[str, str, str, bool, str]:
    agent_caption = _agent_caption(poi_name, language)
    caption = agent_caption or _fallback_caption(poi_name, language)
    verdict = review_text(caption, source_type="ai" if agent_caption else "template")
    if verdict["decision"] != "pass":
        caption = _fallback_caption(poi_name, language)
        return caption, "template", "template", False, "fallback"
    if agent_caption:
        return caption, "agent", "ai", True, verdict["decision"]
    return caption, "template", "template", False, verdict["decision"]


def _format_timestamp(visited_at: datetime, language: str) -> str:
    local = visited_at.astimezone(MACAU_TZ)
    if language == "pt":
        return local.strftime("%d/%m/%Y %H:%M · Macau")
    if language == "en":
        return local.strftime("%Y-%m-%d %H:%M · Macau")
    return local.strftime("%Y-%m-%d %H:%M · 澳门")


def _format_geo_label(
    *,
    latitude: float | None,
    longitude: float | None,
    district: str | None,
    language: str,
) -> str:
    parts: list[str] = []
    if latitude is not None and longitude is not None:
        # Public POI coordinates, rounded (~100 m) — never photo EXIF.
        lat_hem = "N" if latitude >= 0 else "S"
        lng_hem = "E" if longitude >= 0 else "W"
        parts.append(f"{abs(latitude):.3f}°{lat_hem} {abs(longitude):.3f}°{lng_hem}")
    if district:
        localized_district = DISTRICT_NAMES.get(district, {}).get(language)
        if localized_district:
            parts.append(localized_district)
        elif language == "zh-TW":
            parts.append(_to_traditional(district))
        elif language in {"en", "pt"} and HAN_RE.search(district):
            parts.append("Macau")
        else:
            parts.append(district)
    if not parts:
        return "Macau" if language in {"en", "pt"} else "澳门"
    return " · ".join(parts)


def _format_task_label(
    *,
    stop_order: int,
    total_stops: int,
    route_name: str | None,
    language: str,
) -> str:
    stop_n = stop_order + 1
    if language == "zh-TW":
        stop_part = f"第 {stop_n} 站"
        if total_stops > 0:
            stop_part = f"第 {stop_n}/{total_stops} 站"
    elif language == "en":
        stop_part = f"Stop {stop_n}"
        if total_stops > 0:
            stop_part = f"Stop {stop_n} of {total_stops}"
    elif language == "pt":
        stop_part = f"Paragem {stop_n}"
        if total_stops > 0:
            stop_part = f"Paragem {stop_n} de {total_stops}"
    else:
        stop_part = f"第 {stop_n} 站"
        if total_stops > 0:
            stop_part = f"第 {stop_n}/{total_stops} 站"
    if route_name:
        return f"{stop_part} · {route_name}"
    return stop_part


def _render_svg(
    *,
    photo_jpeg: bytes | None,
    scene_svg: str | None,
    poi_name: str,
    caption: str,
    timestamp_label: str,
    geo_label: str,
    task_label: str,
    scene_source: str,
    photo_style: str | None = None,
) -> bytes:
    """Compose a postcard SVG. Geo comes from public POI data, not photo EXIF.

    Scene provenance lives in a non-visible ``data-scene-source`` attribute and
    in the API/UI badges — not as footer copy inside the souvenir face.
    """
    if scene_svg and scene_source in {"ai", "library"} and not photo_jpeg:
        # Nested illustration from QwenPaw (already sanitized).
        inner = scene_svg.strip()
        if inner.lower().startswith("<svg"):
            # Force placement inside the photo panel.
            inner = re.sub(
                r"<svg\b",
                '<svg x="78" y="78" width="658" height="644" preserveAspectRatio="xMidYMid slice"',
                inner,
                count=1,
                flags=re.IGNORECASE,
            )
        else:
            inner = (
                f'<svg x="78" y="78" width="658" height="644" viewBox="0 0 960 720">{inner}</svg>'
            )
        photo_layer = inner
    else:
        photo_base64 = base64.b64encode(photo_jpeg or b"").decode("ascii")
        photo_layer = (
            f'<image x="78" y="78" width="658" height="644" '
            f'preserveAspectRatio="xMidYMid slice" '
            f'href="data:image/jpeg;base64,{photo_base64}"/>'
        )
    source_attr = escape(scene_source or "placeholder", quote=True)
    style_attr = f' data-photo-style="{escape(photo_style, quote=True)}"' if photo_style else ""
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="800" viewBox="0 0 1200 800" role="img" aria-label="Postcard from {escape(poi_name)}" data-scene-source="{source_attr}"{style_attr}>
  <rect width="1200" height="800" fill="#f4eadb"/>
  <rect x="44" y="44" width="1112" height="712" rx="24" fill="#fffaf2" stroke="#a5573f" stroke-width="6"/>
  {photo_layer}
  <line x1="788" y1="106" x2="788" y2="694" stroke="#d9c0a8" stroke-width="3"/>
  <text x="842" y="150" fill="#a5573f" font-family="Noto Serif CJK SC, Songti SC, serif" font-size="48" font-weight="700">MACAU</text>
  <foreignObject x="842" y="176" width="270" height="42"><div xmlns="http://www.w3.org/1999/xhtml" style="font: 15px Arial, sans-serif; color:#806f63; line-height:1.25; overflow-wrap:anywhere;">{escape(task_label)}</div></foreignObject>
  <foreignObject x="842" y="228" width="270" height="132"><div xmlns="http://www.w3.org/1999/xhtml" style="font: 24px 'Noto Serif CJK SC', 'Songti SC', serif; color:#2b3937; line-height:1.12; overflow-wrap:break-word; word-break:normal; hyphens:none;">{escape(poi_name)}</div></foreignObject>
  <foreignObject x="842" y="374" width="270" height="152"><div xmlns="http://www.w3.org/1999/xhtml" style="font: 21px 'Noto Serif CJK SC', serif; color:#39413d; line-height:1.35; overflow-wrap:anywhere;">{escape(caption)}</div></foreignObject>
  <line x1="842" y1="540" x2="1096" y2="540" stroke="#d9c0a8" stroke-width="2"/>
  <text x="842" y="585" fill="#806f63" font-family="Arial, sans-serif" font-size="20">{escape(timestamp_label)}</text>
  <foreignObject x="842" y="615" width="270" height="58"><div xmlns="http://www.w3.org/1999/xhtml" style="font: 15px Arial, sans-serif; color:#806f63; line-height:1.35; overflow-wrap:anywhere;">{escape(geo_label)}</div></foreignObject>
</svg>'''.encode("utf-8")


def _normalize_postcard_svg_layout(svg: bytes) -> bytes:
    """Upgrade stored postcards created before the expanded text layout."""
    replacements = {
        b'<foreignObject x="842" y="228" width="270" height="70">': (
            b'<foreignObject x="842" y="228" width="270" height="132">'
        ),
        b'<foreignObject x="842" y="228" width="270" height="104">': (
            b'<foreignObject x="842" y="228" width="270" height="132">'
        ),
        b"font: 28px 'Noto Serif CJK SC', 'Songti SC', serif": (
            b"font: 24px 'Noto Serif CJK SC', 'Songti SC', serif"
        ),
        b"line-height:1.08": b"line-height:1.12",
        b"line-height:1.12; overflow-wrap:anywhere;": (
            b"line-height:1.12; overflow-wrap:break-word; word-break:normal; hyphens:none;"
        ),
        b'<foreignObject x="842" y="318" width="270" height="200">': (
            b'<foreignObject x="842" y="374" width="270" height="152">'
        ),
        b'<foreignObject x="842" y="350" width="270" height="168">': (
            b'<foreignObject x="842" y="374" width="270" height="152">'
        ),
        b"font: 27px 'Noto Serif CJK SC', serif": (
            b"font: 21px 'Noto Serif CJK SC', serif"
        ),
        b"font: 23px 'Noto Serif CJK SC', serif": (
            b"font: 21px 'Noto Serif CJK SC', serif"
        ),
        b'line-height:1.4; overflow-wrap:anywhere;">': (
            b'line-height:1.35; overflow-wrap:anywhere;">'
        ),
    }
    for old, new in replacements.items():
        svg = svg.replace(old, new)
    return svg


def _draw_wrapped_text(
    draw,
    text: str,
    *,
    xy: tuple[int, int],
    font,
    fill: str,
    max_width: int,
    max_lines: int,
    line_height: int,
) -> None:
    """Draw bounded multilingual text without relying on SVG foreignObject."""
    source = text.strip()
    units = re.findall(r"\S+\s*", source) if re.search(r"\s", source) else list(source)
    lines: list[str] = []
    current = ""
    truncated = False
    for index, unit in enumerate(units):
        candidate = current + unit
        if current and draw.textlength(candidate, font=font) > max_width:
            lines.append(current.rstrip())
            current = unit.lstrip()
            if len(lines) == max_lines:
                truncated = True
                break
        else:
            current = candidate
        if draw.textlength(current, font=font) > max_width:
            word = current
            current = ""
            for character in word:
                candidate = current + character
                if current and draw.textlength(candidate, font=font) > max_width:
                    lines.append(current.rstrip())
                    current = character
                    if len(lines) == max_lines:
                        truncated = True
                        break
                else:
                    current = candidate
            if truncated:
                break
        if index < len(units) - 1 and len(lines) == max_lines:
            truncated = True
            break
    if len(lines) < max_lines and current:
        lines.append(current.rstrip())
    elif current:
        truncated = True
    if truncated and lines:
        last = lines[-1]
        while last and draw.textlength(last + "…", font=font) > max_width:
            last = last[:-1]
        lines[-1] = last.rstrip() + "…"
    x, y = xy
    for index, line in enumerate(lines):
        draw.text((x, y + index * line_height), line, font=font, fill=fill)


def _render_png(*, record: PostcardRecord, postcard: PostcardResponse) -> bytes:
    """Render a downloadable postcard bitmap from persisted scene and metadata."""
    from PIL import Image, ImageDraw, ImageFont, ImageOps

    match = re.search(rb'href="data:image/jpeg;base64,([^\"]+)"', record.image_svg or b"")
    if not match:
        raise PostcardError("postcard bitmap source is unavailable")
    try:
        scene = Image.open(BytesIO(base64.b64decode(match.group(1)))).convert("RGB")
    except Exception as exc:  # noqa: BLE001
        raise PostcardError("postcard bitmap source is invalid") from exc

    canvas = Image.new("RGB", (1200, 800), "#f4eadb")
    draw = ImageDraw.Draw(canvas)
    draw.rounded_rectangle(
        (44, 44, 1156, 756), radius=24, fill="#fffaf2", outline="#a5573f", width=6
    )
    canvas.paste(ImageOps.fit(scene, (658, 644), method=Image.Resampling.LANCZOS), (78, 78))
    draw.line((788, 106, 788, 694), fill="#d9c0a8", width=3)
    draw.line((842, 540, 1096, 540), fill="#d9c0a8", width=2)

    serif_path = "/usr/share/fonts/opentype/noto/NotoSerifCJK-Regular.ttc"
    sans_path = "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"

    def font(path: str, size: int):
        try:
            return ImageFont.truetype(path, size)
        except OSError:
            return ImageFont.load_default(size=size)

    serif_48 = font(serif_path, 48)
    serif_24 = font(serif_path, 24)
    serif_21 = font(serif_path, 21)
    sans_20 = font(sans_path, 20)
    sans_15 = font(sans_path, 15)

    draw.text((842, 105), "MACAU", font=serif_48, fill="#a5573f")
    _draw_wrapped_text(
        draw,
        postcard.task_label or "",
        xy=(842, 176),
        font=sans_15,
        fill="#806f63",
        max_width=270,
        max_lines=2,
        line_height=19,
    )
    _draw_wrapped_text(
        draw,
        postcard.poi_name,
        xy=(842, 228),
        font=serif_24,
        fill="#2b3937",
        max_width=270,
        max_lines=4,
        line_height=29,
    )
    _draw_wrapped_text(
        draw,
        postcard.caption,
        xy=(842, 374),
        font=serif_21,
        fill="#39413d",
        max_width=270,
        max_lines=5,
        line_height=28,
    )
    draw.text((842, 562), postcard.timestamp_label, font=sans_20, fill="#806f63")
    _draw_wrapped_text(
        draw,
        postcard.geo_label or "",
        xy=(842, 615),
        font=sans_15,
        fill="#806f63",
        max_width=270,
        max_lines=3,
        line_height=20,
    )
    output = BytesIO()
    canvas.save(output, format="PNG", optimize=True)
    return output.getvalue()


def _scene_source_from_record(record: PostcardRecord) -> str:
    svg = record.image_svg or b""
    if b'data-scene-source="ai_edit"' in svg:
        return "ai_edit"
    if record.photo_scrubbed:
        return "user"
    if b'data-scene-source="library"' in svg:
        return "library"
    if b'data-scene-source="ai"' in svg or b"AI scene" in svg:
        return "ai"
    return "placeholder"


def _embedded_scene_jpeg(image_svg: bytes) -> bytes | None:
    match = re.search(rb'href="data:image/jpeg;base64,([^\"]+)"', image_svg or b"")
    if not match:
        return None
    try:
        raw = base64.b64decode(match.group(1), validate=True)
        from PIL import Image

        Image.open(BytesIO(raw)).verify()
        return raw
    except Exception:  # noqa: BLE001
        return None


def _photo_style_from_record(record: PostcardRecord) -> str | None:
    match = re.search(rb'data-photo-style="([a-z0-9_-]+)"', record.image_svg or b"")
    if not match:
        return None
    style = match.group(1).decode("ascii", errors="ignore")
    return style if style in SUPPORTED_PHOTO_STYLES else None


class PostcardService:
    def __init__(self, repository: PostcardRepository) -> None:
        self._repository = repository

    def _poi_snapshot(
        self, poi_id: str, language: str
    ) -> tuple[str, float | None, float | None, str | None]:
        """Return poi_name, lat, lng, district. Coordinates are public POI data only."""
        meta = get_poi_metadata(poi_id) or {}
        district = str(meta.get("district") or "") or None
        coords = meta.get("coordinates") or {}
        meta_lat = coords.get("lat")
        meta_lng = coords.get("lng")
        with SessionLocal() as session:
            poi = PoiRepository(session).get_by_id(poi_id)
        if poi is None and not meta:
            raise PostcardError(f"POI not found: {poi_id}")
        fallback_name = (poi.poi_name if poi else None) or str(meta.get("name_zh") or poi_id)
        if language == "en":
            name = str(meta.get("name_en") or "").strip()
            name = name or (fallback_name if not HAN_RE.search(fallback_name) else "Macau stop")
        elif language == "pt":
            name = str(meta.get("name_pt") or meta.get("name_en") or "").strip()
            name = name or (fallback_name if not HAN_RE.search(fallback_name) else "Local de Macau")
        elif language == "zh-TW":
            name = _to_traditional(str(meta.get("name_zh") or fallback_name))
        else:
            name = str(meta.get("name_zh") or fallback_name)
        latitude = float(poi.latitude) if poi is not None else None
        longitude = float(poi.longitude) if poi is not None else None
        if latitude is None and isinstance(meta_lat, (int, float)):
            latitude = float(meta_lat)
        if longitude is None and isinstance(meta_lng, (int, float)):
            longitude = float(meta_lng)
        return name, latitude, longitude, district

    def _route_name(self, route_id: str, language: str) -> str | None:
        template = get_template(route_id)
        if not template:
            return None
        name = template.get("name")
        if not name:
            return None
        value = str(name)
        if language == "en" and HAN_RE.search(value):
            return "Macau itinerary"
        if language == "pt" and HAN_RE.search(value):
            return "Itinerário de Macau"
        if language == "zh-TW":
            return _to_traditional(value)
        return value

    def _reusable_ai_scene(self, poi_id: str) -> bytes | None:
        for candidate in self._repository.list_reusable_scene_candidates(poi_id):
            if _scene_source_from_record(candidate) != "ai":
                continue
            jpeg = _embedded_scene_jpeg(candidate.image_svg)
            if jpeg:
                return jpeg
        return None

    def _stamps(
        self,
        *,
        trip: Trip,
        poi_id: str,
        stop_order: int,
        language: str,
        visited_at: datetime,
    ) -> dict:
        poi_name, latitude, longitude, district = self._poi_snapshot(poi_id, language)
        route_name = self._route_name(trip.route_id, language)
        timestamp_label = _format_timestamp(visited_at, language)
        geo_label = _format_geo_label(
            latitude=latitude,
            longitude=longitude,
            district=district,
            language=language,
        )
        task_label = _format_task_label(
            stop_order=stop_order,
            total_stops=len(trip.stop_poi_ids),
            route_name=route_name,
            language=language,
        )
        return {
            "poi_name": poi_name,
            "visited_at": visited_at,
            "timestamp_label": timestamp_label,
            "geo_label": geo_label,
            "latitude": latitude,
            "longitude": longitude,
            "district": district,
            "route_id": trip.route_id,
            "route_name": route_name,
            "task_label": task_label,
        }

    def _to_response(self, record: PostcardRecord, trip: Trip) -> PostcardResponse:
        stamps = self._stamps(
            trip=trip,
            poi_id=record.poi_id,
            stop_order=record.stop_order,
            language=record.language,
            visited_at=record.created_at,
        )
        # User uploads are always scrubbed; placeholder/AI cards keep photo_scrubbed=False.
        has_user_photo = bool(record.photo_scrubbed)
        scene_source = _scene_source_from_record(record)
        return PostcardResponse(
            postcard_id=record.id,
            trip_id=record.trip_id,
            poi_id=record.poi_id,
            poi_name=stamps["poi_name"],
            stop_order=record.stop_order,
            caption=record.caption,
            caption_source=record.caption_source,
            source_type=record.source_type,
            ai_generated=record.ai_generated,
            language=record.language,
            review_decision=record.review_decision,
            photo_scrubbed=record.photo_scrubbed,
            has_user_photo=has_user_photo,
            scene_source=scene_source,
            photo_style=_photo_style_from_record(record),
            image_url=f"/api/v1/postcards/{record.id}/image",
            created_at=record.created_at,
            visited_at=stamps["visited_at"],
            timestamp_label=stamps["timestamp_label"],
            geo_label=stamps["geo_label"],
            latitude=stamps["latitude"],
            longitude=stamps["longitude"],
            district=stamps["district"],
            route_id=stamps["route_id"],
            route_name=stamps["route_name"],
            task_label=stamps["task_label"],
        )

    def create(
        self,
        trip_id: str,
        poi_id: str,
        photo_bytes: bytes | None,
        language: str,
        *,
        replace: bool = False,
        ai_scene: bool = True,
        photo_style: str | None = None,
    ) -> PostcardResponse:
        if language not in SUPPORTED_LANGUAGES:
            raise PostcardError("unsupported language")
        raw = photo_bytes or b""
        if len(raw) > MAX_UPLOAD_BYTES:
            raise PostcardError("photo exceeds 8 MiB limit")
        requested_style = (photo_style or "").strip().lower() or None
        if requested_style and requested_style not in SUPPORTED_PHOTO_STYLES:
            raise PostcardError("unsupported photo style")
        if requested_style and not raw:
            raise PostcardError("photo style requires an uploaded photo")

        trip = trip_repository.get_trip(trip_id)
        if trip is None:
            raise PostcardNotFoundError(f"Trip not found: {trip_id}")
        if poi_id not in trip.stop_poi_ids:
            raise PostcardError(f"POI is not part of trip {trip_id}: {poi_id}")
        if poi_id not in trip.checked_in_poi_ids:
            raise PostcardError(f"POI must be checked in before postcard generation: {poi_id}")

        existing = self._repository.get_for_trip_poi(trip_id, poi_id)
        if existing is not None:
            existing_source = _scene_source_from_record(existing)
            stale_generated_scene = not raw and existing_source in {"placeholder", "library"}
            if not replace and not stale_generated_scene:
                return self._to_response(existing, trip)
            self._repository.delete(existing.id)
            record_audit(
                kind="postcard.delete",
                status="replaced",
                subject=trip_id,
                metadata={
                    "poi_id": poi_id,
                    "postcard_id": existing.id,
                    "reason": "stale_scene" if stale_generated_scene else "replace",
                },
            )

        created_at = datetime.now(timezone.utc)
        stop_order = trip.stop_poi_ids.index(poi_id)
        stamps = self._stamps(
            trip=trip,
            poi_id=poi_id,
            stop_order=stop_order,
            language=language,
            visited_at=created_at,
        )
        has_user_photo = bool(raw)
        scene_svg: str | None = None
        if has_user_photo:
            try:
                cleaned_photo = scrub(raw)
            except Exception as exc:  # noqa: BLE001
                raise PostcardError("photo must be a valid image") from exc
            photo_scrubbed = True
            scene_source = "user"
            applied_style: str | None = None
            if requested_style:
                styled_photo = stylize_photo_via_qwenpaw(
                    photo_jpeg=cleaned_photo,
                    style=requested_style,
                    poi_name=stamps["poi_name"],
                )
                if styled_photo:
                    # Strip model/output metadata and keep any detected faces blurred.
                    cleaned_photo = scrub(styled_photo)
                    scene_source = "ai_edit"
                    applied_style = requested_style
        else:
            reused_scene = None if replace else self._reusable_ai_scene(poi_id)
            if reused_scene:
                _src, ai_photo, ai_svg = "ai", reused_scene, None
            else:
                try:
                    _src, ai_photo, ai_svg = generate_ai_scene(
                        poi_id=poi_id,
                        poi_name=stamps["poi_name"],
                        district=stamps.get("district"),
                        language=language,
                        ai_scene=True,
                        when=created_at,
                        reuse_cached=not replace,
                    )
                except SceneGenerationError as exc:
                    record_audit(
                        kind="postcard.scene.generate",
                        status="failed",
                        subject=trip_id,
                        agent_id=settings.scene_agent_id or "scene",
                        metadata={"poi_id": poi_id, "language": language},
                    )
                    raise PostcardSceneUnavailableError("POSTCARD_SCENE_UNAVAILABLE") from exc
            if not ai_photo and not ai_svg:
                raise PostcardSceneUnavailableError("POSTCARD_SCENE_UNAVAILABLE")
            cleaned_photo = ai_photo
            scene_svg = ai_svg if not ai_photo else None
            scene_source = _src
            photo_scrubbed = False
            applied_style = None

        caption, caption_source, source_type, ai_generated, review_decision = _caption(
            stamps["poi_name"], language
        )
        record = PostcardRecord(
            id=str(uuid4()),
            trip_id=trip_id,
            poi_id=poi_id,
            stop_order=stop_order,
            caption=caption,
            caption_source=caption_source,
            source_type=source_type,
            ai_generated=ai_generated,
            language=language,
            review_decision=review_decision,
            image_svg=_render_svg(
                photo_jpeg=cleaned_photo,
                scene_svg=scene_svg,
                poi_name=stamps["poi_name"],
                caption=caption,
                timestamp_label=stamps["timestamp_label"],
                geo_label=stamps["geo_label"],
                task_label=stamps["task_label"],
                scene_source=scene_source,
                photo_style=applied_style,
            ),
            photo_scrubbed=photo_scrubbed,
            created_at=created_at,
        )
        saved = self._repository.create(record)
        record_audit(
            kind="postcard.create",
            status="agent" if ai_generated else "template",
            subject=trip_id,
            agent_id="guide" if ai_generated else None,
            decision=review_decision,
            input_chars=len(poi_id) + len(raw),
            output_chars=len(caption),
            metadata={
                "poi_id": poi_id,
                "photo_scrubbed": photo_scrubbed,
                "has_user_photo": has_user_photo,
                "scene_source": scene_source,
                "photo_style_requested": requested_style,
                "photo_style_applied": applied_style,
                "geo_from_poi": True,
                "task_label": stamps["task_label"],
                "replaced": replace,
                "ai_scene_requested": ai_scene,
                "shared_scene_reused": bool(reused_scene) if not has_user_photo else False,
            },
        )
        return self._to_response(saved, trip)

    def validate_scene_prewarm(self, trip_id: str, poi_id: str, language: str) -> None:
        if language not in SUPPORTED_LANGUAGES:
            raise PostcardError("unsupported language")
        trip = trip_repository.get_trip(trip_id)
        if trip is None:
            raise PostcardNotFoundError(f"Trip not found: {trip_id}")
        if poi_id not in trip.stop_poi_ids:
            raise PostcardError(f"POI is not part of trip {trip_id}: {poi_id}")
        if poi_id not in trip.checked_in_poi_ids:
            raise PostcardError(f"POI must be checked in before scene prewarm: {poi_id}")

    def prewarm_scene(self, trip_id: str, poi_id: str, language: str) -> None:
        try:
            self.validate_scene_prewarm(trip_id, poi_id, language)
            if self._reusable_ai_scene(poi_id):
                record_audit(
                    kind="postcard.scene.prewarm",
                    status="reused",
                    subject=trip_id,
                    agent_id=settings.scene_agent_id or "scene",
                    metadata={"poi_id": poi_id, "language": language},
                )
                return
            trip = trip_repository.get_trip(trip_id)
            if trip is None:
                return
            stamps = self._stamps(
                trip=trip,
                poi_id=poi_id,
                stop_order=trip.stop_poi_ids.index(poi_id),
                language=language,
                visited_at=datetime.now(timezone.utc),
            )
            jpeg, _svg = generate_ai_scene_via_qwenpaw(
                poi_id=poi_id,
                poi_name=stamps["poi_name"],
                district=stamps.get("district"),
                language=language,
            )
            record_audit(
                kind="postcard.scene.prewarm",
                status="ok",
                subject=trip_id,
                agent_id=settings.scene_agent_id or "scene",
                metadata={"poi_id": poi_id, "language": language},
            )
        except Exception as exc:  # noqa: BLE001
            logger.info("postcard scene prewarm failed: %s", exc)

    def delete(self, postcard_id: str) -> None:
        record = self._repository.get(postcard_id)
        if record is None:
            raise PostcardNotFoundError(f"Postcard not found: {postcard_id}")
        trip_id = record.trip_id
        poi_id = record.poi_id
        if not self._repository.delete(postcard_id):
            raise PostcardNotFoundError(f"Postcard not found: {postcard_id}")
        record_audit(
            kind="postcard.delete",
            status="ok",
            subject=trip_id,
            metadata={"poi_id": poi_id, "postcard_id": postcard_id},
        )

    def list_by_trip(self, trip_id: str) -> list[PostcardResponse]:
        trip = trip_repository.get_trip(trip_id)
        if trip is None:
            raise PostcardNotFoundError(f"Trip not found: {trip_id}")
        records = self._repository.list_by_trip(trip_id)
        return [self._to_response(record, trip) for record in records]

    def image(self, postcard_id: str) -> bytes:
        record = self._repository.get(postcard_id)
        if record is None:
            raise PostcardNotFoundError(f"Postcard not found: {postcard_id}")
        return _normalize_postcard_svg_layout(record.image_svg)

    def image_png(self, postcard_id: str) -> bytes:
        record = self._repository.get(postcard_id)
        if record is None:
            raise PostcardNotFoundError(f"Postcard not found: {postcard_id}")
        trip = trip_repository.get_trip(record.trip_id)
        if trip is None:
            raise PostcardNotFoundError(f"Trip not found: {record.trip_id}")
        return _render_png(record=record, postcard=self._to_response(record, trip))


postcard_service = PostcardService(postcard_repository)
