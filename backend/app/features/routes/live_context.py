"""Official live travel context with explicit safe network fallbacks."""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from html import unescape
import re
import threading
import time
from typing import Any, Callable
from xml.etree import ElementTree

import httpx

SMG_CURRENT_WEATHER_URL = "https://www.smg.gov.mo/webdiss/c_actualweather_xml.php"
SMG_7DAY_FORECAST_URLS = {
    "zh-CN": "https://xml.smg.gov.mo/c_7daysforecast.xml",
    "zh-TW": "https://xml.smg.gov.mo/c_7daysforecast.xml",
    "en": "https://xml.smg.gov.mo/e_7daysforecast.xml",
    "pt": "https://xml.smg.gov.mo/p_7daysforecast.xml",
}
MGTO_EVENT_CALENDAR_URL = "https://www.macaotourism.gov.mo/en/events/calendar"
MGTO_WHATSON_URL = "https://www.macaotourism.gov.mo/en/events/whatson"
OPEN_METEO_FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
DSAT_BUS_INFO_URL = "https://www.dsat.gov.mo/bus"
MGTO_ATTRACTIONS_URL = "https://www.macaotourism.gov.mo/en/sightseeing"
MAINLAND_CHINA_HOLIDAY_SOURCE_URL = (
    "https://www.gov.cn/zhengce/zhengceku/202511/content_7047091.htm"
)
_CACHE_SECONDS = 600
_cache: dict[str, tuple[float, dict[str, Any]]] = {}
_cache_lock = threading.Lock()
_UA = "MacauStoryWalk/0.1 (competition travel context)"

MAINLAND_CHINA_HOLIDAYS_2026 = (
    {
        "id": "cn_2026_new_year",
        "name_zh": "元旦假期",
        "name_en": "Mainland China New Year holiday",
        "start": date(2026, 1, 1),
        "end": date(2026, 1, 3),
        "crowd_level": "high",
        "note_zh": "短途跨境游需求较高，口岸和核心景点建议预留机动时间。",
        "note_en": "Short-haul cross-border trips increase; allow extra time at ports and core sights.",
    },
    {
        "id": "cn_2026_spring_festival",
        "name_zh": "春节假期",
        "name_en": "Mainland China Spring Festival holiday",
        "start": date(2026, 2, 15),
        "end": date(2026, 2, 23),
        "crowd_level": "very_high",
        "note_zh": "内地春节黄金周通常显著推高访澳客流，建议避开大三巴、议事亭前地、官也街下午高峰。",
        "note_en": "Spring Festival Golden Week can sharply raise Macao visitor volume; avoid afternoon peaks at core sights.",
    },
    {
        "id": "cn_2026_qingming",
        "name_zh": "清明节假期",
        "name_en": "Mainland China Qingming holiday",
        "start": date(2026, 4, 4),
        "end": date(2026, 4, 6),
        "crowd_level": "high",
        "note_zh": "三天连休带来周边短途游增量，热门旧城节点可能偏挤。",
        "note_en": "The three-day break can raise short-trip demand; popular old-town nodes may be busy.",
    },
    {
        "id": "cn_2026_labour_day",
        "name_zh": "劳动节假期",
        "name_en": "Mainland China Labour Day holiday",
        "start": date(2026, 5, 1),
        "end": date(2026, 5, 5),
        "crowd_level": "very_high",
        "note_zh": "五一假期通常是跨境旅游高峰，建议优先安排清晨旧城或室内博物馆备选。",
        "note_en": "Labour Day is typically a cross-border travel peak; prefer early old-town walks or indoor museum backups.",
    },
    {
        "id": "cn_2026_dragon_boat",
        "name_zh": "端午节假期",
        "name_en": "Mainland China Dragon Boat Festival holiday",
        "start": date(2026, 6, 19),
        "end": date(2026, 6, 21),
        "crowd_level": "high",
        "note_zh": "端午连休叠加夏季天气，热门街区与室内商业区都可能升温。",
        "note_en": "The Dragon Boat break plus summer weather can raise demand for both popular streets and indoor areas.",
    },
    {
        "id": "cn_2026_mid_autumn",
        "name_zh": "中秋节假期",
        "name_en": "Mainland China Mid-Autumn Festival holiday",
        "start": date(2026, 9, 25),
        "end": date(2026, 9, 27),
        "crowd_level": "high",
        "note_zh": "中秋连休适合夜景与餐饮消费，旧城夜间与路氹演出区可能更繁忙。",
        "note_en": "Mid-Autumn trips can raise night-view and dining demand; old-town evenings and Cotai events may be busier.",
    },
    {
        "id": "cn_2026_national_day",
        "name_zh": "国庆假期",
        "name_en": "Mainland China National Day holiday",
        "start": date(2026, 10, 1),
        "end": date(2026, 10, 7),
        "crowd_level": "very_high",
        "note_zh": "十一黄金周是访澳高峰，建议路线主动避开核心打卡点下午时段，并预留口岸排队时间。",
        "note_en": "National Day Golden Week is a major Macao travel peak; avoid core photo spots in afternoons and allow port queue time.",
    },
)


