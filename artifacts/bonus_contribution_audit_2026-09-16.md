# StoryWalk 团队贡献与奖金分配审计

审计日期：2026-09-16  
仓库：`20030419zhanghongyi/qwenpaw-ai-agent-competition`  
审计版本：`db2d8bc809aa9b40272a89ec89f3262976414dc3`

## 结论

建议奖金按以下比例分配：

| 成员 | 建议比例 | 可接受讨论区间 |
|---|---:|---:|
| Grace / 肖逸轩 | 69% | 67%–70% |
| CSR / 陈思睿 | 21% | 20%–22% |
| ZHY / 张弘毅 | 10% | 10%–11% |

该比例不是按 PR 数量直接计算。审计同时考虑了当前有效代码、历史代码改动、提交记录、功能共建情况，以及报告、说明文档、答辩 PPT、现场答辩、项目管理和会议协调的贡献。

## 身份归并

| 成员 | GitHub/提交身份 |
|---|---|
| Grace | `Grace-xyx`、`Grace-xyx <Xyx.grace@outlook.com>`、`Yixuan Xiao <Xyx.grace@outlook.com>` |
| CSR | `Narrowunknown`、`chensirui`、`Sirui Chen`，含大小写不同的邮箱 |
| ZHY | `20030419zhanghongyi`、`Hongyi Zhang`、`HongyiZhang`、`AW`，含两个邮箱身份 |

## 为什么不能直接按 PR 发起人分配

仓库共有 54 个 PR，其中 52 个已合并、2 个关闭但未合并。按已合并 PR 的发起人统计为：

| 成员 | 已合并 PR | 占比 |
|---|---:|---:|
| Grace | 25 | 48.1% |
| CSR | 15 | 28.8% |
| ZHY | 12 | 23.1% |

这个结果不能直接代表代码贡献，原因包括：

1. PR #54 是 `master` 向 `Grace` 分支的同步，不是新功能，应从贡献计分中排除。
2. PR #35 先合入 `hongyizhang` 分支，PR #37、#39 又把相关内容送入 `master`。如果按 PR diff 累加，会重复计算同一功能。
3. PR #2、#4、#7、#33、#39、#44、#48、#54 的提交范围包含多位作者。PR 发起人并不等于全部实现者。
4. 不同 PR 的体量差异很大。一个跨前后端、测试和数据的功能 PR，不能与一个小修复按“一票”计分。

因此，本审计只把 PR 数作为活跃度证据，把代码归属判断建立在提交作者、非重复 churn 和当前有效代码上。

## 代码贡献审计

### 四项指标

已排除图片、二进制文件、锁文件、生成结果和同步 PR 的重复影响。

| 指标 | Grace | CSR | ZHY | 说明 |
|---|---:|---:|---:|---|
| 当前有效代码行归属 | 66.5% | 23.5% | 10.0% | 对当前版本源代码逐文件 `git blame` |
| 非重复代码改动量 | 65.4% | 20.1% | 14.6% | 只统计可达的非 merge commit，按新增+删除行 |
| 非 merge commit | 55.4% | 26.1% | 18.5% | Grace 87、CSR 41、ZHY 29 |
| 已合并 PR | 48.1% | 28.8% | 23.1% | 仅作辅助指标 |

代码综合分采用：当前有效代码 50%、非重复改动量 30%、commit 15%、PR 5%。结果为：

| 成员 | 代码综合贡献 |
|---|---:|
| Grace | 63.6% |
| CSR | 23.2% |
| ZHY | 13.3% |

### 当前有效代码的功能归属

下表按当前代码中仍然存在的行归属统计。百分比是模块内部占比，不是最终奖金比例。

