# Story Discovery + Story Invitation — P0 Implementation Plan

> 状态：PLAN ONLY，等待确认后逐步实现  
> 日期：2026-07-24  
> 原则：不修改代码，不创建文件，不顺手重构

---

## A. RECOMMENDED ARCHITECTURE

```
┌─────────────────────────────────────────────────────┐
│  PreferencePage                                     │
│                                                     │
│  generate()                                         │
│    ↓                                                │
│  toPreference(formSnapshot())                       │
│    ↓                                                │
│  ┌──────────────────────────┐                       │
│  │ Story Discovery Layer    │  ← NEW                │
│  │                          │                       │
│  │ storyMatcher(preference) │                       │
│  │   ↓                      │                       │
│  │ StoryMatchResult         │                       │
│  │   matched?               │                       │
│  │   ├─ NO  ──→ continue    │                       │
│  │   └─ YES                 │                       │
│  │       ├─ declined? → cont│                       │
│  │       └─ fresh → CUTSCENE│                       │
│  └──────────┬───────────────┘                       │
│             ↓                                       │
│  ┌──────────────────────────┐                       │
│  │ Story Invitation Engine  │  ← NEW                │
│  │                          │                       │
│  │ Cutscene (telegram)      │                       │
│  │   3 scenes               │                       │
│  │   typewriter             │                       │
│  │   skip → decision        │                       │
│  │   ↓                      │                       │
│  │ InvitationDecision       │                       │
│  │   ├─ ACCEPT              │                       │
│  │   │   StoryContext.start │                       │
│  │   │   → StoryWalk        │                       │
│  │   └─ DECLINE             │                       │
│  │       executeRouteMatch()│                       │
│  │       → /walk            │                       │
│  └──────────────────────────┘                       │
│                                                     │
│  executeRouteMatch()  ← EXTRACTED (no-op refactor)  │
│    matchRoutes() + listPois()                       │
│    saveMatch()                                      │
│    navigate("/walk")                                │
└─────────────────────────────────────────────────────┘
```

### Design Principles

1. **Story Discovery is a pure function** — `preference → StoryMatchResult`，无副作用
2. **Invitation is a UI layer** — 不修改 PreferencePage 核心逻辑，只截流
3. **Catalog is data，not code** — 新增 Story 只需加 catalog entry + matcher rule
4. **Cutscene is authored content** — 不依赖 QwenPaw
5. **Persistence is lightweight** — localStorage，不碰 User DB

---

## B. STEP-BY-STEP IMPLEMENTATION PLAN

---

### Step 1 — Story Discovery Types, Catalog & Matcher

**目标**：创建一个纯函数层的 Story Discovery，接收 Preference 返回 StoryMatchResult。

**新增文件**：
- `frontend/src/story-discovery/types.ts`
- `frontend/src/story-discovery/storyCatalog.ts`
- `frontend/src/story-discovery/storyMatcher.ts`

**不从任何地方 import，不修改任何现有文件。**

#### `types.ts`

```typescript
// 邀请类型 → 决定 Cutscene 组件
export type InvitationType = 'telegram' | 'letter' | 'audio_recording';

// Story 在 catalog 中的状态
export type StoryStatus = 'playable' | 'planned';

// 匹配规则（catalog 作者定义）
export interface StoryMatchRule {
  duration: string[];          // e.g. ['full', 'multi']
  requiredInterests: string[];  // 至少命中一个
  requiredThemes: string[];     // 至少命中一个
  minScore: number;             // 综合分数阈值
}

// Catalog 条目
export interface StoryCatalogEntry {
  storyId: string;
  status: StoryStatus;
  title: string;
  subtitle: string;
  region: string;
  estimatedHours: number;
  invitationType: InvitationType;
  matchRule: StoryMatchRule;
}

// Matcher 输出
export interface StoryMatchResult {
  matched: boolean;
  storyId: string;
  score: number;
  reasons: string[];
  invitationType: InvitationType;
}
```

#### `storyCatalog.ts`

P0 catalog — 只有一条 playable Story：

```typescript
export const STORY_CATALOG: StoryCatalogEntry[] = [
  {
    storyId: 'lotus_city_double_map',
    status: 'playable',
    title: '莲城双图：消失的界线',
    subtitle: '一场跨越约五百年的澳门时间层探索',
    region: 'peninsula',
    estimatedHours: 7,
    invitationType: 'telegram',
    matchRule: {
      duration: ['full', 'multi'],          // 一日游 或 多日游
      requiredInterests: ['history', 'culture', 'arch'],  // interests 中至少一个
      requiredThemes: ['heritage', 'architecture'],        // themes 中至少一个
      minScore: 2,
    },
  },
  // 未来：
  // { storyId: 'taipa_letters', status: 'planned', ... }
  // { storyId: 'coloane_after_tide', status: 'planned', ... }
];
```

