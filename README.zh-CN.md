# qwenpaw-ai-agent-competition

[English](README.md) | **简体中文**

![Python 3.11–3.13](https://img.shields.io/badge/Python-3.11%E2%80%933.13-3776AB?logo=python&logoColor=white)
![Node.js 18+](https://img.shields.io/badge/Node.js-18%2B-339933?logo=nodedotjs&logoColor=white)
![React 18](https://img.shields.io/badge/React-18-61DAFB?logo=react&logoColor=black)
![FastAPI](https://img.shields.io/badge/FastAPI-backend-009688?logo=fastapi&logoColor=white)
[![GitHub stars](https://img.shields.io/github/stars/20030419zhanghongyi/qwenpaw-ai-agent-competition)](https://github.com/20030419zhanghongyi/qwenpaw-ai-agent-competition/stargazers)
[![GitHub forks](https://img.shields.io/github/forks/20030419zhanghongyi/qwenpaw-ai-agent-competition)](https://github.com/20030419zhanghongyi/qwenpaw-ai-agent-competition/forks)
[![Last commit on master](https://img.shields.io/github/last-commit/20030419zhanghongyi/qwenpaw-ai-agent-competition/master)](https://github.com/20030419zhanghongyi/qwenpaw-ai-agent-competition/commits/master)
[![Repository size](https://img.shields.io/github/repo-size/20030419zhanghongyi/qwenpaw-ai-agent-competition)](https://github.com/20030419zhanghongyi/qwenpaw-ai-agent-competition)

Team project repository for the "千模百炼 AI 开发者学生竞赛".

“澳迹同行 · Macau StoryWalk”是一套面向澳门旅行者的全栈 AI 导览应用：React
前端负责路线、地图、讲解和明信片交互，FastAPI 后端负责编排业务与安全降级，
QwenPaw 负责多轮偏好引导、需求理解、路线调整、文化讲解、拍照识别、内容审核
和图片生成。

## Quick Start（新手快速开始）

Windows 用户初始化后可运行 `pwsh -NoProfile -File scripts/configure_qwenpaw_windows.ps1`，
拉取 Skill 更新后加 `-UpdateExistingSkills`。本节同时提供原生 macOS/zsh 命令。macOS 用户可在
完成“安装并初始化 QwenPaw”后运行
`bash scripts/configure_qwenpaw_macos.sh`，一次完成项目 Skills、Agents、伦理基线、
Qwen-Image Plugin 和 Qwen TTS Plugin 的配置；不需要安装 PowerShell 7。

### 1. 安装基础工具

请先安装：

- Git；
- Docker Desktop，并确认 `docker compose version` 可用；
- Node.js 18+（推荐当前 LTS）和 npm；
- Python 3.11–3.13，用于运行 QwenPaw。后端若采用 Docker，无需另装后端依赖。

```powershell
git --version
docker compose version
node --version
npm --version
py --version
```

macOS/zsh：

```zsh
git --version
docker compose version
node --version
npm --version
python3 --version
```

### 2. 克隆项目并准备环境变量

```powershell
git clone https://github.com/20030419zhanghongyi/qwenpaw-ai-agent-competition.git
cd qwenpaw-ai-agent-competition
Copy-Item .env.example .env
notepad .env
```

macOS/zsh：

```zsh
git clone https://github.com/20030419zhanghongyi/qwenpaw-ai-agent-competition.git
cd qwenpaw-ai-agent-competition
cp .env.example .env
open -e .env
```

至少填写你自行申请的 `DASHSCOPE_API_KEY`、`AMAP_WEB_SERVICE_KEY`、
`VITE_AMAP_API_KEY` 和 `VITE_AMAP_SECURITY_CODE`。不要提交 `.env`；它已经被
Git 忽略。完整字段说明见下方“配置要求”。

### 3. 安装并初始化 QwenPaw

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip qwenpaw
qwenpaw --version
qwenpaw init
qwenpaw models config
```

macOS/zsh：

```zsh
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip qwenpaw
qwenpaw --version
qwenpaw init
qwenpaw models config
```

`qwenpaw init` 和 `qwenpaw models config` 是交互式命令：选择一个可用的云端
Provider，填写模型 API Key，并指定默认模型。完成后先继续第 4 步启动服务；
首次完整配置还需按照“配置 QwenPaw 运行资产”一次性创建本项目所需的
Agent、Skills 和 Plugin。

### 4. 启动三个进程

终端 A：

```powershell
.\.venv\Scripts\Activate.ps1
qwenpaw app
```

终端 B：

```powershell
docker compose up -d --build
docker compose ps
```

终端 C：

```powershell
cd frontend
npm install
npm run dev
```

打开以下地址：

- 前端：<http://localhost:5173>
- 后端 OpenAPI：<http://localhost:8001/docs>
- QwenPaw Console：<http://127.0.0.1:8088>

```powershell
Invoke-RestMethod http://127.0.0.1:8001/api/v1/health
Invoke-RestMethod http://127.0.0.1:8088/api/version
```

macOS/zsh 的三个终端分别运行：

```zsh
# 终端 A：QwenPaw
source .venv/bin/activate
qwenpaw app
```

```zsh
# 终端 B：后端与数据库
docker compose up -d --build
docker compose ps
```

```zsh
# 终端 C：前端
cd frontend
npm install
npm run dev
```

```zsh
curl -fsS http://127.0.0.1:8001/api/v1/health
curl -fsS http://127.0.0.1:8088/api/version
```

如果暂时没有配置 Agent，路线等接口仍会使用规则版或本地资源降级；完整 AI
能力需要继续完成下方 QwenPaw 配置。

## 配置要求

### 软件与端口

| 项目 | 要求 | 用途 |
|---|---|---|
| Docker Desktop | Compose v2 | PostGIS/pgvector、数据初始化、FastAPI |
| Python | QwenPaw 要求 3.11–3.13；后端源码支持 3.10+ | QwenPaw、本地后端开发与测试 |
| Node.js | 18+，推荐当前 LTS | React + Vite 前端 |
| `8088` | 本机可用 | QwenPaw；容器通过 `host.docker.internal` 访问 |
| `8000` | 本机可用 | FastAPI |
| `5173` | 本机可用 | Vite 开发服务器 |
| `5432` | 本机可用 | Compose 内的 PostGIS/pgvector |

### `.env` 与外部服务

仓库根目录的 `.env.example` 是唯一模板；后端和前端都会从根目录 `.env` 读取
配置。完整功能建议准备以下凭据：

| 变量 | 必需性 | 说明 |
|---|---|---|
| `DASHSCOPE_API_KEY` | 完整 AI 功能必需 | 部署者自行申请的百炼/DashScope Key；用于 TTS、图片和部分后端能力，**不是赛委会提供的 Key** |
| `QWEN_EMBEDDING_API_KEY` | 可选 | RAG embedding 专用；留空时回退到 DashScope Key |
| `AMAP_WEB_SERVICE_KEY` | 路线步行规划必需 | 高德“Web 服务”Key |
| `VITE_AMAP_API_KEY` | 前端地图必需 | 高德“Web 端（JS API）”Key |
| `VITE_AMAP_SECURITY_CODE` | 前端地图必需 | 与 Web 端 Key 配套的安全密钥 |
| `AMAP_API_KEY` / `AMAP_SECURITY_CODE` | 建议同步填写 | 后端兼容字段，与前端 Key/安全密钥保持一致 |
| `QWENPAW_BASE_URL` | 有默认值 | 本机开发使用 `http://127.0.0.1:8088` |

高德 Key 在[高德开放平台](https://lbs.amap.com/)创建；DashScope Key 需要由部署者
在[阿里云百炼控制台](https://bailian.console.aliyun.com/)自行创建。图像生成所需的
DashScope Key **并非赛委会提供**，请使用自己可控的账号与 Key，并自行确认额度、
计费与区域。密钥还需要在
QwenPaw 的模型 Provider 中单独配置，QwenPaw 不会自动读取项目 `.env` 作为
模型 Provider 配置。

Agent 开关默认关闭，完成相应 Agent 配置后再改为 `true`：

```dotenv
ROUTE_AGENT_ENABLED=true
INTENT_AGENT_ENABLED=true
PREFERENCE_GUIDE_AGENT_ENABLED=true
REVIEWER_AGENT_ENABLED=true
GUIDE_AGENT_ENABLED=true
PHOTO_AGENT_ENABLED=true
```

RAG 是可选增强。执行 `docker compose run --rm rag-seed` 完成向量灌库后，设置
`PGVECTOR_ENABLED=true` 并重建后端；否则讲解会回退到关键词检索。生产部署还应
另行配置强随机 `JWT_SECRET`、OSS 凭据和审计盐，详见
[`backend/README.md`](backend/README.md)。

## QwenPaw 下载与初始化

官方支持 pip、安装脚本、Docker 和桌面版。本项目推荐开发者使用 pip：环境可控，
也方便从仓库本地安装 Qwen-Image Plugin。QwenPaw 当前要求 Python 3.11–3.13。

### 推荐：pip 安装

Windows PowerShell：

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip qwenpaw
qwenpaw init
qwenpaw models config
qwenpaw app
```

macOS/Linux：

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip qwenpaw
qwenpaw init
qwenpaw models config
qwenpaw app
```

默认工作目录是 `~/.qwenpaw`，密钥位于独立的
`~/.qwenpaw.secret`；不要把这两个目录复制进仓库或提交。服务默认监听
`127.0.0.1:8088`。

其他安装方式和版本要求以官方页面为准：

- [QwenPaw Quick Start](https://qwenpaw.agentscope.io/docs/quickstart/)
- [QwenPaw 下载页](https://qwenpaw.agentscope.io/downloads)
- [QwenPaw CLI](https://qwenpaw.agentscope.io/docs/cli/)
- [配置与工作目录](https://qwenpaw.agentscope.io/docs/config/)

## 配置 QwenPaw 运行资产

先完成 `qwenpaw init` 与模型配置，并保持本机 `qwenpaw app` 在
`http://127.0.0.1:8088` 运行。配置脚本不会启动或重启后端、前端。

### Windows / PowerShell 7

在仓库根目录执行：

```powershell
# 首次配置：保留已有 workspace Skill 副本。
pwsh -NoProfile -File .\scripts\configure_qwenpaw_windows.ps1

# 拉取仓库更新后：先备份，再更新已有项目 Skill 副本。
pwsh -NoProfile -File .\scripts\configure_qwenpaw_windows.ps1 -UpdateExistingSkills

# 只读本地验证，包括 Skill 内容是否与仓库一致。
pwsh -NoProfile -File .\scripts\configure_qwenpaw_windows.ps1 -VerifyOnly
```

脚本按自身位置推导仓库根目录，因此也支持从其他目录使用脚本绝对路径执行。
它通过正在运行的 QwenPaw HTTP API 配置，不要求激活虚拟环境或安装额外
PowerShell 模块。可用 `-BaseUrl http://127.0.0.1:8088` 或环境变量
`QWENPAW_BASE_URL` 更换本机端口；仅接受回环地址，禁止请求重定向。
启用鉴权的实例可通过 `-Headers` 传入会话中的认证头，不要把密钥写入命令历史。

普通模式会更新技能池，以 `overwrite=false` 挂载缺少的 Skill；发现已有副本与
仓库不同时会告警并保留。**刷新技能池不会自动更新 Agent 已有副本。**
`-UpdateExistingSkills` 才会更新项目 workspace 内属于仓库的 `SKILL.md`，
保留其他文件及无关 Skill。改动已有文件前，会把原文件和配置清单备份到运行时发现
的 QwenPaw 目录下 `backups/storywalk/<时间戳-id>/`，并输出备份位置。
备份可能含凭据，不能提交或分享；失败时脚本会中止，应保留备份供恢复。
重复执行不会重复创建 Agent 或叠加提示词区块。

以上命令取代旧版内联 Windows 配置及验证代码，避免旧代码重新启用合并版
`scene` 配置。

### 当前 Agent 与 Skill 映射

当前共有 **9 个项目 Agent**（`default` 加 8 个专用 Agent），技能池包含
**13 个 Skill**（9 个业务 Skill、4 个伦理 Skill）：

| Agent | 必需 Skill | 职责 |
| --- | --- | --- |
| `default` | 无额外必需 Skill | 统一伦理基线 |
| `route` | `route-adjust` | 路线微调 |
| `intent` | `requirement-understand`、`fairness-gate` | 完整需求理解 |
| `pref-guide` | `preference-guide` | 每轮追问一个缺失偏好 |
| `guide` | `macau-guide`、`source-attribution`、`anti-sycophancy` | 有据讲解及已批准文本的 TTS 渲染 |
| `photo` | `photo-recognize`、`source-attribution` | 拍照识别 |
| `scene` | `gc-minimal-zine-poster` | 无照片生成，仅使用 `generate_image_qwen` |
| `scene-photo` | `qwen-image-postcard`、`photo-abstract-editorial` | 授权且已脱敏照片编辑，仅使用 `edit_image_qwen` |
| `reviewer` | `content-safety-review` | 独立审核 |

`postcard-scene` 保留在技能池作旧版兼容。Windows 脚本会在 `scene` 中禁用
原来的三个场景 Skill，但保留文件；同时禁用 `scene` 的 `edit_image_qwen`
和 `scene-photo` 的 `generate_image_qwen`。Agent ID 是后端契约，不能改名。

脚本从 `/api/models/active`、`/api/agents` 发现模型和 workspace 路径，
保留现有文本模型。对 `photo`、`scene`、`scene-photo` 检查模型声明的视觉
支持，并启用 `view_image`。若原模型没有视觉支持声明，依次尝试现有
`photo` 模型、默认模型，且只采用声明支持视觉的候选；没有可用候选时会在写入
前中止。此检查只验证配置声明，不代表真实模型能力已经实测。

所有 9 个项目 Agent 使用
[`ethics/prompts/_ethics_base.md`](ethics/prompts/_ethics_base.md)
第 9–42 行作为统一伦理基线，写入 `MACAU_ETHICS_BASE` 标记区。
已有标记时仅替换区块；没有标记时追加，不删除原指令。重复或损坏的标记会在写入前
报错。另有独立标记区维护 guide TTS、无照片生成和照片编辑规则。
伦理技能只复制 `SKILL.md`，已有重复 `prompt.md` 会先备份再移除；
内置 QA 和其他非项目 Agent 的指令保持不变。

### Tool Plugin 与凭据

两个平台的脚本均安装仓库中的 `backend/app/tools/qwen-image/` 和
`backend/app/tools/qwen-tts/`。Windows 脚本经指定的本机 API 热加载发生变化的
Plugin，保留无关 Agent 配置，不重装 QwenPaw 或升级 Python 环境。

图片工具使用 `QWEN_IMAGE_API_KEY`、`QWEN_IMAGE_ENDPOINT` 和
`QWEN_IMAGE_MODEL`；guide 的 `synthesize_speech_qwen` 使用
`DASHSCOPE_API_KEY`。非空进程环境变量优先于根目录 `.env`。
图片端点默认 `https://dashscope.aliyuncs.com/api/v1`；
`/compatible-mode/v1` 后缀会转换为原生 `/api/v1`。
密钥与端点必须属于同一区域。本项目不提供密钥，调用额度和费用归部署账号所有。

Windows 脚本不打印密钥，也不创建包含密钥的临时请求文件。
缺少密钥时，会禁用对应工具并保留原有已存凭据；验证结果会明确显示工具禁用。
`-VerifyOnly` 检查本地 Agent、Skill、伦理标记、Plugin、视觉声明及工具配置，
**不会**调用 `qwenpaw doctor`、聊天模型、图片生成或 TTS。

### macOS / zsh

```zsh
cd /path/to/qwenpaw-ai-agent-competition
source .venv/bin/activate
bash scripts/configure_qwenpaw_macos.sh

# 仅修改图片凭据或端点后：
bash scripts/sync_qwen_image_config.sh
```

macOS 脚本会保留已有 workspace Skill 副本，并包含可能检查模型连通性的
`qwenpaw doctor`；它没有 Windows 脚本的更新备份和只读验证模式。

配置完成后，按需在后端 `.env` 中启用 `ROUTE_AGENT_ENABLED`、
`INTENT_AGENT_ENABLED`、`PREFERENCE_GUIDE_AGENT_ENABLED`、
`REVIEWER_AGENT_ENABLED`、`GUIDE_AGENT_ENABLED`、`PHOTO_AGENT_ENABLED`、
`POSTCARD_AI_IMAGE_ENABLED`、`QWENPAW_TTS_ENABLED`。
仅在希望 QwenPaw TTS 失败明确报错而非直连回退时，设置
`QWENPAW_TTS_DIRECT_FALLBACK_ENABLED=false`。
后端环境或代码改变才需重建／重启；单独同步 Skill 不需要重建后端。

结构化输出及降级机制见 [`skills/README.md`](skills/README.md)，
明信片插件细节见
[`backend/README.md`](backend/README.md#明信片-qwen-image-场景图与照片风格化)。

## Project Overview

An AI-powered travel companion for exploring Macau's historic districts. Delivered as a WeChat Mini Program / mobile app, it provides real-time location-based commentary, intelligent route planning, and a gamified experience for tourists.

## Core Features

### 1. Historic District Guide (核心：旧区位置讲解)
- **Location-aware commentary**: When users enter a district, the app generates contextual descriptions (history, landmarks, culture) based on their current location.
- **Audio narration**: All content is delivered with voice commentary.
- **Tour route generation**: Automatically creates optimized walking routes with guided narration.

### 2. Intelligent Route Planning (核心路线规划)
- **Route optimization**: Combines local attractions and trending spots into curated routes.
- **Dynamic adjustments**: Fine-tunes routes based on crowd levels, weather, and seasonality.
- **Map visualization**: Highlights key stops and connections on a map; tapping a stop reveals a timeline with detailed content.
- **Itinerary view**: A memo-style trip plan for easy reference.
- **Gamification**: Check-in points to encourage exploration (similar to Duolingo's engagement model).

#### Input Factors
- Real-time crowd levels (人流)
- Weather conditions (天气)
- Optimal local routes (本身地区的最优化路线)
- User-defined travel type and purpose (用户自定义的旅游类型和目的)
- Macau festivals and cultural events (澳门节庆和文化活动)
- Casino shuttle bus routes (发财车路线)

### 3. User Management (基础功能)
- **Registration & Login**: Collects name, contact (email/phone), origin country, language preference, visit duration, and travel type (solo, family, post-conference leisure).
- **Preference Checklist**: Understands what the user wants to explore in Macau (entertainment, culture, history, etc.).
- **Tutorial**: An onboarding video walkthrough of app features.
- **Personal Center**: Profile and trip management.

### 4. Human-in-the-Loop Curation (人工调度)
- **Offline research data**: Uses the team's existing Xiaohongshu dataset (100 high-engagement notes + 751 comments, 2023–2025) as a static source for POI popularity, pain points, and route priors. No real-time social media monitoring or ongoing crawling in the competition scope.
- **Crowd intelligence**: Monitors crowd levels at ports and attractions when available (via CrowdPass or similar data sources).
- **Manual curation & feedback**: Team-reviewed content updates and in-app user feedback replace live social listening for knowledge iteration.

## Current Stage

前后端核心闭环已可用：用户偏好多轮引导、路线匹配与 Agent 微调、RAG 讲解、
拍照识别、高德地图和步行路径、位置触发、四语 TTS、明信片与 Qwen-Image
生成/风格化均已接入。当前重点是验证全新环境的可复现部署，使用真实高德、
DashScope、OSS 与 QwenPaw 完成端到端 smoke test，并持续补充评测证据。

## Project Goal

Build an interactive AI Agent application prototype based on QwenPaw that delivers a seamless, personalized tour experience for Macau visitors.

## Team Collaboration

- Keep docs updated as decisions become clearer.
- Use `docs/idea-pool.md` to collect and compare project ideas.
- Use `docs/team-roles.md` to clarify ownership and collaboration boundaries.
- Keep frontend, backend, RAG, assets, and scripts work in their dedicated folders.
- Prefer small, frequent commits with clear commit messages.
- Discuss major architecture, product, and competition-track decisions before implementation.