def _cached(key: str, loader: Callable[[], dict[str, Any]]) -> dict[str, Any]:
    now = time.monotonic()
    with _cache_lock:
        hit = _cache.get(key)
        if hit and now - hit[0] < _CACHE_SECONDS:
            return hit[1]
    value = loader()
    with _cache_lock:
        _cache[key] = (now, value)
    return value


def _fetch(url: str) -> str | None:
    try:
        response = httpx.get(
            url,
            headers={"User-Agent": _UA, "Accept": "application/xml,text/html"},
            follow_redirects=True,
            timeout=4.0,
            trust_env=False,
        )
        return response.text if response.status_code == 200 else None
    except httpx.HTTPError:
        return None


def _fetch_json(url: str, params: dict[str, Any]) -> dict[str, Any] | None:
    try:
        response = httpx.get(
            url,
            params=params,
            headers={"User-Agent": _UA, "Accept": "application/json"},
            follow_redirects=True,
            timeout=4.0,
            trust_env=False,
        )
        return response.json() if response.status_code == 200 else None
    except (httpx.HTTPError, ValueError):
        return None


def _weather() -> dict[str, Any]:
    source = {"name": "Macao Meteorological and Geophysical Bureau", "url": SMG_CURRENT_WEATHER_URL}
    raw = _fetch(SMG_CURRENT_WEATHER_URL)
    if not raw:
        return {"status": "unavailable", "source": source}
    try:
        root = ElementTree.fromstring(raw)
        values = {
            re.sub(r"[^a-z0-9]", "", element.tag.lower()): (element.text or "").strip()
            for element in root.iter()
            if (element.text or "").strip()
        }
    except ElementTree.ParseError:
        return {"status": "unavailable", "source": source}

    def first(*keys: str) -> str | None:
        return next((values[key] for key in keys if values.get(key)), None)

    return {
        "status": "ok",
        "temperature_c": first("temperature", "temp", "macautemp"),
        "humidity_percent": first("humidity", "relativehumidity", "macauhumidity"),
        "rainfall_mm": first("rainfall", "hourlyrainfall", "rain"),
        "condition": first("weather", "weatherdesc", "weatherdescription"),
        "warning": first("warning", "warningmessage", "signal"),
        "source": source,
        "fetched_at": datetime.now(timezone.utc).isoformat(),
    }


_WEATHER_CODE_ZH = {
    0: "晴朗",
    1: "大致晴朗",
    2: "局部多云",
    3: "多云",
    45: "有雾",
    48: "雾凇",
    51: "微雨",
    53: "小雨",
    55: "中雨",
    56: "冻雨",
    57: "冻雨",
    61: "小雨",
    63: "中雨",
    65: "大雨",
    66: "冻雨",
    67: "冻雨",
    71: "小雪",
    73: "中雪",
    75: "大雪",
    77: "雪粒",
    80: "阵雨",
    81: "阵雨",
    82: "强阵雨",
    85: "阵雪",
    86: "强阵雪",
    95: "雷暴",
    96: "雷暴伴冰雹",
    99: "强雷暴伴冰雹",
}

