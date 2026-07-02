"""路线数据访问包装。

为什么单独包一层：
- 让 routes 功能目录内部尽量不要直接散落依赖 app.db.data
- 后续切到 Postgres / pgvector / hybrid planner 时，这里是最自然的替换点
"""

from app.db.data import get_route as _get_route
from app.db.data import load_routes as _load_routes


def list_templates() -> list[dict]:
    """返回全部预设路线模板。"""
    return _load_routes()


def get_template(route_id: str) -> dict | None:
    """按 id 获取单条预设路线模板。"""
    return _get_route(route_id)

