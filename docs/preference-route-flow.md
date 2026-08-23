# Preference → Route Matching → /walk 完整流程审计

> 基于实际代码，不是 README 推测。  
> 审计日期：2026-07-24  
> READ ONLY — 未修改任何代码

---

## 1. PreferencePage 当前收集的字段

### 完整字段清单

| # | 用户看到的问题 | UI 控件 | 可选值 | frontend field | backend field | required? |
|---|-------------|--------|--------|----------------|---------------|-----------|
| 1 | 游览时长 | 4-card grid | 半日游 / 一日游 / 夜间漫步 / 多日游 | `duration` (`"half"` / `"full"` / `"night"` / `"multi"`) | `duration` (`"half-day"` / `"full-day"` / `"evening"` / `"multi-day"`) | 否（默认 `"half"`） |
| 2 | 多日天数 | ± stepper (仅 `multi` 时可见) | 2–5 天 | `tripDays` | `trip_days` | 仅 multi-day 时需要 |
| 3 | 漫游主题 | Chip select (多选) | 历史城区 / 建筑漫游 / 摄影打卡 / 美食街巷 / 亲子轻松 / 休闲漫步 / 路氹度假村 | `themes[]` | `themes[]` | 否 |
| 4 | 兴趣标签 | Chip select (多选) | 历史 / 建筑 / 美食 / 摄影 / 文化 / 放松 | `interests[]` | `interests[]` | 否 |
| 5 | 出行类型 | 3-button grid | 独自 / 朋友 / 家庭 | `companion` (`"solo"` / `"friends"` / `"family"`) | `travel_type[]` + `party_size` | 否（默认 `"solo"`, `party_size=1`） |
| 6 | 行走偏好 | Chip select (多选) | 少走路 / 避免回头路 / 少日晒 / 少爬坡 / 室内优先 / 无障碍友好 | `walkTags[]` | `physical[]` | 否（默认 `["normal"]`） |
| 7 | 进境口岸 | Chip select (单选) | 关闸 / 青茂 / 横琴 / 港珠澳大桥 / 外港码头 / 内港 | `entryPort` | `entry_port` | 否 |
| 8 | 出境口岸 | Chip select (单选) | 同上 | `exitPort` | `exit_port` | 否 |
| 9 | 你还有什么其他需求吗 | 文本输入 | 自由文本 | `customNote` | 经 `parseIntent()` 转为 interests/physical/travel_type/duration | 否 |
| 10 | 界面语言 | （继承自 LanguagePage） | `zh-CN` / `zh-TW` / `en` / `pt` | `language` | `language` | 是（来自 landing） |

### 逐个核对你的问题

| 问题中的概念 | 状态 | 实际位置 |
|------------|------|---------|
| `full_day` | ✅ 存在 | `duration = "full"` → maps to `"full-day"` |
| `multi_day` | ✅ 存在 | `duration = "multi"` → maps to `"multi-day"` |
| `trip duration` | ✅ 存在 | `duration` 字段，4 个可选值 |
| `culture` | ✅ 存在 | `interests[]` 中有 `"culture"` |
| `history` | ✅ 存在 | `interests[]` 中有 `"history"` |
| `heritage` | ✅ 存在 | `themes[]` 中有 `"heritage"` (历史城区) |
| `architecture` | ✅ 存在 | `interests[]` 中有 `"arch"` → maps to `"architecture"`；同时 `themes[]` 中也有 `"architecture"` (建筑漫游) |
| `local_life` | ❌ 不存在 | 代码中未出现此标签 |
| `photography` | ✅ 存在 | `interests[]` 中有 `"photo"`；`themes[]` 中有 `"photo"` (摄影打卡) |
| `food` | ✅ 存在 | `interests[]` 中有 `"food"`；`themes[]` 中有 `"food"` (美食街巷) |
| `shopping` | ❌ 不存在 | 代码中未出现购物相关标签 |
| `physical level` | ⚠️ 部分存在 | `walkTags[]` 中的 `"less-walk"` / `"no-backtrack"` 等是 walking tolerance，但不是 `low/med/high` 三级枚举。`physical_level` 是 route template 的 OUTPUT，不是用户 INPUT |
| `walking tolerance` | ✅ 存在 | `walkTags[]`: `less-walk`, `no-backtrack`, `shade`, `flat`, `indoor`, `accessible` |
| `pace` | ❌ 不存在 | 没有 pace/speed 字段 |
| `companion type` | ✅ 存在 | `companion`: `solo` / `friends` / `family` |

