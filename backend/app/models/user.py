"""用户与偏好数据模型。

遵循「最小必要」原则（见 AI 伦理文档）：注册采集 email + 昵称 + 国家 + 语言，
其余均为可选偏好，用于路线配对。
"""

from typing import Any

from pydantic import BaseModel, field_validator


# 语言代码：简中 / 繁中 / 英文 / 葡文
SUPPORTED_LANGS = ("zh-CN", "zh-TW", "en", "pt")

# 多日游天数：模板互补线有限，限制在 2–5
TRIP_DAYS_MIN = 2
TRIP_DAYS_MAX = 5
TRIP_DAYS_DEFAULT = 3


def clamp_trip_days(value: int | None) -> int | None:
    """Clamp multi-day count into the supported range; None stays None."""
    if value is None:
        return None
    return max(TRIP_DAYS_MIN, min(TRIP_DAYS_MAX, int(value)))


class Preference(BaseModel):
    """用户偏好输入 —— 路线配对的依据。"""
    duration: str = "half-day"           # half-day / full-day / evening / multi-day / custom
    party_size: int = 1
    travel_type: list[str] = []          # solo / friends / family / relax ...
    interests: list[str] = []            # history / architecture / food / photo ...
    themes: list[str] = []               # heritage / architecture / photo / food / family / leisure / cotai
    physical: list[str] = []             # normal / less-walk / no-backtrack
    language: str = "zh-CN"
    # 进出澳门口岸（poi_id）；可选，用于锚定行程首尾
    entry_port: str | None = None
    exit_port: str | None = None
    # YYYY-MM-DD，用于匹配当日活动／拥堵估计；缺省由匹配层按「今天」处理
    travel_date: str | None = None
    # 多日游天数（仅 duration=multi-day 时有意义）；匹配层用作 top_k
    trip_days: int | None = None

    @field_validator("trip_days", mode="before")
    @classmethod
    def validate_trip_days(cls, value: Any) -> int | None:
        if value is None or value == "":
            return None
        try:
            return clamp_trip_days(int(value))
        except (TypeError, ValueError):
            return None


class UserProfile(BaseModel):
    user_id: str
    email: str | None = None
    phone: str | None = None
    name: str
    language: str = "zh-CN"
    country: str | None = None
    verification_status: str = "unverified"  # unverified | pending | verified
    preference: Preference | None = None
    preference_memory: dict[str, Any] | None = None
