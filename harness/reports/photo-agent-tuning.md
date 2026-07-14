# Photo Agent 调优记录（2026-07-13）

## 结论

`photo` Agent 在同一组 20 条冻结样本上，规则评分从 **0.925 提升到 1.000**；
正样本完整通过率从 9/12 提升到 12/12，负样本拒识继续保持 8/8。

| 指标 | before | 中间轮 | final |
|---|---:|---:|---:|
| 总分 | 0.925 | 0.963 | **1.000** |
| 满分样本 | 17/20 | 18/20 | **20/20** |
| 正样本候选命中 | 9/12 | 11/12 | **12/12** |
| 负样本正确拒识 | 8/8 | 8/8 | **8/8** |
| 结构化解析成功 | 19/20 | 20/20 | **20/20** |

## 评测设计

- 模型：`aliyun-tokenplan-intl/qwen3.6-plus`，通过实际运行的 QwenPaw `photo` Agent 调用。
- 正样本 12 条：议事亭前地、妈祖阁（妈阁庙）、大三巴牌坊、龙环葡韵、玫瑰堂、东望洋灯塔，每个 POI 两个视角。
- 负样本 8 条：2 条非澳门地标 + 6 条图表/截图。
- 每次把样本复制成随机临时文件名再交给 `view_image`，避免从文件名泄漏答案。
- before / final 使用同一份 `cases.json` 和同一套 rubric，没有删除失败样本或改宽评分口径。

图片来源与授权见 [`harness/datasets/photos/README.md`](../datasets/photos/README.md)，逐条预期与评分规则见
[`harness/datasets/cases.json`](../datasets/cases.json) 和 [`harness/rubrics/rule_checks.md`](../rubrics/rule_checks.md)。

## before 失败分析

- `p04`：识别出繁体「龍環葡韻」，但未归一到知识库简体标准名。
- `p08`：识别出「媽閣廟」，但别名未归一到「妈祖阁（妈阁庙）」。
- `p11`：视觉识别正确，但描述中的裸双引号造成 JSON 解析失败。

## 调优内容

1. **Skill 约束**：先列视觉证据再匹配 POI，增加 6 个常见 POI 的简体标准名与组合视觉锚点，强制非澳门地标和图表返回 `null`。
2. **结构稳定**：要求严格 JSON 和引号转义；后端增加有限的裸引号修复，并将偶发的 `visual_evidence/reasoning` 字段漂移归一到 `description`。
3. **名称与安全边界**：繁简/英葡别名归一到 `data/pois.json` 标准名；知识库外候选被拒绝并限制置信度。
4. **近邻 POI 消歧**：同图有教堂与广场铺装时，以画面主体的专属组合特征优先；避免玫瑰堂因前景碎石路被误判为议事亭前地。

## 复现

在 `backend/` 目录执行（QwenPaw 需运行在 `127.0.0.1:8088`）：

```powershell
..\.venv\Scripts\python.exe -m app.eval.runner --only photo --run-id photo-baseline
..\.venv\Scripts\python.exe -m app.eval.runner --only photo --run-id photo-tuned-final
..\.venv\Scripts\python.exe -m app.eval.compare --runs photo-baseline photo-tuned-final
```

证据产物：

- [`scores_photo-baseline.json`](../results/scores_photo-baseline.json)
- [`scores_photo-tuned.json`](../results/scores_photo-tuned.json)（中间轮）
- [`scores_photo-tuned-final.json`](../results/scores_photo-tuned-final.json)
- [`compare_photo-baseline_vs_photo-tuned-final.html`](../results/compare_photo-baseline_vs_photo-tuned-final.html)

> 多模态模型输出存在随机性；`1.000` 是本次固定数据集的实测结果，不代表所有现场图片的绝对准确率。
