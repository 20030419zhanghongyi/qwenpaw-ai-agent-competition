"""加载仓库 data/ 目录下的种子数据（POI、路线、权重）。

Phase 1：纯 JSON 内存读取，带 lru_cache。
后续 Phase 3 接入 pgvector / Postgres 时，把这里替换为 DB 查询即可，
上层接口 (load_pois / load_routes / get_poi) 保持不变。
"""

import json
from functools import lru_cache
from pathlib import Path

from app.core.config import settings


@lru_cache
def _read_json(name: str) -> dict | list:
    path: Path = settings.data_dir / name
    if not path.exists():
        raise FileNotFoundError(
            f"数据文件不存在：{path}。请先按 plan/开发计划与清单.md Phase 1 准备数据。"
        )
    with path.open(encoding="utf-8") as f:
        return json.load(f)


@lru_cache
def load_pois() -> list[dict]:
    """返回全部 POI。"""
    return _read_json("pois.json")["pois"]


@lru_cache
def load_routes() -> list[dict]:
    """返回全部预设路线。"""
    return _read_json("routes.json")["routes"]


@lru_cache
def load_weights() -> dict:
    """返回离线调研预计算权重表（POI 热度 / 拥挤 / 小众候选）。"""
    try:
        return _read_json("weights.json")
    except FileNotFoundError:
        return {}


@lru_cache
def load_ports() -> list[dict]:
    """返回口岸目录（进出澳门锚定用）。"""
    try:
        return list(_read_json("ports.json").get("ports") or [])
    except FileNotFoundError:
        return []


@lru_cache
def load_events() -> list[dict]:
    """返回人工维护的活动日程（演唱会等拥堵估计）。"""
    try:
        return list(_read_json("events.json").get("events") or [])
    except FileNotFoundError:
        return []


def get_port(poi_id: str) -> dict | None:
    for port in load_ports():
        if port.get("poi_id") == poi_id:
            return port
    return None


def get_poi(poi_id: str) -> dict | None:
    for p in load_pois():
        if p["id"] == poi_id:
            return p
    return None


def get_route(route_id: str) -> dict | None:
    for r in load_routes():
        if r["id"] == route_id:
            return r
    return None
