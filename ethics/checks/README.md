# checks/ — 伦理合规本地检查

本地可跑（CI / 提交前）的伦理合规测试与脚本，对应 `实施清单.md` 各节的"怎么验证"。

## 计划放置

| 文件 | 作用 | 对应原则 |
|------|------|----------|
| `test_fairness.py` | 同偏好换语言，断言路线排名一致；扫描 matcher 是否读取禁止字段 | 公平性（§2） |
| `test_transparency.py` | 断言讲解/路线响应含 `source_type` / `ai_generated` / `confidence` | 透明度（§4） |
| `test_safety_constraints.py` | 超时长/超体力偏好被约束裁剪；未审核路线不进推荐池 | 安全（§6） |
| `scrub_image.py` → 见 `scripts/` | 图片上传前剥离 EXIF（+ 人脸/车牌模糊） | 私隐（§5） |
| `test_anti_sycophancy.py` | 对抗样例：故意说错历史，断言 Agent 纠正而非附和 | 人类控制（§7） |

> 测试脚本与 `backend/tests/` 协同：纯接口/数据测试放 `backend/tests/`，
> 涉及伦理断言（跨语言一致性、字段必含、对抗纠正）的放这里并标注归属，方便答辩时单独展示。

## 初赛建议先落地

1. `test_fairness.py` —— 成本最低、最有说服力（一条测试证明"不因语言歧视"）。
2. `test_transparency.py` —— 保证每个 AI 输出都带来源/置信度字段。

> 待 QwenPaw Agent 联调（Phase 3）后，`test_anti_sycophancy.py` 用真实 Agent 跑对抗样例。