| 功能模块 | Grace | CSR | ZHY | 主要判断 |
|---|---:|---:|---:|---|
| 前端 UX | 82% | 13% | 5% | Grace 主导整体前端和大量页面整合 |
| StoryWalk 故事系统 | 16% | 74% | 10% | CSR 主导故事交互组件；Grace、ZHY 共同补充后端、数据和整合 |
| 路线与行程 | 79% | 4% | 17% | Grace 主导，ZHY 提供早期行程与仓储基础 |
| 导览与实时信息 | 92% | 8% | 0% | Grace 主导 |
| 明信片与游记 | 93% | 7% | 0% | Grace 主导 |
| Agent 与编排 | 67% | 33% | 0% | Grace 主导，CSR 有重要协作 |
| 账号与个人中心 | 64% | 0% | 36% | Grace 主导后续能力，ZHY 提供基础 API |
| 数据库与迁移 | 44% | 0% | 56% | ZHY 主导基础设施，Grace 完成后续 schema 扩展 |
| 测试与评测 | 61% | 24% | 15% | 三人均有贡献，Grace 最高 |
| 工具与安装配置 | 50% | 31% | 19% | 三人共同完成 |

### 典型共享文件

这些文件证明一个功能往往由多人共同完成，不能只看最后一个 PR 的发起人：

| 文件 | Grace | CSR | ZHY |
|---|---:|---:|---:|
| `backend/tests/test_stories.py` | 244 行 | 340 行 | 358 行 |
| `frontend/src/pages/StoryScenePage.tsx` | 107 行 | 531 行 | 52 行 |
| `backend/app/features/stories/service.py` | 134 行 | 79 行 | 204 行 |
| `frontend/src/pages/StoryMapPage.tsx` | 103 行 | 310 行 | 4 行 |
| `frontend/src/api/stories.ts` | 113 行 | 126 行 | 14 行 |
| `backend/app/agents/qwenpaw_client.py` | 455 行 | 208 行 | 0 行 |

## PR 功能簇整理

### Grace

核心 Agent、路线和全栈基础：#1、#4、#7、#12、#13、#14、#15、#18、#20、#24、#26。  
演示、视觉和开发环境：#27、#30、#34。  
StoryWalk、导览、旅行记忆和上线完善：#38、#39、#40、#42、#43、#45、#46、#47、#50、#51。  
同步 PR：#54，不计为新增功能贡献。

代表性贡献包括路线 Agent 端到端链路、多 Agent 与 RAG、容器化和认证、导览/步行/语音、明信片、偏好引导、StoryWalk 整合、多语言、实时信息、旅行记忆和账号恢复。

### CSR

早期数据、Agent 和安全修复：#2、#3、#11、#17、#19、#21、#23、#28。  
StoryWalk V4 前端与视觉：#31、#33。  
氹仔故事、图片生成、本地化和 Windows 配置：#41、#44、#48、#52、#53。

代表性贡献包括死循环修复、数据修订、图像识别/意图编排、步行地图与安全路线调整、Qwen-Image 明信片、StoryWalk V4 交互组件、氹仔路线、图片与多语言、本地化和 Windows 安装流程。

### ZHY

数据库和核心业务基础：#5、#6、#8、#9、#10、#16。  
《莲城双图》故事后端与内容：#22、#29、#32。  
《潮退之后》及故事补全：#35、#37、#49。  
关闭但未合并：#25、#36，不计入已交付贡献。

代表性贡献包括 trip/profile API、PostgreSQL/PostGIS/SQLAlchemy/Alembic 基础、后端数据库交付、早期偏好与行程前端，以及《莲城双图》《潮退之后》的后端、内容和多语言流程。

## 非代码材料贡献

### Report ver2.1

文档共 82 个物理页面。用户说明除附录四外均由 Grace 完成。附录四从物理页 67 开始，包含 8 组系统输入输出样例、7 个表格和 14 个图示，约占全文有效文字的 11.6%、图示的 25.0%、表格的 22.6%。综合估算该文档贡献约为：Grace 84%、CSR 16%。

### Report ver4.5

