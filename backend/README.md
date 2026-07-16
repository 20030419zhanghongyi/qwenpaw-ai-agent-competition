# QwenPaw 澳门 AI 旅游助手后端

## 1. 项目简介

本后端为 QwenPaw 澳门 AI 旅游助手提供稳定的数据和 REST API 服务，面向项目队友、指导老师、比赛评委，以及后续接入 Qwen Agent 和微信小程序的开发者。

后端主要负责：

- 澳门地点（POI）数据管理与空间查询
- 路线模板及路线节点管理
- 用户旅行状态、行程与打卡管理
- 收藏、行程反馈和历史行程管理
- 为 Agent 和小程序提供稳定、可验证的 REST API

本目录聚焦后端基础设施与数据接口，不包含 Qwen Agent、Prompt、AI 推理逻辑或前端小程序实现。

### 总体架构

```text
小程序 / Qwen Agent
        ↓ HTTP / JSON
     FastAPI API
        ↓
    Service 业务层
        ↓
  Repository 数据层
        ↓
SQLAlchemy + PostgreSQL/PostGIS
```

## 2. 技术栈

- Python 3.11+
- FastAPI
- PostgreSQL 16
- PostGIS 3.4
- SQLAlchemy 2
- Alembic
- Docker Compose
- Pytest

## 3. 已完成模块

### 数据库基础设施

已完成：

- 使用 Docker Compose 提供 PostgreSQL/PostGIS 本地开发环境
- 使用 SQLAlchemy ORM 定义业务数据模型
- 使用 Alembic 管理数据库版本和迁移
- 支持数据库 upgrade、downgrade 和重复 upgrade 验证
- 提供数据库健康检查；数据库不可用时 API 仍返回 HTTP 200，并通过 `database_status=unavailable` 标识状态

当前 Alembic head 为 `20260714_01`（用户落库：`users` 表新增 `name` + `preference` JSON 字段）。

### POI 地点数据库

澳门地点数据已由只读 Excel 数据源导入 PostgreSQL：

- 共导入 341 条 POI
- 使用唯一 `poi_id` 作为 canonical ID
- 使用 PostGIS `geometry(Point, 4326)` 保存空间坐标
- 在位置字段上创建 GiST 空间索引
- 支持 POI 列表、单地点详情和附近地点查询
- 导入脚本支持幂等执行，不修改原始 Excel，也不会产生重复数据

验证结果：

- `SELECT COUNT(*) FROM pois` 返回 `341`
- 单地点 `poi_id` 查询成功
- nearby 空间查询成功，并按照距离排序

### Route Template 数据库

路线模板已从静态数据迁移到：

- `route_templates`
- `route_template_stops`

验证结果：

- 6 条路线模板
- 38 个有序路线节点
- 路线节点使用 canonical `poi_id` 外键关联 `pois`
- 导入脚本支持幂等执行，不修改原始路线 JSON

### Trip 行程持久化

已完成以下能力的 PostgreSQL 持久化：

- Trip 创建
- Trip 详情查询
- 用户当前 Trip 查询
- Checkin 创建
- Trip Progress 计算

数据访问遵循分层结构：

```text
API → Service → Repository → PostgreSQL
```

API 层不直接访问数据库，业务逻辑与数据访问职责相互隔离。

### 用户相关数据

已完成：

- POI 收藏与取消收藏
- 收藏列表查询
- Trip Feedback 创建、查询和更新
- 用户历史行程查询

Favorite 和 Feedback 均通过 Repository 持久化至 PostgreSQL，并保持原有 API 请求、响应和错误码兼容。

### API 稳定化

已完成：

- 为非 204 API 配置 `response_model`
- 完善 Swagger UI、ReDoc 和 OpenAPI Schema
- 统一核心接口的摘要与说明
- 明确 `404 Not Found`、`409 Conflict` 和 `422 Unprocessable Entity` 错误契约
- 增加覆盖 POI、Route、Trip、Checkin、Favorite 和 Feedback 的 API contract 测试

## 4. 验证实验与测试结果

### 2026-07-16 导览与安全增量

- `POST /api/v1/guide/trigger`：PostGIS 附近 POI 触发；匿名会话同一 POI 10 分钟防重复，确认后才调讲解。
- `POST /api/v1/routes/walk-path`：有序 POI → 高德逐段距离、时间与 polyline。
- `POST /api/v1/guide/tts`：普通话、粤语、英语、葡语固定音色；私有 OSS 短期 URL。
- `/guide/photo` 的低置信度明确返回 `uncertain`、重拍/手选动作，并阻止不确定结果进入 RAG 讲解。
- 全 Agent 入口文本隔离、分级限流、去标识 trace 与 PostgreSQL `audit_events`（30 天留存）。

缺少高德、TTS 或 OSS 配置时，相关接口明确返回 503，不伪造路径或音频 URL。

以下结果在本地 PostGIS 容器和项目虚拟环境中完成验证。

### 数据库验证

已通过：