_WEATHER_CODE_EN = {
    0: "clear",
    1: "mostly clear",
    2: "partly cloudy",
    3: "cloudy",
    45: "fog",
    48: "rime fog",
    51: "light drizzle",
    53: "drizzle",
    55: "dense drizzle",
    56: "freezing drizzle",
    57: "freezing drizzle",
    61: "light rain",
    63: "rain",
    65: "heavy rain",
    66: "freezing rain",
    67: "freezing rain",
    71: "light snow",
    73: "snow",
    75: "heavy snow",
    77: "snow grains",
    80: "showers",
    81: "showers",
    82: "heavy showers",
    85: "snow showers",
    86: "heavy snow showers",
    95: "thunderstorm",
    96: "thunderstorm with hail",
    99: "heavy thunderstorm with hail",
}

_RAIN_CODES = {
    51,
    53,
    55,
    56,
    57,
    61,
    63,
    65,
    66,
    67,
    80,
    81,
    82,
    95,
    96,
    99,
}


def _condition_label(code: int | None, language: str) -> str:
    if code is None:
        return "weather pending" if language == "en" else "天气待确认"
    if language == "en":
        return _WEATHER_CODE_EN.get(code, "weather pending")
    return _WEATHER_CODE_ZH.get(code, "天气待确认")


def _parse_float(value: Any) -> float | None:
    try:
        if value is None or value == "":
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _daily_value(daily: dict[str, Any], key: str, index: int) -> Any:
    values = daily.get(key) or []
    try:
        return values[index]
    except (TypeError, IndexError):
        return None


def _smg_source(language: str, issued_at: str | None = None) -> dict[str, Any]:
    names = {
        "zh-CN": "澳门地球物理气象局",
        "zh-TW": "澳門地球物理氣象局",
        "en": "Macao Meteorological and Geophysical Bureau",
        "pt": "Direcção dos Serviços Meteorológicos e Geofísicos de Macau",
    }
    source: dict[str, Any] = {
        "name": names.get(language, names["en"]),
        "url": SMG_7DAY_FORECAST_URLS.get(language, SMG_7DAY_FORECAST_URLS["en"]),
    }
    if issued_at:
        source["issued_at"] = issued_at
    return source


def _smg_forecast(target: date, trip_days: int, language: str) -> dict[str, Any]:
    end = target + timedelta(days=max(1, min(5, trip_days)) - 1)
    source_url = SMG_7DAY_FORECAST_URLS.get(language, SMG_7DAY_FORECAST_URLS["en"])
    raw = _fetch(source_url)
    if not raw:
        return {"status": "unavailable", "days": [], "source": _smg_source(language)}
    try:
        root = ElementTree.fromstring(raw)
    except ElementTree.ParseError:
        return {"status": "unavailable", "days": [], "source": _smg_source(language)}

    issued_at = root.findtext(".//IssuedTime") or root.findtext(".//SysPubdate")
    days: list[dict[str, Any]] = []
    for item in root.findall(".//WeatherForecast"):
        day_text = (item.findtext("ValidFor") or "").strip()
        try:
            forecast_date = date.fromisoformat(day_text)
        except ValueError:
            continue
        if not target <= forecast_date <= end:
            continue

        temperatures: dict[str, float | None] = {}
        for temperature in item.findall("Temperature"):
            kind = (temperature.findtext("Type") or "").strip()
            temperatures[kind] = _parse_float(temperature.findtext("Value"))
        description = " ".join((item.findtext("WeatherDescription") or "").split())
        days.append(
            {
                "date": day_text,
                "weather_code": None,
                "source_weather_code": _parse_float(item.findtext("WeatherStatus")),
                "temperature_max_c": temperatures.get("1"),
                "temperature_min_c": temperatures.get("2"),
                "precipitation_probability_percent": None,
                "precipitation_sum_mm": None,
                "wind_speed_max_kmh": None,
                "condition": description or None,
                "rain_signal": any(
                    term in description.lower()
                    for term in ("rain", "shower", "雨", "aguaceiro", "chuva")
                ),
                "storm_signal": any(
                    term in description.lower()
                    for term in ("thunder", "雷", "trovoada")
                ),
            }
        )

    expected_days = (end - target).days + 1
    if len(days) != expected_days:
        return {"status": "unavailable", "days": [], "source": _smg_source(language, issued_at)}
    return {
        "status": "ok",
        "days": days,
        "source": _smg_source(language, issued_at),
        "fetched_at": datetime.now(timezone.utc).isoformat(),
    }