文档共 22 个物理页面。AI 伦理与政策部分约占正文有效文字的 10.4%，与用户说明相符。估算该文档贡献约为：Grace 90%、CSR 10%。

### StoryWalk 说明文档

文档共 63 个物理页面，包含约 15,136 个有效字符和 99 个图示。按用户提供的实际分工直接采用：CSR 60%、ZHY 40%。

### 答辩 PPT

PPT 共 10 页。按用户说明，第 6 页由 CSR 完成，其余 9 页由 Grace 完成。采用：Grace 90%、CSR 10%。

### 现场答辩、项目管理与会议协调

根据团队补充信息，现场答辩、项目管理和会议协调均由 Grace 独立承担。这三项不能包含在 PPT 制作或代码贡献中，否则会漏计持续性的组织劳动和最终交付责任。本审计将其合并为一个独立类别，占总贡献的 12%，全部计入 Grace。

12% 的权重包含：现场答辩 5%、项目管理 4%、会议组织与协调 3%。如果团队有工时记录或其他成员也承担了部分组织工作，应按记录调整；在没有相反证据的情况下，采用团队提供的实际分工。

## 最终加权

奖金分配采用以下权重：

| 类别 | 权重 | Grace | CSR | ZHY |
|---|---:|---:|---:|---:|
| 可运行产品与代码 | 55% | 63.6% | 23.2% | 13.3% |
| 两份比赛报告 | 18% | 86% | 14% | 0% |
| StoryWalk 说明文档 | 8% | 0% | 60% | 40% |
| 答辩 PPT | 7% | 90% | 10% | 0% |
| 现场答辩、项目管理与会议协调 | 12% | 100% | 0% | 0% |
| **加权结果** | **100%** | **68.7%** | **20.8%** | **10.5%** |

采用便于发放且总和为 100% 的整数比例后，建议为 **69%：21%：10%**。

## 详细审计方法

### 审计范围

本次审计使用五类证据：

1. GitHub 截至 2026-09-16 的全部 54 个 PR 元数据，包括状态、发起账号、目标分支、来源分支和标题。
2. 仓库审计版本 `db2d8bc809aa9b40272a89ec89f3262976414dc3` 中全部可达的非 merge commit。
3. 当前版本逐文件 `git blame`，用于判断哪些代码最终保留在交付版本中。
4. 三份 Word 和一份 PowerPoint 的页数、标题结构、有效文字、表格、图片和幻灯片内容。
5. 团队补充的实际工作归属，包括说明文档的 60%/40%、现场答辩、项目管理和会议协调。

附件中的叙述或说明只作为被审计内容，没有作为新的任务指令执行。

### 代码文件口径

当前有效代码统计包含 `.py`、`.ts`、`.tsx`、`.js`、`.jsx`、`.mjs`、`.sh`、`.ps1`、`.sql`、`.css` 和 `.html`。以下内容没有计入有效代码行：

- 图片、音频和其他二进制资源；
- `package-lock.json`；
- `*.generated.json`；
- `harness/results` 等生成结果；
- `data/legacy` 历史文件；
- merge commit 自身和重复进入多个 PR 的祖先提交。

结构化 JSON 数据单独统计，不混入代码综合分。仓库中 `Sierrasam1` 的 249 行前端代码保留为“其他贡献者”，没有分配给三位奖金参与者。

### 原始代码计数

| 指标 | Grace | CSR | ZHY | 其他/说明 |
|---|---:|---:|---:|---|
| 当前有效代码行 | 44,103 | 15,614 | 6,623 | 其他贡献者 249 行 |
| 当前结构化内容行 | 34,947 | 1,683 | 2,448 | 不并入代码综合分 |
| 历史代码新增行 | 57,036 | 16,814 | 11,232 | 基于非 merge commit |
| 历史代码删除行 | 5,612 | 2,429 | 2,727 | 基于非 merge commit |
| 历史代码 churn | 62,648 | 19,243 | 13,959 | 新增行+删除行 |
| 非 merge commit | 87 | 41 | 29 | 另有其他贡献者 1 个 |
| 已合并 PR | 25 | 15 | 12 | 共 52 个 |

