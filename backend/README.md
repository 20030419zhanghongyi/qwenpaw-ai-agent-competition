# Backend — Macau StoryWalk API

FastAPI 后端，负责 API 编排、路线匹配、QwenPaw Agent 封装与数据访问。

## 技术栈

- **FastAPI** + **Pydantic v2** + **Pydantic Settings**
- 数据访问：Phase 1 直接读 `data/*.json`；Phase 3 接 pgvector / Postgres
- Agent：Phase 3 接入 QwenPaw / DashScope

## 环境准备

```bash
# 1) 在仓库根目录复制环境变量模板并填入 key
cd ..                 # 回到仓库根
cp .env.example .env
#   编辑 .env，至少填 DASHSCOPE_API_KEY（Phase 3 起）。Phase 1/2 不填也能跑。

# 2) 安装依赖（推荐用 uv，也可用 pip）
cd backend
pip install -e ".[dev]"          # 或：uv pip install -e ".[dev]"
```

## 启动

```bash
uvicorn app.main:app --reload --port 8000
# 接口文档：http://localhost:8000/docs
# 健康检查：http://localhost:8000/api/v1/health
```

## 测试

```bash
pytest -q
```

## Local PostgreSQL + PostGIS

The repository root `compose.yml` provides a local Demo database using
`postgis/postgis:16-3.4`. Its credentials are development-only defaults.

```powershell
# From the repository root
docker compose up -d db
docker compose ps

# Apply and inspect schema migrations
Push-Location backend
..\.venv\Scripts\python.exe -m alembic upgrade head
..\.venv\Scripts\python.exe -m alembic current
Pop-Location

# Stop the container while retaining the named data volume
docker compose stop db
```

The application reads `DATABASE_URL` and optional `DB_ECHO` from the normal
Pydantic settings sources. Copy `backend/.env.example` to an ignored local
environment file only when overrides are needed; never commit real secrets.

> **Danger — deletes all local QwenPaw database data:**
> `docker compose down -v`. Normal `docker compose down` retains the named volume.

## 已实现接口（Phase 1/2）

| 方法 | 路径 | 说明 |
|------|------|------|
| GET  | `/api/v1/health` | 健康检查 + 配置状态 |
| POST | `/api/v1/users` | 创建用户（占位，内存） |
| PUT  | `/api/v1/users/{id}/preferences` | 更新偏好 |
| GET  | `/api/v1/pois` · `/{id}` | POI 列表 / 详情 |
| GET  | `/api/v1/routes` · `/{id}` | 预设路线列表 / 详情 |
| POST | `/api/v1/routes/match` | 按偏好规则匹配路线（Phase 2） |

## 目录

```
backend/app/
├── main.py            # FastAPI 入口
├── core/config.py     # 从 .env 读配置
├── models/            # POI / Route / User Pydantic 模型
├── db/data.py         # 加载 data/*.json
├── services/          # route_matcher 等业务逻辑
├── agents/            # Phase 3: QwenPaw 6 Agent
└── api/               # 路由层（/api/v1）
```

> 路线规则匹配在 Phase 2 用作初筛 + 兜底；Phase 3 引入 QwenPaw 路线微调 Agent 后，
> Agent 在 `routes/match` 返回结果上做自然语言微调（换节点 / 加休息 / 调顺序）。