**关键设计**：
- `requiredInterests` 和 `requiredThemes` 是 **OR 逻辑**（至少命中一个）
- `duration` 是 **AND 逻辑**（必须是其中之一）
- 两者都满足才算 `matched`
- `status: 'planned'` 的条目被 matcher **自动排除**

#### `storyMatcher.ts`

Pure function：

```typescript
export function matchStory(pref: PreferenceFormState): StoryMatchResult {
  // 1. 过滤 status=playable 的 Story
  // 2. 逐个对 matchRule 打分
  // 3. 返回分数最高且 >= minScore 的 Story
  // 4. 如果没有匹配 → { matched: false, ... }
  // 5. 记录 reasons[] 方便调试
}
```

Scoring logic（P0 简单版）：
```
score = 0

if duration in matchRule.duration:
  score += 1

hitInterests = pref.interests ∩ matchRule.requiredInterests
score += hitInterests.length

hitThemes = pref.themes ∩ matchRule.requiredThemes
score += hitThemes.length

// Soft penalty for walk-averse users（不直接拒绝）
if 'less-walk' in pref.walkTags or 'accessible' in pref.walkTags:
  score -= 1

matched = score >= matchRule.minScore
```

**validation**：
- `cd frontend && npx tsc --noEmit` 通过
- 新增文件三，修改文件零

**risk**：无。纯函数层，无副作用，不被任何模块 import。

---

### Step 2 — Invitation State (Persistence Layer)

**目标**：创建一个轻量的 invitation state manager，记住用户对每个 Story 的选择。

**新增文件**：
- `frontend/src/story-discovery/invitationState.ts`

**设计**：

```typescript
// localStorage key pattern
const KEY_PREFIX = 'macau-storywalk-invitation-';

export type InvitationStatus = 'not_seen' | 'accepted' | 'declined';

interface InvitationRecord {
  storyId: string;
  status: InvitationStatus;
  timestamp: number;
}

// API:
export function getInvitationStatus(storyId: string): InvitationStatus
export function markInvitationAccepted(storyId: string): void
export function markInvitationDeclined(storyId: string): void
export function hasBeenInvited(storyId: string): boolean
```

存储：
- `localStorage("macau-storywalk-invitation-lotus_city_double_map")` → `{ status: "declined", timestamp: 1712345678 }`
- 不过期（用户明确拒绝后不应再次打扰）
- 每个 Story 独立 key，天然支持未来多 Story

**为什么 localStorage 而不是 sessionStorage**：
- sessionStorage 在关闭 tab 后清除 → 用户关闭再打开会再次被邀请
- 用户点了"拒绝"应该是明确的、持久的决定
- 未来可以提供"重新发现 Story"入口让用户手动清除

**为什么不在 WalkContext**：
- WalkContext 管理的是"旅游行程"状态（3 天 TTL）
- Invitation state 是"用户偏好决策"（持久、独立生命周期）
- 放在 WalkContext 会导致概念混淆

**validation**：
- `npx tsc --noEmit` 通过
- 手动在浏览器 console 验证 localStorage 读写
- 修改文件零

**risk**：无。独立的 utility，不被任何模块 import。

---

### Step 3 — Cutscene Engine

**目标**：创建一个通用的 Cutscene 引擎，支持 typewriter 文本、场景切换、skip、decision。

**新增文件**：
- `frontend/src/components/story-invitation/CutsceneStage.tsx`
- `frontend/src/components/story-invitation/TypewriterText.tsx`
- `frontend/src/components/story-invitation/SceneRenderer.tsx`
- `frontend/src/components/story-invitation/InvitationDecision.tsx`
- `frontend/src/components/story-invitation/StoryInvitationExperience.tsx`（顶层 orchestrator）
- `frontend/src/components/story-invitation/scenes/lotusTelegram.ts`（authored content）

#### 组件树

```
StoryInvitationExperience
├── CutsceneStage（全屏 dark overlay）
│   ├── SceneRenderer（根据 scene index 渲染当前 scene）
│   │   ├── TypewriterText（逐字显示）
│   │   └── SceneVisual（静态背景/动画，per-scene）
│   ├── SkipControl（"跳过剧情 →" 右上角）
│   └── SceneIndicator（底部 dots）
└── InvitationDecision（scene 结束后显示）
    ├── AcceptButton（"接受阿澜的邀请"）
    └── DeclineButton（"继续原来的旅程"）
```

#### TypewriterText 状态机