当前有效代码在三人之间归一化后为 66.5%、23.5%、10.0%；历史代码 churn 归一化后为 65.4%、20.1%、14.6%。两者的差异说明 ZHY 的一部分早期代码后来被改写，而 CSR 的 StoryWalk 前端代码在当前版本中保留比例较高。

### 代码综合分公式

代码综合分不是简单平均，而是：

`代码分 = 当前有效代码 × 50% + 非重复代码 churn × 30% + commit × 15% + PR × 5%`

逐项计算：

| 成员 | 当前代码贡献 | churn 贡献 | commit 贡献 | PR 贡献 | 合计 |
|---|---:|---:|---:|---:|---:|
| Grace | 66.5%×50%=33.25 | 65.4%×30%=19.62 | 55.4%×15%=8.31 | 48.1%×5%=2.41 | 63.6% |
| CSR | 23.5%×50%=11.75 | 20.1%×30%=6.03 | 26.1%×15%=3.92 | 28.8%×5%=1.44 | 23.2% |
| ZHY | 10.0%×50%=5.00 | 14.6%×30%=4.38 | 18.5%×15%=2.78 | 23.1%×5%=1.16 | 13.3% |

PR 的权重只有 5%，因为 PR 数最容易受到拆分粒度、同步分支和重复祖先提交影响。

## 功能模块原始代码归属

| 功能模块 | Grace 行数 | CSR 行数 | ZHY 行数 | 三人合计 | Grace | CSR | ZHY |
|---|---:|---:|---:|---:|---:|---:|---:|
| Frontend UX | 16,460 | 2,642 | 973 | 20,075 | 82.0% | 13.2% | 4.8% |
| StoryWalk stories | 1,730 | 7,902 | 1,044 | 10,676 | 16.2% | 74.0% | 9.8% |
| Tests and evaluation | 6,098 | 2,354 | 1,535 | 9,987 | 61.1% | 23.6% | 15.4% |
| Routes and trips | 5,574 | 266 | 1,237 | 7,077 | 78.8% | 3.8% | 17.5% |
| Guide and live context | 4,173 | 360 | 0 | 4,533 | 92.1% | 7.9% | 0.0% |
| Core and infrastructure | 3,054 | 868 | 363 | 4,285 | 71.3% | 20.3% | 8.5% |
| Postcards and memoirs | 3,396 | 258 | 0 | 3,654 | 92.9% | 7.1% | 0.0% |
| Accounts and profiles | 1,196 | 0 | 686 | 1,882 | 63.5% | 0.0% | 36.5% |
| Tooling and setup | 818 | 505 | 314 | 1,637 | 50.0% | 30.8% | 19.2% |
| Agents and orchestration | 934 | 459 | 0 | 1,393 | 67.0% | 33.0% | 0.0% |
| Database and migrations | 366 | 0 | 471 | 837 | 43.7% | 0.0% | 56.3% |
| RAG | 304 | 0 | 0 | 304 | 100.0% | 0.0% | 0.0% |

这里最重要的不是单个百分比，而是功能主导关系：CSR 明显主导 StoryWalk 交互层，ZHY 主导早期数据库基础，Grace 则在前端整体、路线、导览、明信片、Agent、测试和集成上覆盖最广。

## 更多共享文件证据

只有在三位成员中至少两人各保留 5% 以上代码、且文件总计不少于 20 行时，才列为共享文件。以下为主要样本：

