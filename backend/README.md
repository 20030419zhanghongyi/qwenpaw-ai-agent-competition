# QwenPaw 澳门 AI 旅游助手后端

本目录提供面向 Agent 与小程序团队的稳定 FastAPI 数据服务。POI、路线模板、Trip、
Checkin、收藏和反馈均使用 PostgreSQL/PostGIS 持久化。

## 技术栈

- Python 3.11+
- FastAPI、Pydantic v2
- SQLAlchemy 2、Alembic
- PostgreSQL 16、PostGIS 3.4
- pytest

## 环境准备

以下命令均在仓库根目录执行，且只使用项目虚拟环境：

```powershell
Set-Location C:\Users\AW\Desktop\qwenpaw-ai-agent-competition

# 首次创建虚拟环境时执行
py -m venv .venv

# 安装项目声明的运行和测试依赖
.\.venv\Scripts\python.exe -m pip install -e ".\backend[dev]"
```

默认开发数据库连接已与根目录 `compose.yml` 对齐。需要覆盖配置时，可参考
`backend/.env.example` 设置进程环境变量或创建被 Git 忽略的本地 `.env`；不要提交真实密钥。

## 启动 Docker 数据库

```powershell
docker compose up -d db
docker compose ps
```

预期 `qwenpaw-postgis` 状态为 `healthy`。停止服务但保留数据：

```powershell
docker compose stop db
```

`docker compose down -v` 会删除本地数据库 volume，不应作为日常停止命令。

## 数据库迁移

```powershell
Push-Location backend
..\.venv\Scripts\python.exe -m alembic upgrade head
..\.venv\Scripts\python.exe -m alembic current
..\.venv\Scripts\python.exe -m alembic heads
..\.venv\Scripts\python.exe -m alembic check
Pop-Location
```

当前 Alembic head 为 `20260713_03`。

## 初始化 POI 与路线模板数据

必须先导入 POI，再导入路线模板，因为 `route_template_stops.poi_id` 外键引用 `pois.poi_id`。
两个脚本均支持重复执行，不会创建重复记录，也不会修改源 Excel/JSON。

```powershell
Push-Location backend

# 将路径替换为只读 POI Excel 的实际位置
..\.venv\Scripts\python.exe scripts\import_pois.py `
  "C:\path\to\Macau_Route_Database_simple.xlsx"

..\.venv\Scripts\python.exe scripts\import_routes.py ..\data\routes.json

Pop-Location
```

## 启动 API

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

数据库离线时 health 仍返回 HTTP 200，但 `database_status` 为 `unavailable`。

## 测试

测试需要本机 PostGIS 容器运行并已完成迁移与数据导入。

```powershell
$env:PYTHONDONTWRITEBYTECODE = "1"
Push-Location backend
..\.venv\Scripts\python.exe -m pytest -q -p no:cacheprovider
Pop-Location
Remove-Item Env:PYTHONDONTWRITEBYTECODE -ErrorAction SilentlyContinue
```

## 核心 API

| 方法 | 路径 | 成功响应 | 说明 |
|---|---|---|---|
| GET | `/api/v1/health` | 200 | API 与数据库健康状态 |
| GET | `/api/v1/pois` | 200 | POI 列表与分类过滤 |
| GET | `/api/v1/pois/nearby` | 200 | PostGIS 附近 POI 查询 |
| GET | `/api/v1/pois/{poi_id}` | 200 | POI 详情 |
| GET | `/api/v1/routes` | 200 | 路线模板列表 |
| GET | `/api/v1/routes/{route_id}` | 200 | 路线模板详情 |
| POST | `/api/v1/routes/match` | 200 | 按偏好匹配路线 |
| POST | `/api/v1/routes/adjust` | 200 | 按现有规则调整路线 |
| POST | `/api/v1/trips` | 201 | 创建 Trip |
| GET | `/api/v1/trips/{trip_id}` | 200 | Trip 详情与进度 |
| GET | `/api/v1/users/{user_id}/current-trip` | 200 | 当前进行中的 Trip |
| POST | `/api/v1/trips/{trip_id}/checkins` | 200 | 幂等打卡 |
| GET | `/api/v1/trips/{trip_id}/progress` | 200 | Trip 进度 |
| GET | `/api/v1/users/{user_id}/trips` | 200 | 用户行程历史 |
| POST | `/api/v1/users/{user_id}/favorites/pois/{poi_id}` | 200/201 | 幂等收藏 |
| DELETE | `/api/v1/users/{user_id}/favorites/pois/{poi_id}` | 204 | 幂等取消收藏 |
| GET | `/api/v1/users/{user_id}/favorites/pois` | 200 | 收藏列表 |
| POST | `/api/v1/trips/{trip_id}/feedback` | 200/201 | 新增或更新反馈 |
| GET | `/api/v1/trips/{trip_id}/feedback` | 200 | 查询反馈 |

## 错误响应契约

业务错误统一使用 FastAPI JSON 结构：

```json
{
  "detail": "error description"
}
```

- `404 Not Found`：POI、路线或 Trip 不存在。
- `409 Conflict`：例如尚未完成的 Trip 提交反馈。
- `422 Unprocessable Entity`：请求字段校验失败，或 POI 不属于 Trip 等业务校验失败。

字段级 422 错误的 `detail` 为 FastAPI 标准错误数组。以 `/openapi.json` 中的 schema 为最终契约。

## 交付检查

交付或联调前确认：

1. `docker compose ps` 显示数据库 healthy。
2. `alembic current` 与 `alembic heads` 一致。
3. POI 与路线导入脚本已成功运行。
4. `/api/v1/health` 返回 `database_status=ok`。
5. 全量 pytest 通过。