```
IDLE
  ↓ .start(text)
TYPING
  │ 每 ~40ms 显示一个字符
  │  → 字符计数增加
  ├── 用户点击：
  │   ├── 当前段落未完成 → 立即显示完整段落（跳到 COMPLETE）
  │   └── 当前段落已完成 → 触发 onParagraphComplete（进入下一段）
  ↓ 自然完成
COMPLETE
  │ 显示完整段落
  ↓ 用户点击
  → onParagraphComplete()
```

Props：
```typescript
interface TypewriterTextProps {
  paragraphs: string[];           // 多个段落
  speedMs: number;                // 每字符延迟（默认 40）
  onAllComplete: () => void;      // 全部段落完成
}
```

**Accessibility**：
- 使用 `aria-live="polite"` 区域
- `prefers-reduced-motion` → 跳过 typewriter 动画，直接显示全部文字
- keyboard: Enter/Space → 等同于点击

#### SceneRenderer

```
sceneIndex  →  0: Scene1 "系统异常"
               1: Scene2 "双图"
               2: Scene3 "电报"
             →  all done → 触发 onScenesComplete → 显示 InvitationDecision
```

#### Scene content — authored data

`scenes/lotusTelegram.ts`：

```typescript
export interface CutsceneScene {
  id: string;
  paragraphs: string[];        // TypewriterText 逐段显示
  background: 'dark' | 'maps' | 'telegram';
  audio?: { src: string; type: string };  // P0: undefined, 未来: 音效文件路径
}

export const LOTUS_TELEGRAM_SCENES: CutsceneScene[] = [
  {
    id: 'system_anomaly',
    background: 'dark',
    paragraphs: [
      '正在整理你的澳门旅程……',
      '正在生成路线……',
      '……',
      '检测到未归档数据。',
      '来源：未知。',
      '是否读取？',
    ],
  },
  {
    id: 'double_map',
    background: 'maps',
    paragraphs: [
      '一张图记住山、水、庙宇和人的名字。',
      '一张图记住道路、坐标和城市的边界。',
      '它们画的是同一座澳门。',
      '却从未真正重合。',
      '',
      '缺失的不是地点。',
      '是时间。',
    ],
  },
  {
    id: 'telegram',
    background: 'telegram',
    paragraphs: [
      '寻图人，见字如面。',
      '',
      '如果你正在读这封信，',
      '说明两张地图又一次找到了能够同时看见它们的人。',
      '',
      '不要急着判断哪一张是真的。',
      '两张都真。',
      '两张都不完整。',
      '',
      '如果你愿意，',
      '请替我再走一次这座城。',
      '',
      '——澜',
    ],
  },
];
```

**background 渲染（P0 简化）**：
- `'dark'` → 纯黑背景 + `bg-sage-deep/95`
- `'maps'` → 黑色背景 + CSS 半透明 overlay（不需要实际图片文件）
- `'telegram'` → 深色背景 + 居中文本 + border 模拟旧电报边框

#### SkipControl

```
"跳过剧情 →"
  ↓ 点击
直接跳到 InvitationDecision（不自动接受/拒绝）
```

**关键**：Skip = 跳过叙事，不等于接受。用户仍然需要主动选择接受或拒绝。

#### InvitationDecision

```
┌─────────────────────────────┐
│                             │
│    "接受阿澜的邀请"          │  ← primary CTA, sage-deep bg
│                             │
│    "继续原来的旅程"          │  ← secondary, subtle border
│                             │
└─────────────────────────────┘
```

Props：
```typescript
interface InvitationDecisionProps {
  storyTitle: string;
  characterName: string;    // "阿澜"
  acceptLabel: string;
  declineLabel: string;
  onAccept: () => void;
  onDecline: () => void;
  loading: boolean;
}
```

#### StoryInvitationExperience（顶层）

```
Props:
  storyMatch: StoryMatchResult
  onAccept: () => void
  onDecline: () => void
  onSkip: () => void       // → 直接跳到 decision

State:
  phase: 'loading' | 'cutscene' | 'decision'
  sceneIndex: number
```

Orchestrates: CutsceneStage → InvitationDecision

**validation**：
- `npx tsc --noEmit`
- 在 Storybook-style 独立页面手动验证 Cutscene 效果
- 可以通过临时路由 `/dev/cutscene` 测试

**risk**：低。组件是 self-contained 的 UI 层，不修改任何现有文件。

---

### Step 4 — PreferencePage Interception

**目标**：在 `generate()` 中插入 Story Discovery check，截流普通路线流程。

**修改文件**：`frontend/src/pages/PreferencePage.tsx`

