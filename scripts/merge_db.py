"""把 pois_master.json(xlsx 341)与现有 pois.json(14 文化 POI)合并成一份 live 数据。

决策（读完整数据后修正，见对话 / Task #1）：
- **保留 14 个文化 POI 的 poi_senado ID**，不重映射 routes.json/weights.json。
  weights.json 的 alt_poi_candidates / theme_bias 是手工策展的关系图，按 poi_senado
  键挂——重映射风险高、收益低；ID 不透明，poi_senado 与 poi_NNNN 并存无碍。
- 真正要做的是 **去重 + 富化 + 统一 district**：
  1. 删 4 个错城市（香洲区/油尖旺区/金水区/武侯区，珠海/港/郑/蓉）。
  2. 11 个文化 POI 在 master 有对应记录（6 精确 + 5 模糊），把 master 的
     amap / coordinates / verify_status 并进文化 POI（富化），并从 master 删掉重复。
  3. 3 个文化 POI 无 master 对应（望德堂区 / 路环圣方济各圣堂 / 路环码头），
     district 手工映射到官方堂区。
  4. 所有 district 统一到 8 个官方堂区，供 candidate_selector 重建邻接表。

产出：data/pois.json（覆盖；旧版一次性备份到 data/legacy/pois.legacy.json）。
不影响：data/routes.json、data/weights.json（零改动）。

用法：
    /opt/anaconda3/bin/python3 scripts/merge_db.py
"""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
MASTER = REPO / "data/pois_master.json"
CULTURAL = REPO / "data/pois.json"
LEGACY_DIR = REPO / "data/legacy"
LEGACY_POIS = LEGACY_DIR / "pois.legacy.json"

WRONG_CITIES = {"香洲区", "油尖旺区", "金水区", "武侯区"}  # 珠海 / 香港 / 郑州 / 成都

# 文化 POI 中文名 → master 中文名（模糊对应；精确匹配自动处理，不在此列）
MATCH_MAP = {
    "议事亭前地": "议事亭前地广场",
    "福隆新街": "澳门福隆新街",
    "妈祖阁（妈阁庙）": "妈阁庙",
    "龙环葡韵": "龙环葡韵住宅式博物馆",
    "恩尼斯总统前地": "澳门恩尼斯总统前地",
}

# 无 master 对应的文化 POI → 官方堂区（其余继承 master 的堂区）
CULTURAL_ONLY_DISTRICT = {
    "望德堂区": "望德堂区",
    "路环圣方济各圣堂": "圣方济各堂区",
    "路环码头": "圣方济各堂区",
}

OFFICIAL_DISTRICTS = {
    "花地玛堂区", "花王堂区", "望德堂区", "大堂区",
    "风顺堂区", "嘉模堂区", "路氹填海区", "圣方济各堂区",
}