def _open_meteo_forecast(target: date, trip_days: int) -> dict[str, Any]:
    end = target + timedelta(days=max(1, min(5, trip_days)) - 1)
    params = {
        "latitude": 22.1987,
        "longitude": 113.5439,
        "timezone": "Asia/Macau",
        "start_date": target.isoformat(),
        "end_date": end.isoformat(),
        "daily": ",".join(
            [
                "weather_code",
                "temperature_2m_max",
                "temperature_2m_min",
                "precipitation_probability_max",
                "precipitation_sum",
                "wind_speed_10m_max",
            ]
        ),
    }
    source = {"name": "Open-Meteo forecast", "url": OPEN_METEO_FORECAST_URL}
    data = _fetch_json(OPEN_METEO_FORECAST_URL, params)
    if not data or not isinstance(data.get("daily"), dict):
        return {"status": "unavailable", "days": [], "source": source}

    daily = data["daily"]
    dates = daily.get("time") or []
    days: list[dict[str, Any]] = []
    for index, day in enumerate(dates):
        try:
            code = int((daily.get("weather_code") or [])[index])
        except (TypeError, ValueError, IndexError):
            code = None
        days.append(
            {
                "date": day,
                "weather_code": code,
                "temperature_max_c": _parse_float(_daily_value(daily, "temperature_2m_max", index)),
                "temperature_min_c": _parse_float(_daily_value(daily, "temperature_2m_min", index)),
                "precipitation_probability_percent": _parse_float(
                    _daily_value(daily, "precipitation_probability_max", index)
                ),
                "precipitation_sum_mm": _parse_float(_daily_value(daily, "precipitation_sum", index)),
                "wind_speed_max_kmh": _parse_float(_daily_value(daily, "wind_speed_10m_max", index)),
            }
        )
    return {
        "status": "ok" if days else "unavailable",
        "days": days,
        "source": source,
        "fetched_at": datetime.now(timezone.utc).isoformat(),
    }


def _forecast(target: date, trip_days: int, language: str) -> dict[str, Any]:
    official = _smg_forecast(target, trip_days, language)
    if official.get("status") == "ok":
        return official
    return _open_meteo_forecast(target, trip_days)


def _weather_advice_text(
    *,
    language: str,
    umbrella: bool,
    sunscreen: bool,
    indoor_backup: bool,
    source_status: str,
) -> list[str]:
    if source_status != "ok":
        if language == "en":
            return ["Weather is temporarily unavailable; check official alerts before departure."]
        if language == "pt":
            return ["O tempo está temporariamente indisponível; confirme os avisos oficiais antes de sair."]
        if language == "zh-TW":
            return ["暫時未能取得天氣預報；出發前請再確認官方天氣及警告。"]
        return ["暂时未能取得天气预报；出发前请再确认官方天气及预警。"]

    if language == "en":
        tips = []
        if umbrella:
            tips.append("Bring an umbrella or light raincoat.")
        if sunscreen:
            tips.append("Pack sunscreen and water.")
        if indoor_backup:
            tips.append("Keep an indoor backup route for heavy rain or storms.")
        return tips or ["Weather looks suitable for walking; keep checking alerts before you go."]
    if language == "pt":
        tips = []
        if umbrella:
            tips.append("Leve guarda-chuva ou capa de chuva leve.")
        if sunscreen:
            tips.append("Leve protetor solar e água.")
        if indoor_backup:
            tips.append("Prepare uma rota interior alternativa para chuva forte ou trovoada.")
        return tips or ["O tempo parece adequado para caminhar; confirme os avisos antes de sair."]
    if language == "zh-TW":
        tips = []
        if umbrella:
            tips.append("建議帶傘或輕便雨衣。")
        if sunscreen:
            tips.append("建議準備防曬和飲用水。")
        if indoor_backup:
            tips.append("如遇大雨或雷暴，建議保留室內備選路線。")
        return tips or ["天氣看起來適合步行；出發前仍請留意官方預警。"]

    tips = []
    if umbrella:
        tips.append("建议带伞或轻便雨衣。")
    if sunscreen:
        tips.append("建议准备防晒和饮用水。")
    if indoor_backup:
        tips.append("如遇大雨或雷暴，建议保留室内备选路线。")
    return tips or ["天气看起来适合步行；出发前仍请留意官方预警。"]