**修改范围**：仅 `generate()` 函数内部

#### 修改前

```typescript
const generate = async () => {
  setError(null);
  setLoading(true);
  try {
    const preference = toPreference(formSnapshot());
    // ... customNote parseIntent ...

    const [matchRes, pois] = await Promise.all([     // ← route matching 在这
      matchRoutes(preference),
      listPois({ limit: 500 }),
    ]);
    // ... saveMatch ...
    navigate("/walk");
  } catch (err) { ... }
};
```

#### 修改后

```typescript
const generate = async () => {
  setError(null);
  setLoading(true);
  try {
    const snapshot = formSnapshot();
    const preference = toPreference(snapshot);
    // ... customNote parseIntent (unchanged) ...

    // ── Story Discovery ──
    const storyMatch = matchStory(snapshot);
    if (
      storyMatch.matched &&
      !hasBeenInvited(storyMatch.storyId)
    ) {
      setLoading(false);                    // 停止 loading spinner
      setStoryInvitation(storyMatch);       // 触发 cutscene modal
      return;                               // 截流！不执行 route matching
    }

    // ── Original flow (unchanged) ──
    await executeRouteMatch(preference);
  } catch (err) { ... }
};

// Extracted: allow decline path to call this directly
const executeRouteMatch = async (preference: Preference) => {
  setLoading(true);
  try {
    const [matchRes, pois] = await Promise.all([
      matchRoutes(preference),
      listPois({ limit: 500 }),
    ]);
    const top = matchRes.matches[0];
    if (!top) throw new Error(t(language, "noMatch"));
    const isMulti = preference.duration === "multi-day";
    saveMatch({
      preference: matchRes.preference,
      match: top,
      matches: isMulti ? matchRes.matches : [top],
      pois,
    });
    navigate("/walk");
  } catch (err) {
    const message = err instanceof Error ? err.message : "request failed";
    setError(
      message.includes("Failed to fetch") ? t(language, "backendDown") : message,
    );
  } finally {
    setLoading(false);
  }
};
```

#### 新 state

```typescript
const [storyInvitation, setStoryInvitation] = useState<StoryMatchResult | null>(null);
```

#### Cutscene modal render

```typescript
{storyInvitation && (
  <StoryInvitationExperience
    storyMatch={storyInvitation}
    onAccept={handleStoryAccept}
    onDecline={handleStoryDecline}
    onSkip={() => setShowDecision(true)}
  />
)}
```

**关键**：
- `setLoading(false)` 在截流时清除 loading spinner
- `executeRouteMatch()` 被提取成独立函数 → `decline` 时直接调用
- 原逻辑 **zero diff** — 只是被包了一层条件

**validation**：
- 未匹配 → 直接进入原流程（无 cutscene）
- 已拒绝 → 直接进入原流程（无 cutscene）
- 已接受 → 直接进入 Story（无 cutscene）
- 新鲜匹配 → cutscene 播放
- `npx tsc --noEmit` + `npx vite build`

**risk**：MEDIUM。修改了核心 flow 的 `generate()` 函数。需要确保 `executeRouteMatch()` 提取不影响原有错误处理。

---

### Step 5 — Accept → StoryWalk

**目标**：用户点击"接受阿澜的邀请"后，创建 StorySession 并进入 Story。

**修改文件**：`frontend/src/pages/PreferencePage.tsx`

#### handleStoryAccept

```typescript
const handleStoryAccept = async () => {
  if (!storyInvitation) return;
  setLoading(true);
  try {
    const token = localStorage.getItem("macau-storywalk-auth-token");
    if (!token) {
      // 未登录 → 引导登录后再创建 session
      navigate("/auth?redirect=story-invite");
      return;
    }

    markInvitationAccepted(storyInvitation.storyId);

    const sess = await startStorySession(storyInvitation.storyId, token);
    // 直接进入 prologue（跳过 StoryCoverPage）
    navigate(`/story-sessions/${sess.session_id}/nodes/${sess.current_chapter_id}`);
  } catch (err) {
    // Story start 失败 → 回退到普通路线
    setError("故事初始化失败，已切换到普通路线");
    markInvitationDeclined(storyInvitation.storyId);
    await executeRouteMatch(toPreference(formSnapshot()));
  } finally {
    setLoading(false);
    setStoryInvitation(null);
  }
};
```

**产品决策**：直接进入 Prologue，不经过 Cover Page。

理由：
1. 用户已在 Cutscene 中明确接受 → Cover Page 是冗余确认
2. Cutscene 本身已经起到了"介绍故事"的作用
3. 减少点击次数 = 更好的 mobile 体验

