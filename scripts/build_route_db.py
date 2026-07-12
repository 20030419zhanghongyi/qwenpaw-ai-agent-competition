"""把 Macau_Route_Database_simple.xlsx 转成 route 代码可用的 JSON。

非破坏性：产出 data/pois_master.json 与 data/route_templates.json，
不覆盖现有 data/pois.json / data/routes.json（那 14 个 POI 带文化内容，需另行合并）。

来源：background/raw_data/macau_route/Macau_Route_Database_simple.xlsx
  - POI_Master            → POI 身份 + 高德地理编码（341 行）
  - Preset_Route_Templates → 预设路线模板（67 行 = 多模板 × 多节点）

⚠️ 启发式标注（待人工/agent 精修）：
  - theme[] / suitable_for[] 由 amap_type 关键词推导，非人工标注
  - 文化内容字段（intro/history/story/...）暂留空，由讲解 agent 后续补（source_type=ai）
  - district 用高德官方堂区名，与 candidate_selector.ADJACENT_DISTRICTS 的非正式片区名
    存在词表差异，合并时需统一（见脚本末尾报告）

用法：
    /opt/anaconda3/bin/python3 scripts/build_route_db.py
"""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

import pandas as pd

REPO = Path(__file__).resolve().parents[1]
XLSX = REPO / "background/raw_data/macau_route/Macau_Route_Database_simple.xlsx"
OUT_POIS = REPO / "data/pois_master.json"
OUT_ROUTES = REPO / "data/route_templates.json"

# ---- amap_type 关键词 → theme[] / suitable_for[] 推导（启发式）----
# suitable_for 词表须与 data/README 的 POI/Route/偏好词表一致：
# history/architecture/photo/food/culture/solo/friends/family/relax
TYPE_RULES: list[tuple[tuple[str, ...], list[str], list[str]]] = [
    # (amap_type 关键词, theme[], suitable_for[])
    (("世界遗产", "风景名胜", "公园广场", "城市广场"), ["历史", "建筑", "摄影"], ["history", "architecture", "photo", "culture", "solo", "family"]),
    (("博物馆", "科教文化", "展览馆"), ["文化", "历史"], ["culture", "history", "family"]),
    (("教堂", "寺庙", "宗教", "修道院"), ["历史", "建筑", "文化"], ["history", "architecture", "culture"]),
    (("道路名", "街巷", "交通地名"), ["摄影", "文化"], ["photo", "solo", "friends"]),
    (("餐饮", "美食", "小吃", "餐厅", "茶餐厅"), ["美食"], ["food", "relax"]),
    (("购物", "商业街", "商场"), [], ["relax", "friends"]),
    (("海滨", "海滩", "自然"), ["摄影"], ["photo", "relax", "family"]),
]


def derive_tags(amap_type: str) -> tuple[list[str], list[str]]:
    """从 amap_type 文本推导 theme / suitable_for。"""
    text = str(amap_type or "")
    themes: set[str] = set()
    suitable: set[str] = set()
    for keywords, t, s in TYPE_RULES:
        if any(k in text for k in keywords):
            themes.update(t)
            suitable.update(s)
    if not themes:
        themes.add("文化")
    if not suitable:
        suitable.update(["culture"])
    return sorted(themes), sorted(suitable)


def build_pois(df: pd.DataFrame) -> tuple[list[dict], dict]:
    pois = []
    verify_counter = Counter()
    district_counter = Counter()
    type_counter = Counter()
    for _, r in df.iterrows():
        amap_type = r.get("amap_type")
        themes, suitable = derive_tags(amap_type)
        poi = {
            "id": str(r["poi_id"]),
            "name_zh": str(r["poi_name"]).strip(),
            "name_en": "",
            "name_pt": "",
            "alias": ("" if pd.isna(r.get("alias")) else str(r["alias"])),
            "district": ("" if pd.isna(r.get("amap_district")) else str(r["amap_district"]).strip()),
            "theme": themes,
            "suitable_for": suitable,
            "coordinates": {
                "lat": (None if pd.isna(r.get("latitude")) else float(r["latitude"])),
                "lng": (None if pd.isna(r.get("longitude")) else float(r["longitude"])),
            },
            "amap": {
                "poi_id": ("" if pd.isna(r.get("amap_poi_id")) else str(r["amap_poi_id"])),
                "address": ("" if pd.isna(r.get("amap_address")) else str(r["amap_address"])),
                "type": ("" if pd.isna(amap_type) else str(amap_type)),
                "typecode": ("" if pd.isna(r.get("amap_typecode")) else str(r["amap_typecode"])),
            },
            # 文化内容暂缺：待讲解 agent 补，source_type=ai
            "intro": "",
            "history": "",
            "architecture": "",
            "story": "",
            "observation_tips": "",
            "source_type": "official",  # 地理编码来自高德，身份可信；文化内容缺
            "verify_status": ("" if pd.isna(r.get("verify_status")) else str(r["verify_status"])),
        }
        pois.append(poi)
        verify_counter[poi["verify_status"] or "(空)"] += 1
        district_counter[poi["district"] or "(空)"] += 1
        type_counter[(poi["amap"]["type"] or "(空)")[:20]] += 1
    stats = {
        "verify_status": verify_counter,
        "districts": district_counter,
        "top_amap_types": type_counter.most_common(10),
    }
    return pois, stats