def get_weather_advice(
    travel_date: str | None,
    trip_days: int | None = None,
    language: str = "zh-CN",
) -> dict[str, Any]:
    """Return Macau forecast summary and packing/walking advice for the preference page."""
    try:
        target = date.fromisoformat(travel_date) if travel_date else date.today()
    except ValueError:
        target = date.today()
    days_count = max(1, min(5, int(trip_days or 1)))
    forecast = _cached(
        f"forecast:{target.isoformat()}:{days_count}:{language}",
        lambda: _forecast(target, days_count, language),
    )

    days = forecast.get("days") or []
    source_status = "ok" if forecast.get("status") == "ok" and days else "unavailable"
    umbrella = any(
        day.get("rain_signal")
        or (day.get("weather_code") in _RAIN_CODES)
        or ((day.get("precipitation_probability_percent") or 0) >= 40)
        or ((day.get("precipitation_sum_mm") or 0) >= 0.5)
        for day in days
    )
    sunscreen = any((day.get("temperature_max_c") or 0) >= 30 for day in days)
    indoor_backup = any(
        day.get("storm_signal")
        or day.get("weather_code") in {65, 82, 95, 96, 99}
        or ((day.get("precipitation_sum_mm") or 0) >= 10)
        for day in days
    )

    display_days = [
        {
            **day,
            "condition": day.get("condition")
            or _condition_label(day.get("weather_code"), language),
        }
        for day in days
    ]
    if display_days:
        first = display_days[0]
        summary = {
            "zh-CN": f"{first['date']} 澳门预计{first['condition']}",
            "zh-TW": f"{first['date']} 澳門預計{first['condition']}",
            "en": f"Macau forecast for {first['date']}: {first['condition']}",
            "pt": f"Previsão para Macau em {first['date']}: {first['condition']}",
        }.get(language, f"{first['date']} 澳门预计{first['condition']}")
    else:
        summary = {
            "zh-CN": "澳门天气暂时无法获取",
            "zh-TW": "澳門天氣暫時無法取得",
            "en": "Macau weather is temporarily unavailable",
            "pt": "O tempo em Macau está temporariamente indisponível",
        }.get(language, "澳门天气暂时无法获取")

    return {
        "travel_date": target.isoformat(),
        "trip_days": days_count,
        "status": source_status,
        "summary": summary,
        "days": display_days,
        "advice": _weather_advice_text(
            language=language,
            umbrella=umbrella,
            sunscreen=sunscreen,
            indoor_backup=indoor_backup,
            source_status=source_status,
        ),
        "flags": {
            "umbrella": umbrella,
            "sunscreen": sunscreen,
            "indoor_backup": indoor_backup,
        },
        "source": forecast.get("source"),
        "fetched_at": forecast.get("fetched_at"),
    }


def _localized(value: dict[str, Any], language: str, key: str) -> str:
    if language == "en":
        return str(value.get(f"{key}_en") or value.get(f"{key}_zh") or "")
    return str(value.get(f"{key}_zh") or value.get(f"{key}_en") or "")


def _level_rank(level: str) -> int:
    return {"low": 0, "medium": 1, "high": 2, "very_high": 3}.get(level, 0)


def _max_level(levels: list[str]) -> str:
    if not levels:
        return "low"
    return max(levels, key=_level_rank)


def _event_crowd_level(events: dict[str, Any]) -> str:
    excerpts = " ".join(str(item) for item in events.get("events") or []).lower()
    if not excerpts:
        return "low"
    high_terms = (
        "concert",
        "演唱会",
        "演唱會",
        "fireworks",
        "烟花",
        "煙花",
        "grand prix",
        "格兰披治",
        "格蘭披治",
        "marathon",
        "马拉松",
        "馬拉松",
    )
    if any(term in excerpts for term in high_terms):
        return "high"
    return "medium"