**error 处理**：
- Story API 失败 → fallback 到普通路线（不阻塞用户）
- 同时 mark `declined` 防止重复邀请

**validation**：
- 已登录 → 直接进入 story prologue
- 未登录 → 引导登录，登录后回到 story 流程
- API 失败 → fallback 到普通 route matching

---

### Step 6 — Decline → Normal Route

**目标**：用户点击"继续原来的旅程"后，恢复原 flow。

**修改文件**：`frontend/src/pages/PreferencePage.tsx`

#### handleStoryDecline

```typescript
const handleStoryDecline = () => {
  if (!storyInvitation) return;
  markInvitationDeclined(storyInvitation.storyId);
  setStoryInvitation(null);
  // 恢复原流程
  executeRouteMatch(toPreference(formSnapshot()));
};
```

**简洁直接**：
- 标记 declined
- 关闭 cutscene
- 调用提取好的 `executeRouteMatch()`

**validation**：
- Decline → route matching 正常执行
- 再次点击"生成我的路线" → 不弹 cutscene（因为已 declined）

---

### Step 7 — Mobile UX & Accessibility

**不新增文件，在所有 Cutscene 组件中实现。**

#### Mobile

| 关注点 | 方案 |
|--------|------|
| Touch target | Accept/Decline 按钮 ≥ 48px 高度 |
| 全屏 overlay | `fixed inset-0 z-50`，阻止页面滚动 |
| Safe area | `pb-safe` 处理 iPhone notch |
| 竖屏 | 优先竖屏布局，横屏居中 |

#### Accessibility

| 关注点 | 方案 |
|--------|------|
| `prefers-reduced-motion` | TypewriterText 检测 `matchMedia('(prefers-reduced-motion: reduce)')` → 直接显示全部文本 |
| Screen reader | `aria-live="polite"` 在 TypewriterText 容器；按钮有清晰 label |
| Keyboard | Enter/Space → 推进 typewriter；Tab → 聚焦按钮；Escape → 触发 skip |
| Audio mute | P0 不实现 audio（见 Step 8） |

#### Scroll lock

Cutscene 打开时 `document.body.style.overflow = 'hidden'`，关闭时恢复。

---

### Step 8 — Audio Design (P0 = No Audio)

**P0：不实现音效。**

理由：
1. 没有录音资产
2. 浏览器 autoplay 限制需要用户手势 → 复杂
3. 不是 blocking 功能

**但代码结构预留：**

```typescript
// CutsceneScene 接口中已有
audio?: { src: string; type: string };

// 未来实现时：
// 1. 检查 public/audio/ 下是否有对应的 mp3/ogg
// 2. 用 Howler.js 或原生 Audio API
// 3. 首次用户交互（click）后触发 audio context unlock
// 4. 检测 autoplay policy → 静音 fallback
// 5. <audio> 元素 with muted autoplay → unmute on first click

// 真人 CV 未来接法：
// invitationType='telegram' → audio src='audio/lotus_telegram_alan_cv.mp3'
// cutscene 每个 scene 可以有不同的 audio track
```

**P0 fallback：silent。无阻塞。**

---

### Step 9 — Button 文案建议

当前：`"生成我的路线 →"`

因为点击后可能触发 Story Cutscene，推荐改为更中性的：

**推荐**：`"开启我的澳门旅程 →"`

理由：
- 不承诺"路线"（可能是 Story）
- 保持"澳门旅程"的品牌感
- 与现有页面语气一致（"开始我的漫游"）
- 中英对照：`"Begin my Macau journey →"` / `"Começar a minha viagem por Macau →"`

**本轮不修改。** 等确认后由设计决定。

---

### Step 10 — Loading Screen

Cutscene 开始前显示短暂 loading：

```
┌────────────────────────────┐
│                            │
│                            │
│    "正在整理你的澳门旅程……" │
│                            │
│    [spinner]               │
│                            │
└────────────────────────────┘
```

- 显示 1.5s → 自动进入 Scene 1
- 如果用户在这个阶段关闭 tab → 无副作用（没有 API 调用）
- 属于 `StoryInvitationExperience` 的 `phase: 'loading'` 状态

---

## C. FILE CHANGE MATRIX