---

## 2. PreferenceGuideChat 如何工作

### Agent ID

`"pref-guide"` — 定义在 `backend/app/agents/preference_guide_agent.py:29`

### Session 维护

- 前端发送 `action: "start"` → 后端返回 `session_id`
- 后续每次 `action: "message"` 携带同一个 `session_id`
- Session 由 QwenPaw Console 维护（多轮对话上下文在 QwenPaw 侧）

### 用户输入什么

```typescript
POST /api/v1/intent/guide
Body: {
  action: "start" | "message",
  session_id: string,
  message: string,           // 用户当前输入
  language: "zh-CN",
  user_turn: number,         // 递增轮次
  transcript: string         // 累计用户所有原话，\n 拼接
}
```

### QwenPaw 返回什么

```typescript
Response: {
  session_id: string,
  reply: string,             // 自然语言回复（可能尾部带 JSON）
  ready: boolean,            // agent 认为收集够了
  preference: Preference | null,  // 提取的结构化偏好
  source: "agent" | "script"
}
```

QwenPaw 回复中的 JSON 由后端提取（regex `\{[\s\S]*\}\s*$`），经过白名单校验后转为 `Preference` 对象。

### 谁把自然语言转成 Preference

**三层转换**，同时工作：

| 层 | 位置 | 方式 |
|---|------|------|
| 1. QwenPaw Agent | `backend/app/agents/preference_guide_agent.py` | LLM 输出 structured JSON |
| 2. 后端软解析 | `backend/app/features/intent/api.py:_soft_preference_from_transcript()` | 规则关键词扫描 transcript |
| 3. 前端本地推断 | `frontend/src/lib/preference.ts:inferPreferenceFromText()` | 客户端 regex，每次消息都运行 |

三层结果通过 `_merge_preferences()` 合并（并集），前端 `applyPreferenceToForm()` 将结果回填到结构化表单。

### QwenPaw 失败时怎么办

```
_guide_with_qwenpaw() 尝试调用
    ↓ 失败
返回 ("", None, "script")
    ↓
_guide_scripted_fallback()
    │ 按 user_turn 逐步问：时长 → 口岸 → 同伴 → 兴趣 → 步行
    │ 每轮也用规则关键词提取 preference
    ↓
如果 user_turn >= 2 且网络失败 → 前端仍允许展开 adjusters
```

### Chat 和结构化表单的关系

```
┌─────────────────────────────────┐
│  PreferenceGuideChat (上方)      │
│  - 首次自动 startChat()         │
│  - 用户每发一条 → send()        │
│  - 每次 send → inferPreference  │
│    → applyPreferenceFromChat()  │
│    → 更新下方 chips（实时联动）  │
│  - ready || userTurn >= 3       │
│    → 自动展开下方 adjusters     │
├─────────────────────────────────┤
│  Manual Adjusters (下方)         │
│  - 初始隐藏（chatFirstHint）    │
│  - 展开后：                      │
│    Duration → Themes → Interests│
│    → Companion → Walk → Ports   │
│  - 用户可直接改 chips            │
│  - Chat 继续运行，改 chip 时不   │
│    影响 chat 状态                │
│  - 底部固定 bar："生成我的路线 →"│
└─────────────────────────────────┘
```

**关键设计**：Chat 是引导层，Adjusters 是精确编辑层。两者通过 `formRef` 同步。Chat 的每次结果都增量合并进 form，不会覆盖用户手动选择。

---

## 3. 什么时候算"完成偏好收集"

