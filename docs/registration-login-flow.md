# 注册 & 登录流程文档

> 基于实际代码审计，非 README 推测。  
> 审计日期：2026-07-24  
> 分支：Grace

---

## 1. 总览

```
Landing (/)
    ↓
[选择语言]
    ↓
点击 "登录 / 注册" → /auth
    ↓
┌─────────────────────────────┐
│  AuthPage                   │
│  ┌──────────┬──────────┐    │
│  │  登录     │  注册    │    │
│  └──────────┴──────────┘    │
│                             │
│  登录：只需输入 user_id      │
│  注册：user_id + 昵称 + 语言 │
│                             │
│  无密码，无邮箱，无手机号     │
└─────────────────────────────┘
    ↓ 成功
redirect → /preferences
```

---

## 2. 注册字段

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `user_id` | string | ✅ 是 | 唯一标识，用作登录凭据 |
| `name` | string | ❌ 否 | 昵称，可为空 |
| `language` | enum | ❌ 否 | `zh-CN` / `zh-TW` / `en` / `pt`，默认 `zh-CN` |

### 前端表单

**文件**: `frontend/src/pages/AuthPage.tsx:96-133`

```tsx
// 注册模式额外显示：
<input name="user_id" required />       // 用户 ID
<input name="name" />                   // 昵称（可选）
<select name="language">                // 语言
  zh-CN / zh-TW / English / Português
</select>
```

### 后端 API

**文件**: `backend/app/features/users/api.py`

```
POST /api/v1/users/register
Body: { user_id: string, name?: string, language?: string }
Response: { token: string, user: { user_id, name, language, preference } }
```

### 注册不采集：

- ❌ 密码
- ❌ 邮箱
- ❌ 手机号
- ❌ 旅游偏好
- ❌ 任何非必要个人信息

---

## 3. 登录字段

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `user_id` | string | ✅ 是 | 唯一标识 |

### 前端表单

**文件**: `frontend/src/pages/AuthPage.tsx:96-106`

```tsx
// 登录模式：
<input name="user_id" required />  // 仅此一个字段
```

### 后端 API

**文件**: `backend/app/features/users/api.py`

```
POST /api/v1/users/login
Body: { user_id: string }
Response: { token: string }
```

登录成功后，前端立即调用 `GET /api/v1/users/me` 获取完整用户资料。

---

## 4. JWT 生命周期

| 项目 | 实现 |
|------|------|
| **生成** | 后端登录/注册时签发 |
| **存储** | `localStorage("macau-storywalk-auth-token")` |
| **读取** | `AuthContext` 初始化时从 localStorage 恢复 |
| **过期** | 无过期机制（无 refresh token） |
| **撤销** | 仅前端清除（logout 删除 localStorage） |
| **传输** | 通过 `Authorization: Bearer {token}` header |

### 关键代码

**文件**: `frontend/src/state/AuthContext.tsx`

```typescript
const TOKEN_KEY = "macau-storywalk-auth-token";

function readToken(): string | null {
  return localStorage.getItem(TOKEN_KEY);
}

function writeToken(token: string | null) {
  if (token) localStorage.setItem(TOKEN_KEY, token);
  else localStorage.removeItem(TOKEN_KEY);
}
```

### 受 JWT 保护的操作

| 操作 | API | 说明 |
|------|-----|------|
| 保存偏好 | `PUT /api/v1/users/{id}/preferences` | 需要 Bearer token |
| 获取用户资料 | `GET /api/v1/users/me` | 需要 Bearer token |
| 创建 Trip | `POST /api/v1/trips` | 公开（传 user_id），但建议登录 |
| StoryWalk | `POST /api/v1/stories/{id}/sessions` | 需要 Bearer token |

---

## 5. localStorage 键值总览

| Key | 用途 | 存储方式 |
|-----|------|----------|
| `macau-storywalk-auth-token` | JWT token | localStorage |
| `macau-storywalk-lang` | 界面语言 | Cookie (3天) |
| `macau-storywalk-preference` | 偏好（小数据） | Cookie JSON (3天) |
| `macau-storywalk-session` | 行程会话（含 POI） | localStorage + expiring envelope (3天) |
| `macau-storywalk-story-session-id` | StoryWalk 会话 ID | localStorage |

---

## 6. AuthContext 完整状态

**文件**: `frontend/src/state/AuthContext.tsx`