| 文件 | 操作 | 说明 |
|------|------|------|
| `frontend/src/story-discovery/types.ts` | **NEW** | StoryMatchRule, StoryCatalogEntry, StoryMatchResult 等 |
| `frontend/src/story-discovery/storyCatalog.ts` | **NEW** | P0 catalog（1 playable + 0 planned） |
| `frontend/src/story-discovery/storyMatcher.ts` | **NEW** | `matchStory(pref) → StoryMatchResult` |
| `frontend/src/story-discovery/invitationState.ts` | **NEW** | get/mark/hasBeenInvited localStorage wrapper |
| `frontend/src/components/story-invitation/StoryInvitationExperience.tsx` | **NEW** | Top-level orchestrator |
| `frontend/src/components/story-invitation/CutsceneStage.tsx` | **NEW** | Full-screen dark overlay container |
| `frontend/src/components/story-invitation/TypewriterText.tsx` | **NEW** | Animated typewriter with skip |
| `frontend/src/components/story-invitation/SceneRenderer.tsx` | **NEW** | Scene dispatcher by sceneIndex |
| `frontend/src/components/story-invitation/InvitationDecision.tsx` | **NEW** | Accept / Decline buttons |
| `frontend/src/components/story-invitation/scenes/lotusTelegram.ts` | **NEW** | Authored scene content |
| `frontend/src/pages/PreferencePage.tsx` | **MODIFY** | 插入 StoryDiscovery check + extract `executeRouteMatch()` + cutscene modal |
| `frontend/src/api/stories.ts` | **READ** | 复用 `startStorySession()`（不修改） |
| `frontend/src/state/StoryContext.tsx` | **READ** | 复用 session management（不修改） |
| `frontend/src/state/WalkContext.tsx` | **READ** | 复用 `saveMatch()`（不修改） |

**明确不需要修改的文件**：
- `App.tsx` — 不新增路由
- `StoryCoverPage.tsx` — accept 后跳过此页
- `StoryMapPage.tsx` — 不改
- `StoryScenePage.tsx` — 不改
- `StoryEndingPage.tsx` — 不改
- `AuthContext.tsx` — 不改
- `TripContext.tsx` — 不改
- `backend/` 任何文件 — 不改
- `data/stories/lotus_city_double_map.json` — 不改

---

## D. STATE FLOW DIAGRAM

```
PreferencePage.generate()
    │
    ├─ toPreference(formSnapshot())
    │
    ├─ matchStory(snapshot)
    │     │
    │     ├─ !matched ──────────────────────→ executeRouteMatch() → /walk
    │     │
    │     ├─ hasBeenInvited(storyId) ───────→ executeRouteMatch() → /walk
    │     │
    │     └─ matched && fresh
    │            │
    │            ▼
    │     ┌──────────────────────┐
    │     │ StoryInvitation      │
    │     │                      │
    │     │ Phase: loading       │  1.5s
    │     │  ↓                   │
    │     │ Phase: cutscene      │
    │     │  Scene 1 — 系统异常   │
    │     │  Scene 2 — 双图      │
    │     │  Scene 3 — 电报      │
    │     │  ↓ (or SKIP)         │
    │     │ Phase: decision      │
    │     │                      │
    │     │  ┌───────┐ ┌───────┐│
    │     │  │ACCEPT │ │DECLINE││
    │     │  └───┬───┘ └───┬───┘│
    │     └──────┼──────────┼────┘
    │            │          │
    │     ┌──────┘          └──────────┐
    │     ▼                            ▼
    │ markAccepted()            markDeclined()
    │ startStorySession()       executeRouteMatch()
    │     │                          │
    │     ├─ success                 ├─ matchRoutes()
    │     │  navigate(               │  listPois()
    │     │   /story-sessions/       │  saveMatch()
    │     │   {id}/nodes/            │  navigate("/walk")
    │     │   prologue_time_map      │
    │     │  )                       │
    │     │                          │
    │     └─ error                   │
    │        markDeclined()          │
    │        executeRouteMatch() ←───┘
    │        (fallback to normal)
```

---

## E. STORY MATCHING RULE TABLE

### P0: 莲城双图

| Condition | Operator | Values | Weight |
|-----------|----------|--------|--------|
| `duration` | MUST be one of | `'full'`, `'multi'` | +1 |
| `interests` | at least one of | `'history'`, `'culture'`, `'arch'` | +1 per hit |
| `themes` | at least one of | `'heritage'`, `'architecture'` | +1 per hit |
| `walkTags` | penalty if contains | `'less-walk'`, `'accessible'` | -1 total |
| **threshold** | score >= | 2 | — |

### Example scenarios

| Scenario | Duration | Interests | Themes | Walk | Score | Matched? |
|----------|----------|-----------|--------|------|-------|----------|
| 历史迷 | full | history, culture | heritage | — | 1+2+1 = 4 | ✅ |
| 建筑爱好者 | multi | arch | architecture | — | 1+1+1 = 3 | ✅ |
| 文化+摄影 | full | culture, photo | heritage | — | 1+1+1 = 3 | ✅ |
| 纯美食半日 | half | food | — | — | 0+0+0 = 0 | ❌ |
| 夜间漫步 | night | — | heritage | — | 0+0+1 = 1 | ❌ |
| 历史但少走路 | full | history | heritage | less-walk | 1+1+1-1 = 2 | ✅ (borderline) |
| 路氹一日 | full | — | cotai | — | 1+0+0 = 1 | ❌ |