**没有显式的"完成"按钮**。用户通过点击底部固定 bar 的按钮来触发：

```
PreferencePage.tsx:601
<button onClick={generate}>
  生成我的路线 →
</button>
```

### 函数链

```
用户点击 "生成我的路线 →"
    ↓
generate()                              // PreferencePage.tsx:219
    ↓
formSnapshot() → PreferenceFormState    // PreferencePage.tsx:149-156
    ↓
toPreference(formSnapshot()) → Preference // lib/preference.ts:105-131
    ↓
[条件] parseIntent(customNote)         // 用 QwenPaw/规则 解析自由文本
    ↓
Promise.all([
  matchRoutes(preference),              // POST /api/v1/routes/match
  listPois({ limit: 500 })              // GET /api/v1/pois?limit=500
])
    ↓
saveMatch({ preference, match, matches, pois })  // WalkContext
    ↓
navigate("/walk")
```

**没有 validation**。`generate()` 不检查必填字段。所有偏好都有默认值，用户可以什么都不选直接点按钮。

---

## 4. Route Matching 何时发生

从用户点击按钮开始，逐函数追踪：

```
1. 用户点击 "生成我的路线 →"
   PreferencePage.tsx:601

2. generate()
   PreferencePage.tsx:219-285

3. formSnapshot() → PreferenceFormState
   PreferencePage.tsx:149-156

4. toPreference(formSnapshot()) → Preference
   frontend/src/lib/preference.ts:105-131
   
   映射规则：
   - duration: "half"→"half-day", "full"→"full-day", "night"→"evening", "multi"→"multi-day"
   - interests: "history"→"history", "arch"→"architecture", "food"→"food", "photo"→"photo", "culture"→"culture", "relax"→"relax"
   - companion → party_size: solo=1, friends=2, family=3
   - walkTags → physical[]: less-walk/less-walk, no-backtrack→no-backtrack, shade/flat/indoor/accessible→less-walk
   - empty physical → ["normal"]

5. [条件] parseIntent(customNote)
   frontend/src/api/client.ts:106-113
   POST /api/v1/intent/parse { text: customNote }
   
   backend/app/features/intent/api.py:438-458
   → intent_agent.parse_intent(text)  OR  parse_intent_rules(text)
   → source: "agent" | "rules"
   
   返回的 preference 增量合并到主 preference（并集）

6. await Promise.all([
     matchRoutes(preference),   // POST /api/v1/routes/match
     listPois({ limit: 500 }),  // GET /api/v1/pois?limit=500
   ])
   
   backend/app/features/routes/api.py:53-64
   → route_service.match(pref)
   → match_routes(pref, top_k)
   backend/app/features/routes/matcher.py:400-417
   
   主路径（always）：should_use_theme_days() → True
   → _match_theme_days(pref, research_tips)
   backend/app/features/routes/theme_days.py
   → allocate_theme_days(pref)  // 按主题分配天
   → build_theme_day_shell(spec, pref)  // 每天一个 shell
   → build_candidate_pool_for_shell(shell)  // POI 候选池
   → construct_route(shell, pref, candidate_pois)  // 排线
   → _dedupe_multi_day_pois(matches)  // 多日去重
   
   兜底（异常时）：_match_preset_templates(pref, top_k)
   → 遍历预设模板，score_template_preference() 打分排序

7. Response → matchRoutes() 返回
   { preference: Preference, matches: MatchResult[] }

8. saveMatch({ preference, match, matches, pois })
   frontend/src/state/WalkContext.tsx:171-192
   → WalkSession { language, preference, match, matches, poisById }
   → writeExpiringLocal("macau-storywalk-session", session)  // localStorage, 3天TTL

9. navigate("/walk")
   → RouteResultPage
```

### 关键事实

- Route matching 是 **纯确定性**，不涉及任何 LLM
- 主路径是 POI-pool theme day generation（不是预设模板打分）
- 预设模板仅在异常时作为兜底
- QwenPaw 只在 `parseIntent(customNote)` 步骤参与（可选）
- 此时 Trip 还未创建

