# skills/ —— 仓库级技能源（非伦理类）

本目录存放面向 QwenPaw agent 的**技能源**（`SKILL.md`），平行于 `ethics/qwenpaw-skills/`（伦理类）。

```
skills/
├── route-adjust/SKILL.md        # P1：路线微调 agent（NL 偏好 → 结构化意图 JSON）
├── requirement-understand/SKILL.md  # 需求理解 agent（NL → Preference JSON）
├── macau-guide/SKILL.md         # P2：文化讲解 agent（POI 资料 → 有据讲解 + 来源/置信）
├── photo-recognize/SKILL.md     # P4：拍照识别 agent（图 → {描述,候选POI,置信} JSON）
└── postcard-scene/SKILL.md      # 明信片场景插画（参考实景 → 四时段 SVG）
```

## 部署到 QwenPaw（开发期）

开发期用「文件夹丢 skill_pool」的方式批量加载（plan.md §5）。

> ⚠️ **2026-07-12 实测纠正**：早期文档说「丢进 `~/.qwenpaw/skill_pool/` → `qwenpaw skills list`
> 自动发现」——**不成立**。`qwenpaw app` 启动**不扫描** pool 目录，`qwenpaw skills list` 只列
> 已挂到某 agent 的技能，`qwenpaw skills install` 只收 http(s) URL 不收本地路径。丢进去的文件夹不会
> 进清单 `skill_pool/skill.json`，Console 技能网格也看不到。**必须显式触发 reconcile**：

```bash
# 1. 复制技能源到 QwenPaw 技能池
cp -R skills/route-adjust skills/requirement-understand skills/macau-guide skills/photo-recognize ~/.qwenpaw/skill_pool/

# 2. 校验 SKILL.md 格式通过（safe=True 才会被登记）
qwenpaw skills test ~/.qwenpaw/skill_pool/route-adjust

# 3. 触发 pool reconcile：扫盘 → 写进 skill_pool/skill.json（source=customized）
#    方式 A（API，推荐）：app 在跑时调一次即可
curl -X POST http://127.0.0.1:8088/api/skills/pool/refresh
#    方式 B：Console → Skills 页若有 Refresh 按钮，点它
#    之后刷新 Console 页面，route-adjust 就出现在技能网格里

# 4. 在 Console Create New Agent / Skills 页给目标 agent 勾选启用该技能
```

## 当前项目 Agent / Skill 映射（2026-07-13 已验证）

运行态统一使用 `aliyun-tokenplan-intl/qwen3.6-plus`；各 Agent 已经真实调用烟测，不只是写入配置。

| Agent ID | 名称 | 已启用技能 | 额外能力 |
|---|---|---|---|
| `route` | 路线微调 | `route-adjust` | 结构化 RouteAdjustment，失败回落规则版 |
| `intent` | 需求理解 | `requirement-understand`、`fairness-gate` | 结构化 Preference |
| `guide` | 文化讲解 | `macau-guide`、`source-attribution`、`anti-sycophancy` | RAG 取料 + 来源/置信度 |
| `photo` | 拍照识别 | `photo-recognize`、`source-attribution` | 多模态 + 内置 `view_image` 工具 |
| `scene` | 明信片场景插画 | `postcard-scene` | 多模态 + `view_image`；先看参考实景再画四时段 SVG |
| `reviewer` | 独立审核 | `content-safety-review` | pass / revise / block 独立裁定 |

> `source-attribution` 不承担独立审核；生成结果仍由 `reviewer` 做后置安全裁定。

## 在 QwenPaw 里建路线 agent（P1 手动步骤）—— ✅ 已完成 + 端到端验证（2026-07-12）

CLI 默认不在 PATH 时，用 **Console** 建：

1. Console → Create New Agent：name `路线微调`，agent-id `route`，挑一个已配的 text 模型
2. 确认 `qwenpaw agents list` / `GET /api/agents` 能看到 `route`
3. 给该 agent 启用 `route-adjust` 技能（按上节「部署」先 reconcile 进清单）
4. 仓库 `.env` 设 `ROUTE_AGENT_ENABLED=true`，重启后端 → `/routes/adjust` 走 agent 驱动