def get_crowd_advice(
    travel_date: str | None,
    *,
    trip_days: int | None = None,
    language: str = "zh-CN",
) -> dict[str, Any]:
    """Estimate crowd pressure from public holidays, weekends, and official events."""
    try:
        target = date.fromisoformat(travel_date) if travel_date else date.today()
    except ValueError:
        target = date.today()
    days_count = max(1, min(5, int(trip_days or 1)))
    factors: list[dict[str, Any]] = []
    levels: list[str] = []

    for offset in range(days_count):
        current = target + timedelta(days=offset)
        for holiday in MAINLAND_CHINA_HOLIDAYS_2026:
            if holiday["start"] <= current <= holiday["end"]:
                levels.append(str(holiday["crowd_level"]))
                factors.append(
                    {
                        "kind": "mainland_china_holiday",
                        "date": current.isoformat(),
                        "level": holiday["crowd_level"],
                        "name": _localized(holiday, language, "name"),
                        "note": _localized(holiday, language, "note"),
                    }
                )
        if current.weekday() >= 5:
            levels.append("medium")
            factors.append(
                {
                    "kind": "weekend",
                    "date": current.isoformat(),
                    "level": "medium",
                    "name": "Weekend" if language == "en" else "周末",
                    "note": (
                        "Weekend demand can raise crowds around Senado Square, Ruins of St. Paul's, Rua do Cunha, and Cotai venues."
                        if language == "en"
                        else "周末会推高议事亭前地、大三巴、官也街和路氹演出场馆周边人流。"
                    ),
                }
            )

    events = _cached(f"events:{target.isoformat()}", lambda: _events(target))
    event_level = _event_crowd_level(events)
    if event_level != "low":
        levels.append(event_level)
        factors.append(
            {
                "kind": "official_event_calendar",
                "date": target.isoformat(),
                "level": event_level,
                "name": "Macao event calendar" if language == "en" else "澳门活动日历",
                "note": (
                    "Official event calendar excerpts suggest extra demand near event venues."
                    if language == "en"
                    else "官方活动日历命中当日活动，场馆周边可能出现额外人流。"
                ),
                "events": events.get("events") or [],
                "source": events.get("source"),
            }
        )

    level = _max_level(levels)
    if level in {"high", "very_high"}:
        notes = [
            "建议核心景点安排在上午或傍晚后，下午避开大三巴、议事亭前地、官也街等高热节点。",
            "口岸、热门餐饮和大型演出散场时段需预留机动时间。",
        ]
        if language == "en":
            notes = [
                "Put core sights in the morning or after early evening; avoid high-demand nodes in the afternoon.",
                "Allow buffer time for ports, popular dining spots, and post-event departures.",
            ]
    elif level == "medium":
        notes = [
            "预计人流中等偏高，建议保留一两个低人流替代点。",
        ]
        if language == "en":
            notes = ["Crowds may be moderate; keep one or two quieter backup stops."]
    else:
        notes = [
            "未命中明显高峰信号；仍需以现场排队和官方通告为准。",
        ]
        if language == "en":
            notes = ["No strong peak signal detected; still follow on-site queues and official notices."]

    return {
        "travel_date": target.isoformat(),
        "trip_days": days_count,
        "status": "estimated",
        "level": level,
        "factors": factors,
        "notes": notes,
        "sources": [
            {
                "name": "Macao Government Tourism Office events",
                "url": MGTO_WHATSON_URL,
            },
            {
                "name": "State Council 2026 public holiday notice",
                "url": MAINLAND_CHINA_HOLIDAY_SOURCE_URL,
            },
        ],
    }


def get_live_travel_advice(
    travel_date: str | None,
    *,
    trip_days: int | None = None,
    language: str = "zh-CN",
) -> dict[str, Any]:
    """Return the current live-consultation bundle for route planning."""
    weather = get_weather_advice(travel_date, trip_days=trip_days, language=language)
    crowd = get_crowd_advice(travel_date, trip_days=trip_days, language=language)
    transport_note = {
        "zh-CN": "出发前建议查询“巴士报站”或高德地图 App，了解巴士到站和路线资讯。",
        "zh-TW": "出發前建議查詢「巴士報站」或高德地圖 App，了解巴士到站和路線資訊。",
        "en": (
            "For bus arrivals and route planning, use Bus Reporting or the AMap app "
            "before departure."
        ),
        "pt": (
            "Antes de partir, consulte a aplicação Bus Reporting ou AMap para ver "
            "as chegadas dos autocarros e planear o percurso."
        ),
    }.get(language, "出发前建议查询“巴士报站”或高德地图 App，了解巴士到站和路线资讯。")
    opening_hours_note = {
        "zh-CN": "景点开放时间会因场馆和假期变动，出发前建议查询景点官方网站。",
        "zh-TW": "景點開放時間會因場館和假期變動，出發前建議查詢景點官方網站。",
        "en": (
            "Opening hours can change by venue and holiday; check the attraction's "
            "official website before departure."
        ),
        "pt": (
            "Os horários de funcionamento podem variar conforme o local e os feriados; "
            "consulte o site oficial da atração antes de partir."
        ),
    }.get(language, "景点开放时间会因场馆和假期变动，出发前建议查询景点官方网站。")
    return {
        "travel_date": weather["travel_date"],
        "trip_days": weather["trip_days"],
        "weather": weather,
        "crowd": crowd,
        "transport": {
            "status": "advice-only",
            "notes": [transport_note],
            "sources": [],
        },
        "opening_hours": {
            "status": "advice-only",
            "notes": [opening_hours_note],
            "sources": [],
        },
    }


