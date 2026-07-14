-- 容器首次建库时由 postgres entrypoint 自动执行（/docker-entrypoint-initdb.d/init.sql）。
-- 启用两个扩展：postgis（POI 地理/空间查询）+ vector（RAG 语义检索）。
-- seed 服务里也会 CREATE EXTENSION IF NOT EXISTS 兜底（已建库的情况）。
CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS vector;