---

## 5. Route Matching Request 的 Payload

```json
POST /api/v1/routes/match
Content-Type: application/json

{
  "duration": "full-day",
  "party_size": 1,
  "travel_type": ["solo"],
  "interests": ["history", "architecture", "culture"],
  "themes": ["heritage", "architecture"],
  "physical": ["normal"],
  "language": "zh-CN",
  "entry_port": null,
  "exit_port": null,
  "travel_date": "2026-07-24",
  "trip_days": null
}
```

字段来源：`toPreference(formSnapshot())` 在 `frontend/src/lib/preference.ts:105-131`

---

## 6. Route Matching Response

```json
{
  "preference": { /* 同上，后端可能微调 */ },
  "matches": [
    {
      "route": {
        "id": "theme_day_heritage",
        "name": "历史城区 · 第1天",
        "theme": "文化",
        "duration_label": "一日",
        "duration_hours": 7.5,
        "walk_distance_km": 3.4,
        "physical_level": "medium",
        "suitable_for": ["history", "architecture", "culture", "solo", "friends"],
        "nodes": [
          {
            "poi_id": "poi_ama",
            "order": 1,
            "suggested_stay_min": 35,
            "note": "...",
            "replaceable_with": []
          }
        ]
      },
      "score": 100,
      "reasons": ["第 1 天按主题...从景点池生成", "未使用预设模板打分选线"],
      "selected_template": "theme_day_heritage",
      "candidate_pois": [...],
      "applied_constraints": [...],
      "explanation": { "summary": "...", "details": [...] }
    }
  ]
}
```

### POI 如何获取

- `listPois({ limit: 500 })` 在 route matching 的同时并行调用
- 返回全部 POI（目前 ~339 条），用于构建 `poisById` map

### Route 保存在哪里

```typescript
WalkContext.saveMatch() → WalkSession {
  language, preference, match, matches[], poisById
}
→ writeExpiringLocal("macau-storywalk-session", session)
→ localStorage, 3 天 TTL (expiring envelope)
```

### Refresh 后是否恢复

**是。** `WalkProvider` 初始化时调用 `readSession()` → `readExpiringLocal("macau-storywalk-session")`。如果未过期，完整恢复 `WalkSession`（含 route + POIs）。

---

## 7. Trip 何时创建

```
Preference completed → route matched
                        ↓
                    此时 Trip 未创建 ❌
                        ↓
                  navigate("/walk")
                        ↓
                  RouteResultPage 渲染
                        ↓
              用户点击 "仅开始行程" 或 "模拟到站"
                        ↓
              TripContext.startTrip(userId, routeId, stopPoiIds)
              或 TripContext.simulateArrive(userId, routeId, poiId, stopPoiIds)
                        ↓
              POST /api/v1/trips { user_id, route_id, stop_poi_ids }
                        ↓
              Trip 创建，状态 ACTIVE
```

### 关键代码路径

```
RouteResultPage → TripControls 组件
    ↓
startTrip() / simulateArrive()
    frontend/src/state/TripContext.tsx:121-252
    ↓
createTrip({ user_id, route_id, stop_poi_ids })
    frontend/src/api/trips.ts:43-48
    POST /api/v1/trips
    backend/app/features/trips/api.py:47-53
```

**结论：Trip 在 /walk 页面按需创建，不在 route matching 阶段创建。**

---

## 8. 未登录用户能否完整执行 /preferences → route matching → /walk

**可以。**

原因：

1. **`/preferences` 页面没有登录检查**。`PreferencePage.tsx` 不 import `useAuth`。
2. **`matchRoutes()` 不需要 JWT**。`POST /api/v1/routes/match` 是公开端点，不需要认证。
3. **`listPois()` 不需要 JWT**。`GET /api/v1/pois` 是公开端点。
4. **`/walk` 页面没有登录检查**。`RouteResultPage` 使用 `guestUser` 机制的 `resolveTripUserId()`。
5. **Trip 创建使用 `user_id` 参数**，不是 JWT derived。`POST /api/v1/trips` 接受 `user_id` in body。

