"""POI（文化节点）数据模型。

对应 data/pois.json 中每条记录的 schema。
source_type 用于落实 AI 伦理透明度：区分内容来源。
"""

from pydantic import BaseModel


class Coordinates(BaseModel):
    lat: float
    lng: float


class POI(BaseModel):
    id: str
    name_zh: str
    name_en: str | None = None
    name_pt: str | None = None
    district: str                       # 所属街区
    theme: list[str] = []               # 历史 / 建筑 / 美食 / 摄影 ...
    coordinates: Coordinates
    intro: str                          # 基本介绍
    history: str                        # 历史背景
    architecture: str                   # 建筑特色
    story: str                          # 文化故事
    observation_tips: str               # 建议观察角度
    suitable_for: list[str] = []        # 适合人群 / 兴趣
    # 来源类型：official / academic / folklore / ai
    source_type: str = "official"
