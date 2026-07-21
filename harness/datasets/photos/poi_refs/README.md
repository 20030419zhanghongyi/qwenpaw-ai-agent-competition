# poi_refs/ —— 明信片场景参考图（phase 1）

本目录存放从网上为各 POI 收集的**实景参考图**，供后续明信片插画（`view_image`）使用。

与上级目录中的评测正/负样本（`senado_square.jpg` 等）分开：那些是 photo-agent 评测固定集；
这里是按 `poi_id` 批量收集的参考图。

## 命名

```text
harness/datasets/photos/poi_refs/{poi_id}.jpg   # 或 .png / .webp
```

例：`poi_senado.jpg`、`poi_0001.jpg`。

来源多为 Openverse / Flickr 等 CC 图片；具体 URL 记在
`data/postcard_scenes/{poi_id}/_brief.json` 的 `sources` / `ref_image_url`。

## 收集命令

```bash
cd backend
python scripts/generate_postcard_scenes.py --research-only
```

不调用 QwenPaw，也不生成 SVG。本目录内容默认 gitignore（体积大）；需要时可挑选少量入库。