def _events(target: date) -> dict[str, Any]:
    source = {
        "name": "Macao Government Tourism Office events",
        "url": f"{MGTO_WHATSON_URL}?month={target.strftime('%Y%m')}",
    }
    raw_calendar = _fetch(MGTO_EVENT_CALENDAR_URL)
    raw_month = _fetch(source["url"])
    if not raw_calendar and not raw_month:
        return {"status": "unavailable", "events": [], "source": source}
    text = re.sub(
        r"\s+",
        " ",
        unescape(re.sub(r"<[^>]+>", " ", " ".join(item for item in (raw_calendar, raw_month) if item))),
    ).strip()
    excerpts: list[str] = []
    date_patterns = (
        f"{target.strftime('%B')} {target.day}",
        f"{target.strftime('%B')} {target.day:02d}",
        f"{target.strftime('%b')} {target.day}",
        f"{target.strftime('%b')} {target.day:02d}",
    )
    for pattern in date_patterns:
        start = text.lower().find(pattern.lower())
        if start >= 0:
            excerpt = text[max(0, start - 100) : start + 240].strip()
            if excerpt and excerpt not in excerpts:
                excerpts.append(excerpt)

    # The What's On listing commonly renders dates as "29-30/8". Match the
    # full range so a concert influences only its actual performance dates.
    day_range = re.compile(rf"\b(\d{{1,2}})(?:\s*-\s*(\d{{1,2}}))?/{target.month}\b")
    for match in day_range.finditer(text):
        start_day = int(match.group(1))
        end_day = int(match.group(2) or start_day)
        if not start_day <= target.day <= end_day:
            continue
        excerpt = text[max(0, match.start() - 100) : match.end() + 240].strip()
        if excerpt and excerpt not in excerpts:
            excerpts.append(excerpt)
    return {
        "status": "ok",
        "events": excerpts[:3],
        "source": source,
        "fetched_at": datetime.now(timezone.utc).isoformat(),
    }


def get_live_route_context(travel_date: str | None) -> dict[str, Any]:
    """Return source-attributed weather and official event signals for a route."""
    try:
        target = date.fromisoformat(travel_date) if travel_date else date.today()
    except ValueError:
        target = date.today()
    weather = _cached("weather", _weather)
    events = _cached(f"events:{target.isoformat()}", lambda: _events(target))
    notes: list[str] = []
    if weather.get("status") == "ok":
        details = [
            f"{weather['temperature_c']}°C" if weather.get("temperature_c") else None,
            weather.get("condition"),
            f"雨量 {weather['rainfall_mm']}mm" if weather.get("rainfall_mm") else None,
        ]
        summary = "，".join(item for item in details if item)
        if summary:
            notes.append(f"澳门气象局实时天气：{summary}")
        if weather.get("warning"):
            notes.append(f"气象提醒：{weather['warning']}")
    else:
        notes.append("暂未取得澳门气象局实时天气；请以现场官方预警为准")
    if events.get("status") == "ok" and events.get("events"):
        notes.append("澳门旅游局日历显示当日附近有公开活动，热门区域可能较繁忙")
    elif events.get("status") == "unavailable":
        notes.append("暂未取得澳门旅游局活动日历；未据此作实时人流判断")
    return {
        "travel_date": target.isoformat(),
        "weather": weather,
        "events": events,
        "notes": notes,
        "crowd_signal": "event-proxy" if events.get("events") else "unavailable",
    }