- PostgreSQL/PostGIS 容器启动及 healthy 状态检查
- PostGIS 扩展版本验证：`3.4.3`
- Alembic `upgrade head`
- Alembic `downgrade base`
- Alembic 再次 `upgrade head`
- `alembic current` 与 `alembic heads` 均为 `20260714_01 (head)`
- `alembic check` 返回无待生成迁移

### POI 数据验证

验证结果：

- 成功导入 341 条 POI
- 重复运行导入不会产生重复数据
- 使用 canonical `poi_id` 查询地点成功
- nearby 空间查询成功
- 数据库存储的经纬度与导入数据一致

### 空间查询验证

使用大三巴牌坊坐标进行 PostGIS 空间查询：

```text
longitude: 113.545883
latitude:  22.194627
```

返回结果：

```text
大三巴牌坊  distance=0.000m
旧城墙遗址  distance=24.305m
恋爱·电影馆 distance=33.612m
大三巴斜巷  distance=43.480m
恋爱巷      distance=49.455m
```

大三巴牌坊距离为 0，其他附近地点按照距离从近到远排列。

### Route Template 数据验证

- `route_templates`：6 条记录
- `route_template_stops`：38 条记录
- 节点顺序约束验证通过
- 所有节点均通过外键引用 `pois.poi_id`
- Route Match API 保持原有响应结构兼容

### 自动化测试

最终全量测试结果：

```text
97 passed
```

测试覆盖：

- Health API
- POI API 与 PostGIS nearby 查询
- Route API 与路线模板 Repository
- Trip API、Checkin 和 Progress
- Profile、Favorite 和 Feedback API
- Database integration
- Repository 数据持久化
- API contract、response model 和错误码

## 5. 环境准备

以下命令均在仓库根目录执行，并只使用项目虚拟环境：

```powershell
Set-Location C:\Users\AW\Desktop\qwenpaw-ai-agent-competition

# 首次创建虚拟环境
py -m venv .venv

# 安装项目声明的运行与测试依赖
.\.venv\Scripts\python.exe -m pip install -e ".\backend[dev]"
```

默认开发数据库连接已与仓库根目录的 `compose.yml` 对齐。需要覆盖配置时，可参考 `backend/.env.example` 设置进程环境变量或创建被 Git 忽略的本地 `.env`。不要提交真实密钥或 `.env`。

## 6. 启动数据库与执行迁移

### 启动 Docker 数据库

```powershell
docker compose up -d db
docker compose ps
```

预期 `qwenpaw-postgis` 状态为 `healthy`。

停止服务但保留数据：

```powershell
docker compose stop db
```

`docker compose down -v` 会删除本地数据库 volume，不应作为日常停止命令。

### 执行数据库迁移

```powershell
Push-Location backend
..\.venv\Scripts\python.exe -m alembic upgrade head
..\.venv\Scripts\python.exe -m alembic current
..\.venv\Scripts\python.exe -m alembic heads
..\.venv\Scripts\python.exe -m alembic check
Pop-Location
```

### 导入 POI 和路线模板

必须先导入 POI，再导入路线模板，因为 `route_template_stops.poi_id` 外键引用 `pois.poi_id`。两个脚本都支持重复执行，且不会修改只读 Excel/JSON 数据源。

```powershell
Push-Location backend

# 将路径替换为本机只读 POI Excel 的实际位置
..\.venv\Scripts\python.exe scripts\import_pois.py `
  "C:\path\to\Macau_Route_Database_simple.xlsx"

..\.venv\Scripts\python.exe scripts\import_routes.py ..\data\routes.json

Pop-Location
```

## 7. 启动 API 与接口文档

```powershell
Push-Location backend
..\.venv\Scripts\python.exe -m uvicorn app.main:app `
  --host 127.0.0.1 --port 8000 --reload
Pop-Location
```

- Swagger UI：<http://127.0.0.1:8000/docs>
- ReDoc：<http://127.0.0.1:8000/redoc>
- OpenAPI JSON：<http://127.0.0.1:8000/openapi.json>
- 健康检查：<http://127.0.0.1:8000/api/v1/health>