整个偏好→匹配→路线查看流程完全不需要登录。仅 StoryWalk（需要 JWT）和个人资料保存（需要 JWT）才要求登录。

---

## 9. Eligibility Rule 可行性分析

### 目标规则

```
(duration == full_day OR multi_day)
AND
interests intersects [culture, history, heritage, architecture, local_life]
```

### 逐项分析

| 条件 | 状态 | 详情 |
|------|------|------|
| `duration == full_day` | ✅ 已有 | `formSnapshot().duration === "full"` → 后端 `"full-day"` |
| `duration == multi_day` | ✅ 已有 | `formSnapshot().duration === "multi"` → 后端 `"multi-day"` |
| `interests has culture` | ✅ 已有 | `formSnapshot().interests.includes("culture")` |
| `interests has history` | ✅ 已有 | `formSnapshot().interests.includes("history")` |
| `interests has architecture` | ✅ 已有 | `formSnapshot().interests.includes("arch")` |
| `interests has heritage` | ⚠️ 已有但枚举不同 | `heritage` 不在 `interests[]` 中，在 `themes[]` 中。themes 有 `"heritage"`（历史城区） |
| `interests has local_life` | ❌ 完全缺失 | 代码中未出现 `"local_life"` 标签 |
| `physical_level != low` | ⚠️ 可映射但需谨慎 | `physical_level` 是 route 的 OUTPUT。用户侧只能用 `walkTags` 推断：不选 `"less-walk"` 暗示体力尚可。但这是**推断**不是**显式声明** |

### 实际可行的 eligibility check

```typescript
function isStoryEligible(form: PreferenceFormState): boolean {
  // Core: duration
  const isFullOrMulti = form.duration === "full" || form.duration === "multi";
  if (!isFullOrMulti) return false;

  // Core: cultural interests (interests + themes)
  const culturalInterests = new Set(form.interests);
  const culturalThemes = new Set(form.themes);
  const hasCultureSignal =
    culturalInterests.has("history") ||
    culturalInterests.has("culture") ||
    culturalInterests.has("arch") ||
    culturalThemes.has("heritage") ||
    culturalThemes.has("architecture");
  if (!hasCultureSignal) return false;

  // Soft: not explicitly avoiding walking
  const walkTags = new Set(form.walkTags);
  const avoidsWalking = walkTags.has("less-walk") || walkTags.has("accessible");
  // if (avoidsWalking) return false;  // optional

  return true;
}
```

**结论：核心规则（duration + cultural interests）完全可以实现。`local_life` 缺失但可用 heritage 替代。Soft condition 可推断但非显式。**

---

## 10. 最精确插入点

### 推荐位置

**文件**：`frontend/src/pages/PreferencePage.tsx`  
**函数**：`generate()`  
**具体位置**：第 223 行 `const preference = toPreference(formSnapshot());` **之后**，  
第 261 行 `const [matchRes, pois] = await Promise.all([...])` **之前**

```typescript
const generate = async () => {
    setError(null);
    setLoading(true);
    try {
      const preference = toPreference(formSnapshot());       // ← preference finalized
      // ... customNote parseIntent ...
      
      // ★★★ 插入点在这里 ★★★
      // if (isStoryEligible(formSnapshot()) && isAuthenticated) {
      //   show StoryInviteModal
      //   if accepted → navigate("/stories/lotus_city_double_map"); return;
      //   if declined → 继续下面的流程
      // }
      
      const [matchRes, pois] = await Promise.all([            // ← route matching 尚未发生
        matchRoutes(preference),
        listPois({ limit: 500 }),
      ]);
      // ...
    }
};
```

### 此时能拿到什么