def main() -> None:
    master_all = json.loads(MASTER.read_text(encoding="utf-8"))["pois"]
    # 幂等：若已备份原始 14 文化版，从备份读，避免把已合并的 pois.json 当 cultural 再喂入
    cultural_src = LEGACY_POIS if LEGACY_POIS.exists() else CULTURAL
    cultural = json.loads(cultural_src.read_text(encoding="utf-8"))["pois"]

    # 1) 删错城市
    master_clean = [p for p in master_all if p.get("district") not in WRONG_CITIES]
    deleted = len(master_all) - len(master_clean)

    # 1b) 修正 district='[]'(amap 返回空列表)等：从名字推断官方堂区；无信息量的占位条目丢弃
    fixed: list[dict] = []
    dropped_generic = 0
    for p in master_clean:
        d = p.get("district")
        if d in OFFICIAL_DISTRICTS:
            fixed.append(p)
            continue
        hit = next((off for off in OFFICIAL_DISTRICTS if off in name), None) if (name := p.get("name_zh", "")) else None
        if hit:
            p = dict(p); p["district"] = hit
            fixed.append(p)
        else:
            dropped_generic += 1  # district 空/[] 且名字也无堂区线索 → 丢
    master_clean = fixed

    master_by_name = {p["name_zh"]: p for p in master_clean}

    # 2) 文化 POI 富化 + 去重
    enriched: list[dict] = []
    matched_master_names: set[str] = set()
    report: list[tuple[str, str, str, str]] = []  # (kind, cultural, master, district)

    for cp in cultural:
        cname = cp["name_zh"]
        mname = cname if cname in master_by_name else MATCH_MAP.get(cname)
        ep = dict(cp)  # 保留全部文化内容 + poi_senado id
        if mname and mname in master_by_name:
            mp = master_by_name[mname]
            matched_master_names.add(mname)
            ep["coordinates"] = mp.get("coordinates") or cp.get("coordinates", {})
            ep["amap"] = mp.get("amap", {})
            ep["verify_status"] = mp.get("verify_status", "")
            ep["district"] = mp.get("district") or cp.get("district")  # 官方堂区
            report.append(("match", cname, mname, ep["district"]))
        else:
            if cname in CULTURAL_ONLY_DISTRICT:
                ep["district"] = CULTURAL_ONLY_DISTRICT[cname]
            report.append(("cultural-only", cname, "", ep["district"]))
        enriched.append(ep)

    # 3) master-only = 清洗后 master 减去被合并的重复
    master_only = [p for p in master_clean if p["name_zh"] not in matched_master_names]

    merged = enriched + master_only

    # 4) 校验：district 是否都在官方堂区内
    bad_district = [p for p in merged if p.get("district") not in OFFICIAL_DISTRICTS]
    id_set = {p["id"] for p in merged}
    assert len(id_set) == len(merged), "ID 冲突！"

    # 5) 一次性备份原始 pois.json（14 文化版）
    LEGACY_DIR.mkdir(parents=True, exist_ok=True)
    if not LEGACY_POIS.exists():
        LEGACY_POIS.write_text(CULTURAL.read_text(encoding="utf-8"), encoding="utf-8")
        backed_up = True
    else:
        backed_up = False

    out = {
        "_comment": (
            "合并后的 live POI 库：14 文化 POI（poi_senado，含 intro/history/...）"
            "+ master 地理编码 POI（poi_NNNN，文化内容待讲解 agent 补）。"
            "district 统一为官方堂区。旧版备份见 data/legacy/pois.legacy.json。"
        ),
        "pois": merged,
    }
    CULTURAL.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")

    # 6) 报告
    dist_counter = Counter(p.get("district") or "(空)" for p in merged)
    verify_counter = Counter(p.get("verify_status") or "(空)" for p in merged)
    print(f"读取 master={len(master_all)} cultural={len(cultural)}")
    print(f"删错城市: {deleted}; 丢无信息量占位: {dropped_generic} → master_clean={len(master_clean)}")
    print(f"文化 POI 富化（合并 master 重复）: {len(matched_master_names)}")
    print(f"master-only（thin，poi_NNNN）: {len(master_only)}")
    print(f"合并后总 POI: {len(merged)}")
    print(f"旧版备份: {'已写 ' + str(LEGACY_POIS.relative_to(REPO)) if backed_up else '已存在，跳过'}")
    print("\n— 去重明细:")
    for kind, cn, mn, dist in report:
        arrow = f"  ←master→ {mn}" if mn else ""
        print(f"  [{kind}] {cn}{arrow}  (district={dist})")
    print(f"\n— district 分布（官方堂区）: {dict(dist_counter)}")
    print(f"— verify_status 分布: {dict(verify_counter)}")
    if bad_district:
        print(f"⚠️ {len(bad_district)} 个 POI district 非官方堂区，需人工修正:")
        for p in bad_district[:20]:
            print(f"   {p['id']} {p['name_zh']} → {p.get('district')!r}")
    else:
        print("✅ 所有 district 均在 8 个官方堂区内")


if __name__ == "__main__":
    main()