### Planned Story exclusion

`storyCatalog.ts` 中 `status: 'planned'` → `matchStory()` 的 filter 自动排除。
Future matcher enhancement: 如果 `status: 'planned'` 但偏好高度匹配 → debug log 但不返回。

---

## F. CUTSCENE STATE DIAGRAM

```
                          ┌──────────┐
                          │  LOADING │  1.5s → auto advance
                          └────┬─────┘
                               │
                    ┌──────────▼──────────┐
                    │    CUTSCENE         │
                    │                     │
                    │  sceneIndex = 0 ────┤  Scene 1: 系统异常
                    │    │                │
                    │    │ typing/complete│
                    │    ▼                │
                    │  sceneIndex = 1 ────┤  Scene 2: 双图
                    │    │                │
                    │    │                │
                    │    ▼                │
                    │  sceneIndex = 2 ────┤  Scene 3: 电报
                    │    │                │
                    │    ▼                │
                    │  allScenesComplete  │
                    │    │                │
                    └────┼────────────────┘
                         │
              ┌──────────┼──────────┐
              │ SKIP      │          │ normal completion
              │ (anytime) │          │
              ▼           │          ▼
         ┌────────┐       │    ┌──────────┐
         │ SKIP   │◄──────┘    │ DECISION │
         │ confirm│            │          │
         │ ?      │            │ ACCEPT   │
         └───┬────┘            │ DECLINE  │
             │                 └────┬─────┘
        ┌────┴────┐                │
        │ YES     │ NO             │
        ▼         ▼                │
    go to     back to              │
    DECISION  CUTSCENE             │
    (direct)  (resume)             │
```

Typewriter per scene：

```
scene.paragraphs = [p0, p1, p2, ...]

p0:
  TYPING (40ms/char)
    ├── click → show full p0 immediately (COMPLETE)
    └── finished → COMPLETE

COMPLETE:
  click → next paragraph
  
after last paragraph:
  onAllComplete() → sceneIndex++

If sceneIndex === scenes.length:
  → show DECISION
```

Skip：
```
SKIP button (anytime during CUTSCENE)
  → show confirmation "确定要跳过剧情吗？"
  → YES → directly show DECISION (no auto-accept)
  → NO  → resume current scene
```

---

## G. ACCEPT / DECLINE SEQUENCE

### ACCEPT

```
User clicks "接受阿澜的邀请"
    ↓
check JWT token
    ├── 未登录 → navigate("/auth?redirect=story-invite")
    │   AuthPage 登录成功 → redirect 回 PreferencePage
    │   → 重新 trigger story flow（从 generate 开始）
    │   → 检测到 token 存在 → 直接 create session
    │
    └── 已登录
        ↓
markInvitationAccepted("lotus_city_double_map")
    ↓
POST /api/v1/stories/lotus_city_double_map/sessions
  Authorization: Bearer {token}
    ↓
    ├── 201 Created → { session_id, current_chapter_id: "prologue_time_map" }
    │   ↓
    │   navigate(`/story-sessions/${session_id}/nodes/prologue_time_map`)
    │   → StoryScenePage 渲染 prologue
    │   → 用户开始 StoryWalk
    │
    └── 4xx/5xx → catch
        ↓
        markInvitationDeclined(storyId)  // 防止重试循环
        executeRouteMatch(preference)     // fallback 普通路线
        → setError("故事初始化失败，已切换到普通路线")
```

### DECLINE

```
User clicks "继续原来的旅程"
    ↓
markInvitationDeclined("lotus_city_double_map")
    ↓
setStoryInvitation(null)          // 关闭 cutscene
    ↓
executeRouteMatch(preference)     // 原 flow 恢复
    ↓
matchRoutes() + listPois()
    ↓
saveMatch()
    ↓
navigate("/walk")
```

---

## H. TEST CHECKLIST

### Story Matcher Unit Tests