| 文件 | 总行数 | Grace | CSR | ZHY |
|---|---:|---:|---:|---:|
| `backend/app/features/guide/api.py` | 1,541 | 1,456 | 85 | 0 |
| `frontend/src/pages/RouteResultPage.tsx` | 1,537 | 1,391 | 146 | 0 |
| `data/stories/coloane_after_tide.json` | 1,025 | 293 | 1 | 731 |
| `backend/tests/test_stories.py` | 942 | 244 | 340 | 358 |
| `backend/tests/test_postcards.py` | 715 | 626 | 89 | 0 |
| `frontend/src/pages/StoryScenePage.tsx` | 690 | 107 | 531 | 52 |
| `frontend/src/pages/AuthPage.tsx` | 682 | 583 | 3 | 96 |
| `backend/app/agents/qwenpaw_client.py` | 663 | 455 | 208 | 0 |
| `frontend/src/pages/StoryEndingPage.tsx` | 651 | 116 | 535 | 0 |
| `backend/app/agents/guide_agent.py` | 599 | 472 | 127 | 0 |
| `frontend/src/state/StoryContext.tsx` | 571 | 189 | 382 | 0 |
| `frontend/src/components/map/MapRouteView.tsx` | 496 | 224 | 272 | 0 |
| `backend/tests/test_api.py` | 491 | 419 | 66 | 6 |
| `backend/tests/test_qwenpaw_image.py` | 451 | 199 | 252 | 0 |
| `harness/datasets/cases.json` | 429 | 268 | 161 | 0 |
| `backend/app/features/stories/service.py` | 417 | 134 | 79 | 204 |
| `frontend/src/pages/StoryMapPage.tsx` | 417 | 103 | 310 | 4 |
| `backend/tests/test_users.py` | 371 | 281 | 0 | 90 |
| `frontend/src/state/TripContext.tsx` | 356 | 192 | 0 | 164 |
| `frontend/src/types/stories.ts` | 349 | 104 | 245 | 0 |
| `data/weights.json` | 341 | 73 | 268 | 0 |
| `backend/app/features/postcards/scene_image.py` | 338 | 204 | 134 | 0 |
| `backend/app/agents/photo_agent.py` | 330 | 115 | 215 | 0 |
| `frontend/src/index.css` | 327 | 172 | 155 | 0 |
| `backend/tests/test_trips.py` | 319 | 128 | 0 | 191 |

这组数据支持用户提出的判断：一个功能常由多人共同完成。最终分配没有把文件或功能强行归给最后提交者。

## 跨作者 PR 与重复关系

下面列出的“提交作者数”来自 PR head 相对于 merge-base 的提交范围。它说明 PR 分支包含哪些作者，但不能自动证明每位作者都参与了 PR 标题所述的全部工作，因为分支可能包含祖先提交。

| PR | 发起人 | 提交作者构成 | 审计解释 |
|---|---|---|---|
| #2 | CSR | Grace 2、CSR 1 | 分支包含 Grace 既有提交，不能把全部 diff 归给 CSR |
| #4 | Grace | Grace 1、ZHY 1 | 路线 Agent PR 范围含 ZHY 提交 |
| #7 | Grace | Grace 8、ZHY 1 | 多 Agent 全栈 PR 含一项 ZHY 提交 |
| #33 | CSR | CSR 10、ZHY 2、Grace 4 | StoryWalk V4 视觉整合包含三人分支历史 |
| #39 | Grace | ZHY 5、Grace 1 | 路环入口与导览流程是明显的跨成员交付 |
| #44 | CSR | CSR 4、Grace 8 | 氹仔未来信图片功能建立在 Grace 分支工作上 |
| #48 | CSR | CSR 2、ZHY 1 | 本地化修复包含 ZHY 提交 |
| #54 | Grace | ZHY 8、CSR 12、Grace 1 | `master` 同步到 `Grace`，整体排除新增贡献计分 |

PR #35 的目标分支是 `hongyizhang`，不是 `master`；随后 #37 补齐文件，#39 再将相关功能送入 `master`。因此这三者只在 commit 和当前代码层面计算一次，不把 PR diff 机械相加。

