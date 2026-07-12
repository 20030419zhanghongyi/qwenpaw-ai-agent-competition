# data/ — 种子数据与 schema 说明

Phase 1 最小数据集。团队按 `plan/开发计划与清单.md` Phase 1 扩充：
**目标 6 个旧区 / 30 个文化节点 / ≥6 条主题路线**。

## 文件

| 文件 | 内容 | 对应模型 |
|------|------|----------|
| `pois.json` | 文化节点（POI） | `backend/app/models/poi.py` → `POI` |
| `routes.json` | 预设路线库 | `backend/app/models/route.py` → `Route` |
| `weights.json` | （Phase 1 末生成）离线调研权重表 | `scripts/clean_xhs.py` 产出 |

## weights schema

```json
{
  "poi_heat": { "<poi_id>": 0 },
  "crowd_risk": { "<poi_id>": 0 },
  "pain_point_tags": { "<poi_id>": ["排队", "人多"] },
  "alt_poi_candidates": { "<poi_id>": ["<poi_id>", "<poi_id>"] },
  "theme_bias": {
    "文化|摄影|美食": { "<poi_id>": 0 }
  }
}
```

- `poi_heat`：离线提及热度，用于模板打分和候选点加权。
- `crowd_risk`：热门时段拥挤风险，适合在轻松 / 亲子 / 少走路路线里做降权。
- `pain_point_tags`：游客抱怨标签，如 `排队`、`人多`、`台阶多`。
- `alt_poi_candidates`：人工或离线调研整理的可替换候选点。
- `theme_bias`：按路线主题给候选点加额外偏好，避免“同主题但不够代表”的点排太前。

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
verify_status   核验状态：待核验 / AI生成·待核验 / 已核验
```

## POI 文化内容的来源（official vs ai）

`pois.json` 共 339 条 POI，文化内容分两类来源，靠 `source_type` 区分（伦理透明度）：

| 来源 | 条数 | source_type | verify_status | 说明 |
|------|------|-------------|---------------|------|
| 人工富化（官方/学术史料） | 14 | `official` | `待核验` | 精选核心节点，手工核对写入 |
| AI 生成（讲解 agent 补全） | 325 | `ai` | `AI生成·待核验` | 由 QwenPaw 讲解能力批量补全，**人工核验前不作权威史料** |

### AI 富化怎么来的

`scripts/generate_guide_content.py` 调本地 QwenPaw（`default` agent；待 `guide` agent 建好后用
`--agent guide`），对 5 个文化字段为空的「瘦 POI」逐条补全 `intro`/`history`/`architecture`/
`story`/`observation_tips`，并发跑（`--workers 8`）、幂等可续跑（intro 非空即跳过）、每条原子写回。

纪律（对齐 `skills/macau-guide/SKILL.md`）：
- **不编史料**：资料不足的字段写概括描述或留空（故 `story` 仅 ~140/325 非空，属正常）；
- **易变信息低置信**：开放时间/票价/活动不给具体时间表，写「以现场为准」；
- **冷门点位如实说明**：公开资料匮乏者，`confidence ≤ 0.4` 且正文写「公开资料有限」
  （全集中 13 条 <0.4，均为此类）。

每条生成的审计记录（id / confidence / token / 延迟 / 状态）落盘于
`data/legacy/guide_enrichment_log.jsonl`，可复核、可重算。geo 数据（coordinates / amap）
不受富化影响，325 条全保留。


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
