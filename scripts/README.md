# Scripts — 本地配置、数据清洗与批处理

| 脚本 | 职责 | 阶段 |
|------|------|------|
| `configure_qwenpaw_windows.ps1` | PowerShell 7 一键配置、备份更新 Skill、只读验证 | 已实现 |
| `configure_qwenpaw_macos.sh` | macOS 一键配置 QwenPaw | 已实现 |
| `sync_qwen_image_config.sh` | macOS 同步图片工具凭据与职责分工 | 已实现 |
| `clean_xhs.py` | 小红书离线数据 → `data/weights.json` 权重表 | Phase 1（待实现清洗逻辑） |
| `background/report_assets/scripts/*.py` | 调研图表生成（已有，见 `background/`） | 已完成 |

## Windows QwenPaw 配置

先初始化 QwenPaw、配置模型并保持服务运行。仓库根目录执行：

```powershell
pwsh -NoProfile -File scripts/configure_qwenpaw_windows.ps1 -UpdateExistingSkills
pwsh -NoProfile -File scripts/configure_qwenpaw_windows.ps1 -VerifyOnly
```

省略 `-UpdateExistingSkills` 时保留不同的已有 Skill 副本并告警；更新模式只替换
项目 `SKILL.md`，原件与配置清单备份至 QwenPaw 的 `backups/storywalk/`。
备份可能包含凭据，不可提交或分享。脚本不调用模型、图片生成、TTS 或 `doctor`。
完整参数、当前 Agent 映射与工具配置见[中文 README](../README.zh-CN.md#配置-qwenpaw-运行资产)。

隔离测试（不访问真实 QwenPaw 或后端数据库）：

```powershell
.\.venv\Scripts\python.exe -m pytest scripts/tests/test_configure_qwenpaw_windows.py -q -p no:cacheprovider
```

## clean_xhs.py

- **输入**：`background/raw_data/xhs/xhs_search_*.xlsx`（100 高赞笔记 + 751 评论）
- **输出**：`data/weights.json`，含 `poi_heat` / `pain_points` / `nicome_candidates`
- **约束**：只用现有离线数据集，不做实时爬取

```bash
python scripts/clean_xhs.py
```

> 后续可加 `build_routes.py`：根据权重表半自动生成/校验预设路线库 `data/routes.json`。