## 文档量化细节

### Report ver2.1

| 项目 | 全文 | CSR 的附录四 | 占比 |
|---|---:|---:|---:|
| 物理页 | 82 | 约 15 页 | 约 18% |
| 有效文字 | 45,377 字符 | 5,282 字符 | 11.6% |
| 图示 | 56 | 14 | 25.0% |
| 表格 | 31 | 7 | 22.6% |

附录四包含需求理解、偏好引导、路线调整、文化讲解、Reviewer、照片识别、明信片场景和故事游共 8 组系统输入输出证据。由于这一部分的图表密度高于正文，没有只按字数给 CSR 11.6%，而是综合文字、图示和表格后取约 16%。因此该报告采用 Grace 84%、CSR 16%。

### Report ver4.5

全文共 22 个物理页面、16,915 个有效字符。CSR 完成的“AI 伦理与政策考量”有 1,755 个有效字符，占 10.4%，未包含额外图表。因此采用 Grace 90%、CSR 10%。

### StoryWalk 说明文档

全文共 63 个物理页面、约 15,136 个有效字符和 99 个图示，主体是逐界面、逐流程的操作说明。文件本身不能可靠恢复两人的真实撰写工时，因此不尝试用 `lastModifiedBy` 等元数据替代团队事实，直接采用团队确认的 CSR 60%、ZHY 40%。

### 答辩 PPT

PPT 共 10 页、约 3,544 个有效字符和 33 个图片引用。CSR 制作的第 6 页有约 181 个有效字符和 4 个图片引用，分别占 5.1% 和 12.1%。考虑到幻灯片的设计工作不能只按字数计算，按页采用 Grace 90%、CSR 10%。现场答辩另设类别，没有与 PPT 制作重复计算。

## 总奖金公式

最终平衡方案为：

`总贡献 = 代码 55% + 两份报告 18% + 说明文档 8% + PPT 7% + 现场答辩/项目管理/会议协调 12%`

逐人计算：

- Grace：`63.6%×55% + 86%×18% + 0%×8% + 90%×7% + 100%×12% = 约 68.7%`
- CSR：`23.2%×55% + 14%×18% + 60%×8% + 10%×7% + 0%×12% = 约 20.8%`
- ZHY：`13.3%×55% + 0%×18% + 40%×8% + 0%×7% + 0%×12% = 约 10.5%`

为了便于实际发放且合计为 100%，取整为 69%、21%、10%。

## 权重敏感性分析

为了避免某一套权重人为决定结果，又计算了三种方案：

| 方案 | 代码 | 报告 | 说明文档 | PPT | 管理与答辩 | Grace | CSR | ZHY |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 技术优先 | 65% | 15% | 7% | 5% | 8% | 66.7% | 21.9% | 11.4% |
| 平衡方案 | 55% | 18% | 8% | 7% | 12% | 约 68.7% | 20.8% | 10.5% |
| 组织交付优先 | 45% | 20% | 10% | 10% | 15% | 69.8% | 20.2% | 10.0% |

三种方案的排序完全一致，合理区间约为 Grace 67%–70%、CSR 20%–22%、ZHY 10%–11%。因此 69%、21%、10% 并不依赖某一个极端权重设定。

## 全部 PR 清单