| Test | Input | Expected |
|------|-------|----------|
| 一日游 + 历史兴趣 | `{duration:'full', interests:['history'], themes:['heritage']}` | `matched: true, score >= 3` |
| 多日游 + 建筑主题 | `{duration:'multi', themes:['architecture']}` | `matched: true` |
| 半日游 + 历史兴趣 | `{duration:'half', interests:['history']}` | `matched: false` |
| 夜间 + 文化兴趣 | `{duration:'night', interests:['culture']}` | `matched: false` |
| 一日游 + 纯美食 | `{duration:'full', interests:['food']}` | `matched: false` |
| 一日游 + 少走路 + 文化 | `{duration:'full', interests:['culture'], walkTags:['less-walk']}` | `matched: true` (borderline, score=2) |
| 空偏好 | all defaults | `matched: false` |
| 多 Story 场景 | future: add taipa_letters to catalog | returns highest scored playable story |

### Invitation State Tests

| Test | Expected |
|------|----------|
| `markInvitationDeclined(id)` then `hasBeenInvited(id)` | `true` |
| `getInvitationStatus(id)` after decline | `'declined'` |
| `getInvitationStatus(unknown)` | `'not_seen'` |
| Refresh page after decline → `hasBeenInvited(id)` | `true` (localStorage survives) |
| Two different storyIds independent | `hasBeenInvited('A')` ≠ `hasBeenInvited('B')` |

### Flow Tests

| Test | Expected |
|------|----------|
| Eligible + fresh → generate() | Cutscene renders, route matching NOT called |
| Eligible + declined → generate() | Cutscene skipped, route matching called normally |
| Not eligible → generate() | Cutscene skipped, route matching called normally |
| Accept → StorySession created → navigate | Arrive at prologue scene |
| Accept + API fail → fallback | Normal route matching executes |
| Decline → route matching | WalkSession saved, navigate to /walk |
| Decline → refresh → generate() again | Cutscene NOT shown (declined persistence) |
| Skip cutscene → decision | Shows Accept/Decline (NOT auto-accept) |

### Build

| Check | Command |
|-------|---------|
| TypeScript | `npx tsc --noEmit` — zero errors |
| Vite build | `npx vite build` — zero warnings |
| Existing tests | Backend `test_stories.py` — still 5 passed |

---

## I. RISKS

| Risk | Severity | Mitigation |
|------|----------|------------|
| `executeRouteMatch()` extraction breaks error handling | MEDIUM | Keep diff minimal; the function body is a direct copy of the original code. Test decline → route match first. |
| Cutscene modal layering (z-index conflicts with bottom bar) | LOW | Use `z-50` for cutscene overlay; PreferencePage bottom bar is `z-30`. |
| Story start API fails for unauthenticated user | MEDIUM | Already handled: redirect to auth, then retry. Fallback to normal route on persistent failure. |
| localStorage quota (private browsing) | LOW | invitation state is tiny (~100 bytes per story). Catch `quota exceeded` and degrade gracefully (always show invitation). |
| Cutscene accessibility | LOW | `prefers-reduced-motion` check + `aria-live` + keyboard support from Step 7. |
| Mobile scroll during cutscene | LOW | `overflow: hidden` on body + `touch-action: none` on overlay. |

---

## J. RECOMMENDED STEP 1 CODING PROMPT

When you're ready to begin implementation, here's the first prompt:

---

> Implement Step 1 of the Story Discovery plan:  
> Create `frontend/src/story-discovery/types.ts`, `storyCatalog.ts`, and `storyMatcher.ts`.  
> 
> These files should be self-contained TypeScript modules with no imports from the rest of the codebase.  
> 
> The matcher should be a pure function `matchStory(pref: PreferenceFormState): StoryMatchResult`.  
> 
> Do NOT modify any existing files. Do NOT import these modules anywhere yet.  
> 
> After creation, run `npx tsc --noEmit` to verify TypeScript compilation.  
> 
> Also write a small set of manual test cases (inline comments in `storyMatcher.ts`) showing expected results for 6+ preference scenarios.

---

## APPENDIX: KEY CODE REFERENCES

| Thing | File | Line/Function |
|-------|------|---------------|
| Insertion point | `frontend/src/pages/PreferencePage.tsx` | `generate()` function, after `toPreference()` call |
| Preference form snapshot | `frontend/src/lib/preference.ts:149-156` | `formSnapshot()` |
| toPreference mapping | `frontend/src/lib/preference.ts:105-131` | `toPreference(form)` |
| WalkContext save | `frontend/src/state/WalkContext.tsx:171-192` | `saveMatch()` |
| StoryContext start | `frontend/src/state/StoryContext.tsx` | `startStory(storyId)` |
| Story API | `frontend/src/api/stories.ts:32-38` | `startStorySession(storyId, token)` |
| WalkSession localStorage key | `frontend/src/state/WalkContext.tsx:21` | `"macau-storywalk-session"` |
| Auth token key | `frontend/src/state/AuthContext.tsx:20` | `"macau-storywalk-auth-token"` |
