# data/ — 种子数据与 schema 说明

Phase 1 最小数据集。团队按 `plan/开发计划与清单.md` Phase 1 扩充：
**目标 6 个旧区 / 30 个文化节点 / ≥6 条主题路线**。

## 文件

| 文件 | 内容 | 对应模型 |
|------|------|----------|
| `pois.json` | 文化节点（POI） | `backend/app/models/poi.py` → `POI` |
| `routes.json` | 预设路线库 | `backend/app/models/route.py` → `Route` |
| `weights.json` | （Phase 1 末生成）离线调研权重表 | `scripts/clean_xhs.py` 产出 |

## POI schema

```
id              字符串，唯一（poi_<拼音/区>）
name_zh/_en/_pt 多语言名称
district        所属旧区
theme[]         主题标签：历史/建筑/美食/摄影/文化
coordinates     { lat, lng }
intro           基本介绍
history         历史背景
architecture    建筑特色
story           文化故事
observation_tips 建议观察角度
suitable_for[]  匹配标签：history/architecture/photo/food/culture/solo/friends/family/relax
source_type     来源分级：official/academic/folklore/ai   ← 落实伦理透明度
```

## Route schema

```
id              唯一
name / theme    名称与主题
duration_label  半日 / 一日 / 夜间散步
duration_hours  预计总用时
walk_distance_km 步行距离
physical_level  low / medium / high
suitable_for[]  用于匹配打分的标签（需与 POI 的 suitable_for 同词表）
nodes[]         { poi_id, order, suggested_stay_min, note, replaceable_with[] }
description     路线说明
```

> `suitable_for` 标签词表务必跨 POI / Route / 用户偏好保持一致，
> 否则 `route_matcher.py` 的匹配打分会失真。

## 数据来源与伦理

- 文化资料以**官方史料**优先，区分 `source_type`；AI 生成或情景演绎须标 `ai`，不作真实史料使用。
- 社交媒体相关数据**仅用团队现有离线数据集**（100 高赞笔记 + 751 评论），不做实时爬取。
  清洗后写入 `weights.json`，详见 `scripts/clean_xhs.py`。