| 信息 | 可用？ |
|------|--------|
| PreferenceFormState（所有原始 UI 字段） | ✅ `formSnapshot()` |
| Preference（转换后的 API 格式） | ✅ `preference` 已计算 |
| QwenPaw structured result | ⚠️ `parseIntent()` 结果已合并到 `preference` |
| 是否已保存 preference | ❌ 尚未调用 `saveMatch()` |
| 是否已创建 Trip | ❌ 尚未 |
| Route matching 是否已发生 | ❌ 尚未（在下面的 Promise.all 中） |
| 用户是否登录 | ✅ 可通过 `useAuth()` 获取 |

### 优势

- 零浪费：route matching API 调用不会发生（如果用户接受 StoryWalk）
- 所有 preference 数据已 finalized
- 单点插入，改动最小
- 如果用户拒绝 → 正常流程无任何副作用

---

## 11. Workflow 决定 WHETHER / QwenPaw 决定 HOW

### 架构可行性：可以 ✅

现有 PreferenceGuideChat 的架构已经支持这种分离模式。

### 具体方案

```
Preference finalized → isStoryEligible(form) → true
    ↓
显示邀请弹窗（含 narrative scene）
    ↓
[可选] 如果 QwenPaw pref-guide agent 的 session 仍然活跃：
    ↓
POST /api/v1/intent/guide
{
  action: "message",
  session_id: "<existing pref-guide session>",
  message: "",  // 空消息，让 agent 主动发起
  language: "...",
  transcript: "<累计对话历史>",
  // 可增加 context hint：
  // "用户符合 StoryWalk 条件。请用角色阿澜的语气，邀请用户探索《莲城双图》..."
}
    ↓
QwenPaw 返回 narrative invitation（角色化文案）
    ↓
前端渲染 invite text + 两个按钮：
  "接受邀请" → navigate("/stories/lotus_city_double_map")
  "继续普通路线" → 关闭弹窗，继续 generate()
```

### 为什么可行

1. **Pref-guide agent 的 session 仍然存活** — 在 `PreferencePage` 中，`PreferenceGuideChat` 的 session 在组件生命周期内保持
2. **QwenPaw 支持追加消息** — `POST /api/v1/intent/guide { action: "message" }` 可以在同一个 session 中继续对话
3. **Separation of concerns 清晰** — eligibility 检查是纯前端/后端确定性逻辑；invitation 表达是 QwenPaw 的 creative layer
4. **失败安全** — 如果 QwenPaw 不可用，可以用硬编码的多语言邀请文案 fallback（类似 `_OPENERS` 字典）

### 需要确认的问题

- Pref-guide agent 的 system prompt 是否需要更新以支持 "story invitation" 模式
- Invitation 是否需要单独的 agent（`story-invite`）还是复用 `pref-guide`
- 如果 QwenPaw 返回的 invitation 文案不理想，是否有 editorial review

---

## 12. 未来最小改动涉及的文件

| 文件 | 改动 |
|------|------|
| `frontend/src/pages/PreferencePage.tsx` | `generate()` 中插入 eligibility check + modal trigger |
| `frontend/src/lib/preference.ts` | 新增 `isStoryEligible(form: PreferenceFormState): boolean` |
| `frontend/src/components/preference/StoryInviteModal.tsx` | **NEW** — 邀请弹窗组件（narrative scene + accept/decline） |
| `frontend/src/state/WalkContext.tsx` | 可选：添加 `storyInvitationDeclined` 状态避免重复弹窗 |
| `frontend/src/components/preference/PreferenceGuideChat.tsx` | 可选：暴露 `sessionId` 供 invitation 复用 |
| `backend/app/features/intent/api.py` | 可选：`/guide` 端点支持 invitation context hint |
| `backend/app/agents/preference_guide_agent.py` | 可选：agent prompt 增加 story invitation 能力 |
| `frontend/src/pages/StoryCoverPage.tsx` | 可选：接受来自 onboarding 的 `prePopulatedPreference` |

**不改动的文件**：
- `App.tsx`（不需要新路由）
- `RouteResultPage.tsx`（不受影响）
- `TripContext.tsx`（不受影响）
- Story backend（`stories/api.py`, `engine.py` 等 — 已完整）
- 后端 route matcher（不受影响）
