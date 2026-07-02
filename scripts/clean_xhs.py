"""小红书离线数据清洗脚本（Phase 1 占位）。

输入：background/raw_data/xhs/xhs_search_*.xlsx（100 高赞笔记 + 751 评论，2023–2025）
输出：data/weights.json —— 预计算权重表，供路线匹配与讲解主题优先级使用。

⚠️  仅处理团队**现有离线数据集**，不做实时爬取（见 README 与 AI 伦理文档）。

weight 表结构（建议）：
{
  "poi_heat":   { "<poi_id>": float },   # 提及热度
  "pain_points":{ "<poi_id|district>": ["排队","累",...] },
  "niche_candidates": ["<poi_id>", ...]  # 小众推荐候选
}

运行：python scripts/clean_xhs.py
"""

from __future__ import annotations

import logging
import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = REPO_ROOT / "background" / "raw_data" / "xhs"
OUT = REPO_ROOT / "data" / "weights.json"

log = logging.getLogger("scripts.clean_xhs")


def find_xlsx() -> Path | None:
    matches = sorted(RAW_DIR.glob("xhs_search_*.xlsx"))
    return matches[0] if matches else None


def main() -> int:
    logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
    xlsx = find_xlsx()
    if not xlsx:
        log.warning("未找到离线数据 %s。请把原始 xlsx 放入 background/raw_data/xhs/", RAW_DIR)
        return 0

    log.info("读取：%s", xlsx)
    # TODO(Phase 1, owner: 数据组肖懿宣):
    #   1) pandas 读 notes / comments sheet
    #   2) 关键词命中统计：「攻略/路线/排队/人多/累/暴走/回头路/历史/文化/介绍/为什么」
    #   3) POI 提及抽取（与 data/pois.json 的 name_zh 对齐 → poi_id）
    #   4) 生成 poi_heat / pain_points / niche_candidates 写入 data/weights.json
    print(f"✓ 找到数据源 {xlsx.name}，等待实现清洗逻辑后产出 {OUT.relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