> **验证状态**：已完成。`route` agent + `route-adjust` 技能就位，thin prompt（不带 schema、靠技能
> system prompt）返回干净结构化 JSON；`POST /api/v1/routes/adjust` 实测 `source=agent`，agent 把
> 「少走点路」翻成 `physical:less-walk` + `remove_tail`，排线引擎据此裁末端、压到 2.4km。
>
> **两个坑（已踩过）**：
> - **技能不自动发现**：见上节，必须 `POST /api/skills/pool/refresh`。
> - **模型 provider 401**：建 agent 时若被分到 key 失效的 provider，会 `MODEL_UNAUTHORIZED_ACCESS`、
>   `completion_tokens:0`、返回空串且秒退（~1.5s）。换到可用 provider（如 default 用的那个）即通。
>   症状：空返回 + 秒退 + `qwenpaw.log` 里 `openai.AuthenticationError 401`。

## 在 QwenPaw 里建需求理解 agent（手动步骤）—— ✅ 已完成 + 端到端验证（2026-07-13）

需求理解 agent（`intent`）的技能源已就位（`skills/requirement-understand/SKILL.md`），与 route/guide 平行：

1. Console → Create New Agent：name `需求理解`，agent-id `intent`，挑已配的 text 模型
2. `cp -R skills/requirement-understand ~/.qwenpaw/skill_pool/` → `qwenpaw skills test ~/.qwenpaw/skill_pool/requirement-understand` → `curl -X POST http://127.0.0.1:8088/api/skills/pool/refresh`（同 route/guide，**不自动发现**）
3. 给该 agent 启用 `requirement-understand` 技能
4. 仓库 `.env` 设 `INTENT_AGENT_ENABLED=true` → `POST /api/v1/intent/parse` 走 agent 驱动（失败降级规则版）

> **验证状态**：已完成。thin prompt（不带 schema、靠技能 system prompt）返回干净 Preference JSON；
> `POST /api/v1/intent/parse` 实测 `source=agent`，agent 把「下午带老人少走路，看建筑」翻成
> `{travel_type:["family"], physical:["less-walk"], interests:["architecture"], duration:"half-day"}`，
> 「晚上一个人去拍拍照，别绕路」翻成 `{duration:"evening", travel_type:["solo"], interests:["photo"], physical:["no-backtrack"]}`。
>
> **两个坑（route agent 已踩过，同样适用）**：技能不自动发现（见上节，必须 `pool/refresh`）；
> 模型 provider 401（建 agent 时分到失效 key 会秒退空返回，换可用 provider）。

> `requirement-understand` 输出严格 Preference JSON
> （`duration/party_size/travel_type/interests/physical/language`），字段对齐
> `backend/app/models/user.py`——与 route-adjust 同一套「结构化输出 + 失败降级」纪律。

## 在 QwenPaw 里建独立审核 agent（手动步骤）—— ✅ 已完成 + 端到端验证（2026-07-13）

独立审核 agent（`reviewer`）的技能 `content-safety-review` **已在 pool 里**（2026-07-13 已随 ethics 4 技能一起 reconcile），
故只需建 agent + 挂技能，无需再 cp/refresh：

1. Console → Create New Agent：name `独立审核`，agent-id `reviewer`，挑已配的 text 模型
2. 给该 agent 启用 `content-safety-review` 技能（技能已在 pool，Console 刷新即可看到）
3. 仓库 `.env` 设 `REVIEWER_AGENT_ENABLED=true` → `POST /api/v1/review/content` 走 agent 驱动（失败降级规则版）

> **验证状态**：已完成。`POST /api/v1/review/content` 三 case 实测 `source=agent`：干净内容 `pass`；
> 「制于1908…肯定最豪华」（绝对化无来源）`revise`（命中「不编造 + 附置信度」红线）；「拨打120…
> 出示身份证银行卡号」`block`——agent 甚至**比规则版更深**：抓到澳门急救应拨 999 而非 120（大陆号码，
> 地理错可延误救援），并把紧急场景索要银行卡号定性为「诈骗诱导」，需记审计日志并通知内容责任人。
>
> **为什么必须独立 agent**：content-safety-review 硬规则「审核者只审核、不改写正文，改写交回
> 原生成 agent」—— 挂在 guide/photo 上会让生成者与审核者同体，违背设计。故 reviewer 独立存在，
> 生成方（guide/photo）的输出 pipe 到 `/review/content` 做上线前 pass/revise/block 把关。
>
> **验证目标**：`POST /api/v1/review/content` 实测 `source=agent`，agent 对含编造史料 / 安全隐患 /
> 越界（紧急救援 / 索要个人信息）的内容判 `block`，对过度自信无来源的断言判 `revise`，干净内容 `pass`。
>
> **坑**（route/intent 已踩过，同样适用）：技能不自动发现（content-safety-review 已 reconcile 过）；
> 模型 provider 401（建 agent 分到失效 key 会秒退空返回，换可用 provider）。

