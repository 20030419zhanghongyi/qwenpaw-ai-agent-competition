#!/bin/sh
# 一次性数据初始化（幂等，可重复运行）：
#   1) 确保扩展 postgis + vector（首次建库由 db/init.sql 已建，此处兜底已存在的库）
#   2) alembic 建后端表（pois / route_templates / trips / ...）
#   3) 建 RAG 表 poi_chunks（rag/schema.sql）
#   4) 导 POI（xlsx） —— 必须先于 routes（routes 有 POI 外键校验）
#   5) 导路线模板（routes.json）
# 用 psycopg 直连（app 镜像无 psql）。DATABASE_URL 由 compose 注入（指向 db 服务）。
set -e
cd /app/backend

PY="import os,psycopg;u=os.environ['DATABASE_URL'].replace('postgresql+psycopg://','postgresql://');c=psycopg.connect(u);c.autocommit=True"

echo "[seed] 1/6 ensure extensions (postgis + vector)..."
python -c "$PY;cur=c.cursor();cur.execute('CREATE EXTENSION IF NOT EXISTS postgis');cur.execute('CREATE EXTENSION IF NOT EXISTS vector');print('ok')"

echo "[seed] 2/6 alembic upgrade head (backend tables)..."
python -m alembic upgrade head

echo "[seed] 3/6 create poi_chunks (rag/schema.sql)..."
python -c "$PY;cur=c.cursor();cur.execute(open('/app/rag/schema.sql').read());print('ok')"

echo "[seed] 4/6 import POIs (xlsx)..."
python scripts/import_pois.py /app/background/raw_data/macau_route/Macau_Route_Database_simple.xlsx

echo "[seed] 5/6 import route templates (routes.json)..."
python scripts/import_routes.py /app/data/routes.json

echo "[seed] 6/6 upsert border ports (ports.json)..."
python scripts/import_ports.py /app/data/ports.json

echo "[seed] done"