## 8. 核心 API 列表

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/api/v1/health` | API 与数据库健康状态 |
| POST | `/api/v1/users/register` | 注册用户并签发 JWT（落 PostgreSQL） |
| POST | `/api/v1/users/login` | 极简登录：user_id 换 JWT（demo 不设密码） |
| GET | `/api/v1/users/me` | Bearer token 获取当前用户 |
| GET | `/api/v1/users/{user_id}` | 查询用户 |
| PUT | `/api/v1/users/{user_id}/preferences` | 更新用户偏好（整体 JSON 落库） |
| GET | `/api/v1/pois` | POI 列表和分类过滤 |
| GET | `/api/v1/pois/nearby` | PostGIS 附近 POI 查询 |
| GET | `/api/v1/pois/{poi_id}` | POI 详情 |
| GET | `/api/v1/routes` | 路线模板列表 |
| GET | `/api/v1/routes/{route_id}` | 路线模板详情 |
| POST | `/api/v1/routes/match` | 按用户偏好匹配路线 |
| POST | `/api/v1/routes/adjust` | 按现有规则调整路线 |
| POST | `/api/v1/trips` | 创建 Trip |
| GET | `/api/v1/trips/{trip_id}` | Trip 详情 |
| GET | `/api/v1/users/{user_id}/current-trip` | 用户当前 Trip |
| POST | `/api/v1/trips/{trip_id}/checkins` | 创建 Checkin |
| GET | `/api/v1/trips/{trip_id}/progress` | 查询 Trip 进度 |
| GET | `/api/v1/users/{user_id}/trips` | 用户历史行程 |
| POST | `/api/v1/users/{user_id}/favorites/pois/{poi_id}` | 收藏 POI |
| DELETE | `/api/v1/users/{user_id}/favorites/pois/{poi_id}` | 取消收藏 POI |
| GET | `/api/v1/users/{user_id}/favorites/pois` | 收藏列表 |
| POST | `/api/v1/trips/{trip_id}/feedback` | 创建或更新反馈 |
| GET | `/api/v1/trips/{trip_id}/feedback` | 查询反馈 |

## 9. 错误响应规范

业务错误统一使用 FastAPI JSON 响应：

```json
{
  "detail": "error description"
}
```

- `404 Not Found`：POI、路线模板、Trip 或其他目标资源不存在
- `409 Conflict`：资源当前状态不允许操作，例如未完成 Trip 提交反馈
- `422 Unprocessable Entity`：请求字段校验失败，或 POI 不属于 Trip 等业务校验失败

字段级 422 错误的 `detail` 使用 FastAPI 标准错误数组。最终接口契约以 `/openapi.json` 为准。

## 10. 运行测试

测试前请确保本地 PostGIS 容器已启动，并已完成数据库迁移和基础数据导入：

```powershell
$env:PYTHONDONTWRITEBYTECODE = "1"

Push-Location backend
..\.venv\Scripts\python.exe -m pytest -q -p no:cacheprovider
Pop-Location

Remove-Item Env:PYTHONDONTWRITEBYTECODE -ErrorAction SilentlyContinue
```

测试完成后不要提交测试生成的 `harness/results/traces/traces.jsonl`、pytest cache 或虚拟环境文件。

## 11. 交付检查

联调或交付前请确认：

1. `docker compose ps` 显示数据库为 `healthy`。
2. `alembic current` 与 `alembic heads` 均为 `20260714_01 (head)`。
3. POI 和路线模板导入脚本已成功执行。
4. `/api/v1/health` 返回 `database_status=ok`。
5. Swagger UI 和 OpenAPI JSON 可正常访问。
6. 全量 Pytest 测试通过。
7. 工作区不包含 `.env`、`.venv`、trace 或 pytest cache 改动。

## 12. Docker 一键启动（统一库，推荐）

整个后端（数据库 + 应用 + 数据）都容器化，队友无需本地装 Python 依赖或手动建库。

**前置**：已安装 Docker Desktop；本机已启动 QwenPaw（监听 `:8088`）。

```bash
# 1) 准备配置（填入 DashScope / QwenPaw / 高德 等 key）
cp .env.example .env

# 2) 一键起：统一数据库(PostGIS+pgvector) + 后端 + 自动建表导数据
docker compose up -d --build

# 3) 访问
open http://localhost:8000/docs        # Swagger UI
```

`up` 会自动完成：建库并启用 `postgis`+`vector` 扩展 → alembic 迁移建表 → 导入 341 POI 与 6 路线模板 → 启动后端。后端会在数据就绪后才对外服务（依赖 `seed` 完成成功）。

常用命令：

```bash
docker compose ps                       # db=healthy / seed=exited(0) / backend=running
docker compose logs -f seed             # 看建表/导数据过程
docker compose stop                     # 停（保留数据）
docker compose down -v                  # 彻底重置（删库卷，下次 up 重新建库导数）
```

**RAG / 文化讲解（可选）**：默认不灌向量数据（省 API 费用）。需要时手动跑一次向量化，并在 `.env` 开启对应开关：

```bash
docker compose run --rm rag-seed        # 把 data/pois.json 向量化灌入 poi_chunks（~1 分钟）
# .env 里设：PGVECTOR_ENABLED=true、GUIDE_AGENT_ENABLED=true
```

**说明**：

- QwenPaw 本体**不在容器内**，每人本机跑 `:8088`；容器经 `host.docker.internal` 连宿主机（Mac/Windows 原生支持，Linux 自动加 `host-gateway`）。
- 密钥不打进镜像，全部走宿主机 `.env`（`.dockerignore` 已排除）。
- 统一库同时承载后端表（`pois`/`route_templates`/…）与 RAG 表（`poi_chunks`），共用一条 `DATABASE_URL`，不再有 PostGIS 与 pgvector 两个容器抢端口的问题。