## 在 QwenPaw 里建讲解 agent（P2）—— ✅ 已建 + 端到端验证（2026-07-13，API 建档）

讲解 agent（`guide`）的后端与运行态配置均已落地：
- `backend/app/agents/guide_agent.py`（调 QwenPaw `guide` agent，输出 `{text, source_type, confidence, ai_generated, language}`）
- `backend/app/features/guide/api.py`：`/guide/photo` 的 `_explain()` seam 已接通 RAG + guide agent；
  新增 `POST /api/v1/guide/generate`（POI 名/id + 偏好 → 讲解）
- RAG 已是 **Phase 3 pgvector 语义检索**（不再是 Phase 1 关键词）：339 个 POI 经 DashScope
  `text-embedding-v3` 向量化入库（`rag/ingest.py`），`rag/retrieve.py` 走余弦 top-k（库空/报错回落关键词）
- 讲解素材：candidate_poi 已点名 → `get_poi_material` 精确取整 POI；否则 `retrieve()` 向量兜底

**端到端已验证**（2026-07-13）：运行态 `guide` 使用
`aliyun-tokenplan-intl/qwen3.6-plus`，启用 `macau-guide` / `source-attribution` /
`anti-sycophancy`。真实请求返回结构化讲解、`source_type=official` 与合理置信度，
即取料→prompt→LLM→JSON→GuideExplanation 全通。

运行态配置的复现步骤：
1. Console → Create New Agent：name `文化讲解`，agent-id `guide`，挑已配的 text 模型
2. `cp -R skills/macau-guide ~/.qwenpaw/skill_pool/` →
   `qwenpaw skills test ~/.qwenpaw/skill_pool/macau-guide` →
   `curl -X POST http://127.0.0.1:8088/api/skills/pool/refresh`（同 route/intent，**技能不自动发现**）
3. 给该 agent 启用 `macau-guide` 技能（讲解类，对齐 `ethics/qwenpaw-skills/source-attribution`）
4. `.env` 设 `GUIDE_AGENT_ENABLED=true` →
   `curl -X POST localhost:8000/api/v1/guide/generate -H 'Content-Type: application/json' -d '{"poi":"议事亭前地","interests":["history","architecture"]}'`
   → `source:"agent"`、`text` 非空讲解；`/guide/photo` 的 `explanation` 也随之有值

> `macau-guide` 输出严格 JSON（沉浸式伴侣字段 + `{text, audio_script, source_type, confidence, ai_generated, language}`）：
> 易变信息（开放时间/活动）置信度 ≤0.5 且正文「以现场为准」，不编史料——
> 与路线技能同一套「结构化输出 + 失败降级」纪律。
>
> **前置：pgvector 要在跑**。讲解取料走 `retrieve()`（向量），需 `macau-pg` 容器在线：
> `docker start macau-pg`（首次起库 + ingest 见 `rag/README.md`）。库空时 `retrieve` 自动回落关键词，不挂。

## 在 QwenPaw 里建明信片场景 agent（scene）—— 技能源已就位

专用 agent：先 `view_image` 看后端下好的实景参考图，再输出四时段明信片 SVG。
与 `photo`（识别 JSON）分工不同——`scene` **只画图**。

```bash
# 1. 技能进池 + reconcile
cp -R skills/postcard-scene ~/.qwenpaw/skill_pool/
curl -X POST http://127.0.0.1:8088/api/skills/pool/refresh

# 2. 建 agent（多模态模型；与 photo 同 provider）
curl -X POST http://127.0.0.1:8088/api/agents \
  -H 'Content-Type: application/json' \
  -d '{
    "id": "scene",
    "name": "明信片场景",
    "active_model": {"provider_id": "aliyun-tokenplan-intl", "model": "qwen3.6-plus"},
    "skill_names": ["postcard-scene"],
    "language": "zh"
  }'

# 3. 确认 view_image 已启用（内置工具，默认开）
# 4. 批量：先研究断点，再生成
cd backend
python scripts/generate_postcard_scenes.py --only-routed --research-only
python scripts/generate_postcard_scenes.py --only-routed --agent scene
```

