# 如何手动删改 POI

路线匹配读的是仓库里的 **`data/pois.json`**（主题日 / 密点填充）。  
数据库里的点来自 seed 时导入的 Excel，和 JSON 可能不完全同步——**改排线逻辑以 `pois.json` 为准**。

## 推荐做法（改 JSON）

1. 打开 [`data/pois.json`](pois.json)。
2. 在 `"pois": [ ... ]` 数组里找到要删的对象（搜 `name_zh` 或 `id`，如 `poi_0080`）。
3. **删掉整条 POI 对象**（注意逗号，保持合法 JSON）。
4. 若该 `id` 还出现在 [`data/routes.json`](routes.json) 的节点里，一并改掉或删节点，否则预设模板会引用失效。
5. 本地校验：

```bash
python -c "import json; json.load(open('data/pois.json', encoding='utf-8')); print('ok')"
```

6. 重建后端让 Docker 带上新数据：

```bash
docker compose up -d --build backend
```

7. 前端硬刷新后**重新生成路线**（旧会话不会自动丢掉已删点）。

## 若还要改数据库里的点（地图 / 步行查库）

Seed 用的是：

`background/raw_data/macau_route/Macau_Route_Database_simple.xlsx`

- 在 Excel 里删行后重新 seed，或  
- 在库里 `DELETE FROM pois WHERE poi_id = '...'`（需自行处理路线外键）。

只改 `pois.json`、不改库时：主题生成会少用该点，但 `/walk-path` 若仍收到该 id 可能 404。

## 不建议

- 不要只在前端隐藏；后端仍会排进路线。  
- 不要用 `git add -f` 提交本地 trace / `.env`。