| PR | 状态 | 发起账号 | 目标分支 ← 来源分支 | 标题 |
|---|---|---|---|---|
| #1 | 已合并 | Grace-xyx | `master` ← `Grace` | 更新checklist |
| #2 | 已合并 | Narrowunknown | `master` ← `chensirui` | 修复可能的死循环 |
| #3 | 已合并 | Narrowunknown | `master` ← `chensirui` | 添加和修订数据 |
| #4 | 已合并 | Grace-xyx | `master` ← `Grace` | feat(route-agent): P1 路线 agent 端到端打通 + QwenPaw harness 骨架 |
| #5 | 已合并 | 20030419zhanghongyi | `master` ← `hongyizhang` | feat(trips): add demo trip check-in and progress APIs |
| #6 | 已合并 | 20030419zhanghongyi | `master` ← `hongyizhang` | feat(profile): add trip history favorites and feedback APIs |
| #7 | 已合并 | Grace-xyx | `master` ← `Grace` | feat(agents): 核心能力全栈落地 — route/intent/reviewer/photo/guide + pgvector RAG |
| #8 | 已合并 | 20030419zhanghongyi | `master` ← `hongyizhang` | feat(db): add PostgreSQL PostGIS SQLAlchemy and Alembic foundation |
| #9 | 已合并 | 20030419zhanghongyi | `master` ← `hongyizhang` | fix(api): restore trips and profile router registration |
| #10 | 已合并 | 20030419zhanghongyi | `master` ← `hongyizhang` | feat: complete backend database infrastructure and API delivery |
| #11 | 已合并 | Narrowunknown | `master` ← `chensirui` | feat(agents): improve photo recognition and add intent-based orchestration |
| #12 | 已合并 | Grace-xyx | `master` ← `Grace` | feat: 后端全容器化 + F1 用户落库/极简 JWT 登录 |
| #13 | 已合并 | Grace-xyx | `master` ← `codex/backend-guide-completion` | feat(guide): complete location trigger, walking paths, TTS, and guardrails |
| #14 | 已合并 | Grace-xyx | `master` ← `codex/backend-guide-completion` | feat(storywalk): ship guide/walk/profile MVP with preset narration |
| #15 | 已合并 | Grace-xyx | `master` ← `Grace` | feat(postcards): add postcard model and transit-aware walk paths |
| #16 | 已合并 | 20030419zhanghongyi | `master` ← `hongyizhang` | feat(frontend): 接入用户偏好与行程流程 |
| #17 | 已合并 | Narrowunknown | `master` ← `chensirui` | feat(frontend): add real walking map and safer route adjustment |
| #18 | 已合并 | Grace-xyx | `master` ← `Grace` | feat(routes): 口岸锚定多日游、明信片与讲解联网检索 |
| #19 | 已合并 | Narrowunknown | `master` ← `chensirui` | test(backend): isolate pytest runtime state, update route agents |
| #20 | 已合并 | Grace-xyx | `master` ← `Grace` | feat: 主题日路线、导览伦理与明信片场景参考图管线 |
| #21 | 已合并 | Narrowunknown | `master` ← `chensirui` | feat(postcards): add Qwen-Image generation and photo styling |
| #22 | 已合并 | 20030419zhanghongyi | `master` ← `hongyizhang` | 新增《莲城双图》剧情路线后端与文字内容 |
| #23 | 已合并 | Narrowunknown | `master` ← `chensirui` | 补充README内容及修复qwenpaw_image测试中的图片路径问题 |
| #24 | 已合并 | Grace-xyx | `master` ← `Grace` | feat(agents): 新增偏好多轮引导 Agent (pref-guide) |
| #25 | 关闭未合并 | 20030419zhanghongyi | `master` ← `hongyizhang` | 更新《莲城双图》修订版剧情后端 |
| #26 | 已合并 | Grace-xyx | `master` ← `Grace` | feat: StoryWalk P0 前端实现 + 莲城双图后端 v3 升级 |
| #27 | 已合并 | Grace-xyx | `master` ← `Grace` | feat(cutscene): v2 cinematic cutscene |
| #28 | 已合并 | Narrowunknown | `master` ← `chensirui` | chore: update README, .env.example and pyproject |
| #29 | 已合并 | 20030419zhanghongyi | `master` ← `hongyizhang` | 完善《莲城双图》V4 故事后端、协作规范与全链路验证 |
| #30 | 已合并 | Grace-xyx | `master` ← `Grace` | feat(setup): add macOS QwenPaw configuration |
| #31 | 已合并 | Narrowunknown | `master` ← `chensirui` | feat(story-v4): implement Lotus City Double Map frontend |
| #32 | 已合并 | 20030419zhanghongyi | `master` ← `hongyizhang` | feat(story): add complete V4 visual asset set |
| #33 | 已合并 | Narrowunknown | `master` ← `chensirui` | feat(story-v4): integrate visual asset library |
| #34 | 已合并 | Grace-xyx | `master` ← `Grace` | feat(明信片): 接入 editorial 图片 Skill 并修复游客行程 500 |
| #35 | 已合并 | 20030419zhanghongyi | `hongyizhang` ← `feat/coloane-after-tide` | Add Coloane after tide story mode |
| #36 | 关闭未合并 | 20030419zhanghongyi | `master` ← `hongyizhang` | Hongyizhang |
| #37 | 已合并 | 20030419zhanghongyi | `master` ← `fix/coloane-master-missing-files` | Add missing Coloane story files to master |
| #38 | 已合并 | Grace-xyx | `master` ← `Grace` | feat(storywalk): add live travel guidance and agent memory |
| #39 | 已合并 | Grace-xyx | `master` ← `feat/coloane-after-tide` | feat(story): complete Coloane entry and guidance flow |
| #40 | 已合并 | Grace-xyx | `master` ← `Grace` | feat: enhance travel guidance and enable Coloane story |
| #41 | 已合并 | Narrowunknown | `master` ← `chensirui` | feat(story): add the Taipa Letters story route |
| #42 | 已合并 | Grace-xyx | `master` ← `Grace` | fix(guide): keep POI answers relevant |
| #43 | 已合并 | Grace-xyx | `master` ← `Grace` | Grace |
| #44 | 已合并 | Narrowunknown | `master` ← `chensirui` | feat(story): generate optional Taipa future-letter artwork |
| #45 | 已合并 | Grace-xyx | `master` ← `Grace` | feat: complete multilingual StoryWalk journeys |
| #46 | 已合并 | Grace-xyx | `master` ← `Grace` | feat: persist guide photos and refine travel memories |
| #47 | 已合并 | Grace-xyx | `master` ← `Grace` | feat(travel): add live operations and fixed POI context |
| #48 | 已合并 | Narrowunknown | `master` ← `chensirui` | fix(story): localize puzzle feedback and image labels |
| #49 | 已合并 | 20030419zhanghongyi | `master` ← `hongyizhang` | 完善故事三《潮退之后》的流程与多语言体验 |
| #50 | 已合并 | Grace-xyx | `master` ← `Grace` | feat: persist traveler content and browser sessions |
| #51 | 已合并 | Grace-xyx | `master` ← `Grace` | feat(auth): add account recovery and demo readiness fixes |
| #52 | 已合并 | Narrowunknown | `master` ← `chensirui` | feat: add Windows QwenPaw setup and fix StoryWalk localization |
| #53 | 已合并 | Narrowunknown | `master` ← `chensirui` | fix(story): restore Guide-backed A Lin and QwenPaw image setup |
| #54 | 已合并 | Grace-xyx | `Grace` ← `master` | chore: sync Grace with latest master |

## 使用边界

1. `git blame` 反映当前仍保留的代码，不完全等于投入时间；被重构删除的工作由 churn 和 commit 指标补偿。
2. 行数不能直接代表难度，所以最终模型没有只按行数分配。
3. 文档作者归属采用团队提供的信息；文件元数据不能可靠证明实际撰写者。
4. 现场答辩、项目管理和会议协调的归属来自团队提供的信息，而不是 Git 记录；奖金确认前建议由三人共同确认这一事实。
5. 尚未计入的线下工作，例如现场调研、素材拍摄或外部沟通，如果工作量较大，应提供记录后再调整 1–2 个百分点。
