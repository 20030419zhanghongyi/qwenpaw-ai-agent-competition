# Scripts — 数据清洗与批处理

| 脚本 | 职责 | 阶段 |
|------|------|------|
| `clean_xhs.py` | 小红书离线数据 → `data/weights.json` 权重表 | Phase 1（待实现清洗逻辑） |
| `background/report_assets/scripts/*.py` | 调研图表生成（已有，见 `background/`） | 已完成 |

## clean_xhs.py

- **输入**：`background/raw_data/xhs/xhs_search_*.xlsx`（100 高赞笔记 + 751 评论）
- **输出**：`data/weights.json`，含 `poi_heat` / `pain_points` / `nicome_candidates`
- **约束**：只用现有离线数据集，不做实时爬取

```bash
python scripts/clean_xhs.py
```

> 后续可加 `build_routes.py`：根据权重表半自动生成/校验预设路线库 `data/routes.json`。
