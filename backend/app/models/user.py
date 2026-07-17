"""用户与偏好数据模型。

遵循「最小必要」原则（见 AI 伦理文档）：注册只采集登录标识 + 语言，
其余均为可选偏好，用于路线配对。
"""

from pydantic import BaseModel


# 语言代码：简中 / 繁中 / 英文 / 葡文
SUPPORTED_LANGS = ("zh-CN", "zh-TW", "en", "pt")


class Preference(BaseModel):
    """用户偏好输入 —— 路线配对的依据。"""
    duration: str = "half-day"           # half-day / full-day / evening / multi-day / custom
    party_size: int = 1
    travel_type: list[str] = []          # solo / friends / family / relax ...
    interests: list[str] = []            # history / architecture / food / photo ...
    themes: list[str] = []               # heritage / architecture / photo / food / family / leisure / cotai
    physical: list[str] = []             # normal / less-walk / no-backtrack
    language: str = "zh-CN"


class UserProfile(BaseModel):
    user_id: str
    name: str | None = None
    language: str = "zh-CN"
    preference: Preference | None = None
