"""预设路线数据模型。

对应 data/routes.json。Phase 1 先用静态预设路线库，
Phase 3 由 QwenPaw 路线微调 Agent 在此基础上增删节点 / 调整顺序。
"""

from pydantic import BaseModel


class RouteNode(BaseModel):
    poi_id: str
    order: int                          # 在路线中的顺序
    suggested_stay_min: int             # 建议停留分钟
    note: str | None = None             # 该节点说明
    replaceable_with: list[str] = []    # 可替换节点 poi_id（人流拥挤时备选）


class Route(BaseModel):
    id: str
    name: str
    theme: str                          # 文化 / 摄影 / 美食 / 亲子 ...
    duration_label: str                 # 半日 / 一日 / 夜间散步
    duration_hours: float               # 预计总用时
    walk_distance_km: float             # 步行距离
    physical_level: str                 # low / medium / high
    suitable_for: list[str] = []        # 命中的偏好标签，用于匹配打分
    nodes: list[RouteNode]
    description: str