```typescript
interface AuthContextValue {
  token: string | null;          // JWT
  userId: string | null;         // user.user_id
  user: UserProfile | null;      // { user_id, name, language, preference }
  isAuthenticated: boolean;      // token && user 同时存在
  isRestoring: boolean;          // 正在从 localStorage 恢复
  error: string | null;          // 最近错误
  register(input) → Promise;     // 注册
  login(input) → Promise;        // 登录
  logout() → void;               // 退出
  savePreference(pref) → Promise;// 保存偏好到服务端
  clearError() → void;           // 清除错误
}
```

### 恢复流程

```
AuthProvider 挂载
    ↓
readToken() → token 存在？
    ↓ YES
setIsRestoring(true)
    ↓
GET /api/v1/users/me (with Bearer token)
    ↓
    ├── 200 → setUser(restoredUser)
    ├── 401 → logout()（token 无效，清除）
    └── 网络错误 → setError(message)
    ↓
setIsRestoring(false)
    ↓
isAuthenticated = token && user 均不为 null
```

---

## 7. 重定向行为

| 场景 | 来源 | 目标 |
|------|------|------|
| 登录成功 | `/auth` | `/preferences` |
| 注册成功 | `/auth` | `/preferences` |
| 已登录用户访问 `/auth` | `/auth` | `/preferences`（自动跳转） |
| 退出登录 | 任意 | 留在当前页（清除状态） |
| 未登录访问 StoryWalk | `/stories/*` | 显示登录提示（不自动跳转） |

### 核心代码

**文件**: `frontend/src/pages/AuthPage.tsx:19-23`

```typescript
useEffect(() => {
  if (!isRestoring && isAuthenticated) {
    navigate("/preferences", { replace: true });
  }
}, [isAuthenticated, isRestoring, navigate]);
```

---

## 8. 偏好保存

**文件**: `frontend/src/api/auth.ts:71-84`

```
PUT /api/v1/users/{userId}/preferences
Authorization: Bearer {token}
Body: Preference JSON
Response: { preference: Preference }
```

偏好保存在 User 模型上，登录后可跨设备恢复。但不是注册/登录流程的一部分——偏好收集是独立页面。

---

## 9. 与 StoryWalk 的关系

StoryWalk 入口虽然出现在 Landing 页（`LanguagePage.tsx`），但它依赖 JWT：

```
/stories/lotus_city_double_map
    ↓
StoryCoverPage
    ↓
检查 isAuthenticated
    ├── 未登录 → 显示 "请先登录" 提示 + 登录按钮
    └── 已登录 → 显示 "开始探索" / "继续探索"
```

StoryWalk 的 session 创建需要 Bearer token：

```
POST /api/v1/stories/{storyId}/sessions
Authorization: Bearer {token}
→ 201 Created { session_id, ... }
```

---

## 10. 错误处理

| 错误 | 前端表现 | 来源 |
|------|----------|------|
| 401 登录失败 | 红色提示文字 | AuthApiError |
| 网络不通 | "请求失败，请稍后重试" | errorMessage() |
| Token 过期/无效 | 自动 logout，清除状态 | AuthContext restore |
| 注册 ID 已存在 | 后端返回错误详情，红色显示 | AuthApiError |

### 关键代码

**文件**: `frontend/src/api/auth.ts:13-21`

```typescript
export class AuthApiError extends Error {
  constructor(message: string, readonly status: number) {
    super(message);
    this.name = "AuthApiError";
  }
}
```

---

## 11. 架构小结

```
┌──────────────────────────────────────────────┐
│                  前端                         │
│                                              │
│  AuthPage  ←→  AuthContext  ←→  localStorage │
│     │              │                         │
│     │         token 存在则自动恢复             │
│     │              │                         │
│     ▼              ▼                         │
│  POST /register  GET /me                     │
│  POST /login     PUT /preferences            │
└──────────────────┬───────────────────────────┘
                   │
                   ▼
┌──────────────────────────────────────────────┐
│                  后端                         │
│                                              │
│  /api/v1/users/register  → 签发 JWT          │
│  /api/v1/users/login     → 签发 JWT          │
│  /api/v1/users/me        → 验证 JWT，返回资料 │
│  /api/v1/users/{id}/preferences → 存储偏好    │
│                                              │
│  JWT 无过期，无 refresh                       │
│  用户模型：user_id + name + language + pref   │
└──────────────────────────────────────────────┘
```

**设计特点：**

- **极简注册**：只需 user_id，无密码/邮箱/手机
- **无密码登录**：仅凭 user_id 即可
- **偏好独立**：偏好收集与注册/登录分离
- **公开可用**：核心旅游流程（偏好→路线→讲解）无需登录即可使用
- **登录增强**：登录后可跨设备保存偏好、使用 StoryWalk