> 断点文件：`data/postcard_scenes/_checkpoint.json`（研究阶段写完即可暂停，之后续跑生成）。

## 在 QwenPaw 里建拍照识别 agent（P4）—— ✅ 已建 + 端到端验证（2026-07-13，API 建档）

> **验证状态**：已完成。**全程用 API 建档，未手点 Console**：
> 1. `cp -R skills/photo-recognize ~/.qwenpaw/skill_pool/` → `curl -X POST http://127.0.0.1:8088/api/skills/pool/refresh`（技能进池，`source=customized`）
> 2. `POST /api/agents`（body `{id:"photo", name:"拍照识别", active_model:{provider_id:"aliyun-tokenplan-intl", model:"qwen3.6-plus"}, skill_names:["photo-recognize","source-attribution"], language:"zh"}`）→ HTTP 201
> 3. 验证：`active_model=qwen3.6-plus`（多模态）、`view_image.enabled=true`（**内置工具不是 skill**，默认开、每个 agent 自动注册，技能网格里找不到是正常的）、`photo-recognize` / `source-attribution` 技能均为 `enabled:true`
> 4. `.env` `PHOTO_AGENT_ENABLED=true` + 重启后端
>
> **端到端实测**（合成图：红顶黄墙建筑+太阳）：`POST /api/v1/guide/photo` → `source:"agent"`、`scrubbed:true`、`description` 精准；`candidate_poi:null`+低置信（非澳门 POI 正确回退）；讲解 seam 与 guide→reviewer 管道均已跑通。
>
> **真实图片评估**：2026-07-13 已冻结 20 条评测集（12 条澳门 POI 正样本 + 8 条负样本），
> before/after 规则分从 **0.925 提升到 1.000**（20/20 满分通过），产物见
> `harness/results/scores_photo-*.json` 和 `harness/reports/photo-agent-tuning.md`。

拍照识别 agent（`photo`）的技能源已就位（`skills/photo-recognize/SKILL.md`），与 route/intent 平行。
**关键差异：本 agent 必须挂多模态模型 + 启用 `view_image` 工具。**

> **机制（2026-07-13 实测确认）**：QwenPaw agent **不**通过内联 image content block 看图，而是用
> 自带的 `view_image` 工具读取「**本地文件路径**」。后端 `features/guide/api.py` 把脱敏图写成临时
> 文件、把绝对路径发给 `photo` agent，agent 自行 `view_image` 后输出 JSON。
> 实测：`{type:"image",image:<data-uri>}` 格式 console-chat 虽接受但模型收不到图、只提示「用
> view_image / 给文件路径或 URL」；`{type:"image_url",...}` 格式直接空回。故「临时文件路径 +
> view_image」是唯一通路。

1. Console → Create New Agent：name `拍照识别`，agent-id `photo`
2. **模型选「支持视觉/多模态」的那个**。当前实测使用
   `aliyun-tokenplan-intl/qwen3.6-plus`；若模型实际支持视觉却被报非多模态，在提供者设置里把
   `supports_multimodal` 设为 `true`。
3. **确认该 agent 启用了 `view_image` 工具**（agent 工具集里勾上——这是它看图的唯一途径）。
4. `cp -R skills/photo-recognize ~/.qwenpaw/skill_pool/` →
   `qwenpaw skills test ~/.qwenpaw/skill_pool/photo-recognize` →
   `curl -X POST http://127.0.0.1:8088/api/skills/pool/refresh`（同 route/intent，**技能不自动发现**）
5. 给该 agent 启用 `photo-recognize` 技能
6. 仓库 `.env` 设 `PHOTO_AGENT_ENABLED=true` → `POST /api/v1/guide/photo` 走 photo agent
   （失败降级：返回 `confidence:0` + `error`，不 500）

> **验证目标**（已达成，见上方状态块）：`curl -F file=@澳门建筑.jpg http://127.0.0.1:8000/api/v1/guide/photo` →
> `source:"agent"`、`description` 非空、`candidate_poi`/`confidence` 合理。讲解字段 `explanation`
> 在 guide agent 就位后**已有值**（candidate_poi 命中→精确取料讲解；未命中→向量兜底检索相关 POI），并过 reviewer。
>
> **坑**（route agent 已踩过，同样适用）：技能不自动发现（必须 `pool/refresh`）；模型 provider 401
> （建 agent 时分到失效 key 会秒退空返回，换可用 provider）。