# 节点角色 → 默认停留分钟（对齐 route_constructor._default_stay_min 的量级）
ROLE_STAY_MIN = {"起点": 20, "景点": 30, "街巷": 15, "文化": 25, "美食": 40, "休息": 20, "终点": 15}


def stay_for_role(role: str) -> int:
    role = str(role or "")
    for k, v in ROLE_STAY_MIN.items():
        if k in role:
            return v
    return 25


def physical_from_route_type(route_type: str) -> str:
    t = str(route_type or "")
    if "低强度" in t or "舒适" in t or "轻松" in t:
        return "low"
    if "高强度" in t or "暴走" in t:
        return "high"
    return "medium"


def build_routes(df: pd.DataFrame) -> tuple[list[dict], dict]:
    routes: dict[str, dict] = {}
    matched = 0
    unmatched = 0
    for _, r in df.iterrows():
        tid = str(r["template_id"]).strip()
        if tid not in routes:
            routes[tid] = {
                "id": tid.lower(),
                "name": str(r["template_name"]).strip(),
                "route_type_raw": str(r.get("route_type") or "").strip(),
                "physical_level": physical_from_route_type(r.get("route_type")),
                "route_area": str(r.get("route_area") or "").strip(),
                "description": str(r.get("template_description") or "").strip(),
                "nodes": [],
                "_unmatched_nodes": 0,
            }
        poi_id = r.get("poi_id")
        status = str(r.get("poi_match_status") or "")
        if pd.isna(poi_id) or not str(poi_id).strip() or status != "已匹配":
            routes[tid]["_unmatched_nodes"] += 1
            unmatched += 1
            continue
        routes[tid]["nodes"].append({
            "poi_id": str(poi_id).strip(),
            "order": int(r["sequence"]),
            "suggested_stay_min": stay_for_role(r.get("node_role")),
            "note": str(r.get("node_role") or "").strip(),
            "replaceable_with": [],
        })
        matched += 1
    for rt in routes.values():
        rt["nodes"].sort(key=lambda n: n["order"])
    route_list = list(routes.values())
    stats = {"templates": len(route_list), "matched_nodes": matched, "unmatched_nodes": unmatched}
    return route_list, stats


def main() -> None:
    print(f"读取: {XLSX}")
    pois_df = pd.read_excel(XLSX, sheet_name="POI_Master")
    routes_df = pd.read_excel(XLSX, sheet_name="Preset_Route_Templates")

    pois, poi_stats = build_pois(pois_df)
    routes, route_stats = build_routes(routes_df)

    OUT_POIS.write_text(json.dumps({"_comment": "由 scripts/build_route_db.py 从 xlsx 生成；文化内容待补", "pois": pois}, ensure_ascii=False, indent=2), encoding="utf-8")
    OUT_ROUTES.write_text(json.dumps({"_comment": "由 scripts/build_route_db.py 从 xlsx 生成；未匹配节点已剔除", "routes": routes}, ensure_ascii=False, indent=2), encoding="utf-8")

    # 与现有 pois.json(14 个带文化内容的 POI)按中文名比对
    existing = json.loads((REPO / "data/pois.json").read_text(encoding="utf-8"))
    existing_names = {p["name_zh"] for p in existing["pois"]}
    overlap = [p["name_zh"] for p in pois if p["name_zh"] in existing_names]

    print(f"\n✅ 写出 {OUT_POIS.relative_to(REPO)}  ({len(pois)} POI)")
    print(f"✅ 写出 {OUT_ROUTES.relative_to(REPO)} ({route_stats['templates']} 模板, "
          f"{route_stats['matched_nodes']} 已匹配节点, {route_stats['unmatched_nodes']} 未匹配已剔除)")
    print(f"\n— verify_status 分布: {dict(poi_stats['verify_status'])}")
    print(f"— district 值(高德堂区): {dict(poi_stats['districts'])}")
    print(f"— 与现有 14 个文化 POI 中文名重合: {len(overlap)} 个 → {overlap}")
    print("\n⚠️ 待决策(见终端/对话): ID 方案 / district 词表统一 / theme 标签精修 / 文化内容补全")


if __name__ == "__main__":
    main()
