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

本节保留 Windows PowerShell 指引，同时提供原生 macOS/zsh 命令。macOS 用户可在
完成“安装并初始化 QwenPaw”后运行
`bash scripts/configure_qwenpaw_macos.sh`，一次完成项目 Skills、Agents、伦理基线
和 Qwen-Image Plugin 的配置；不需要安装 PowerShell 7。

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

以下是新机器上的一次性配置。保持终端 A 中的 `qwenpaw app` 运行，另开一个
终端，`cd` 到仓库根目录并激活同一个 QwenPaw 虚拟环境。先完成 `qwenpaw init`
和 `qwenpaw models config`，再执行本节命令。
以下 PowerShell 片段统一使用一个地址变量；默认安装使用 `8088`。若自行修改
端口，请同步修改这里、项目 `.env`，以及 `compose.yml` 中的
`host.docker.internal:8088`：

```powershell
$qwenpawBaseUrl = "http://127.0.0.1:8088"
Invoke-RestMethod "$qwenpawBaseUrl/api/version"
```

以下代码块默认在同一个 PowerShell 会话中依次执行；若打开新终端，请先重新设置
`$qwenpawBaseUrl`。

#### macOS/zsh 一次性配置

macOS 用户不需要逐段转换下面的 PowerShell。保持 `qwenpaw app` 运行后，在新的
zsh 终端执行：

```zsh
cd /path/to/qwenpaw-ai-agent-competition
source .venv/bin/activate
bash scripts/configure_qwenpaw_macos.sh
```

脚本会校验并导入本地 Skills，创建缺失的项目 Agents（已有 Agent 不会被删除），
注入统一伦理基线，安装 Qwen-Image Plugin，并从根目录 `.env` 读取部署者自行提供的
`QWEN_IMAGE_API_KEY` 与北京原生 `QWEN_IMAGE_ENDPOINT`，同步到 QwenPaw 图片工具。
仓库与赛委会环境不会提供图像生成 Key；相关用量、额度与费用由部署账号承担。
脚本不会在终端显示密钥；无 Key 时会保留插件已安装、工具未启用的状态。可用
`QWENPAW_BASE_URL=http://127.0.0.1:8088 bash scripts/configure_qwenpaw_macos.sh`
覆盖默认地址。

以后只修改图片密钥或端点时，无需重新导入全部 Agent 和 Skill；保持 QwenPaw 运行并执行：

```zsh
bash scripts/sync_qwen_image_config.sh
```

### 1. 导入全部本地 Skills

本项目包含 8 个业务 Skill 和 4 个伦理 Skill：

| Skill | 用途 | 挂载到 |
|---|---|---|
| `route-adjust` | 自然语言路线微调 | `route` |
| `requirement-understand` | 游览需求结构化 | `intent` |
| `preference-guide` | 多轮补充路线偏好 | `pref-guide` |
| `macau-guide` | 有据文化讲解 | `guide` |
| `photo-recognize` | 图片描述与 POI 判断 | `photo` |
| `postcard-scene` | SVG 明信片场景约束 | `scene` |
| `qwen-image-postcard` | 调用 Qwen-Image 的真实旅行回忆图 | `scene` |
| `photo-abstract-editorial` | 用户授权照片 → 原片保留 + 抽象记忆面板编辑图 | `scene` |
| `fairness-gate` | 偏好公平性检查 | `intent` |
| `source-attribution` | 来源和置信度标注 | `guide`、`photo` |
| `anti-sycophancy` | 避免迎合与无依据断言 | `guide` |
| `content-safety-review` | 独立内容安全裁定 | `reviewer` |

PowerShell 导入命令：

```powershell
$agentResponse = Invoke-RestMethod "$qwenpawBaseUrl/api/agents"
$defaultAgent = @($agentResponse.agents | Where-Object { $_.id -eq "default" })[0]
if ($null -eq $defaultAgent) { throw "找不到 default Agent" }
$qwenpawWorkingDir = Split-Path `
  (Split-Path $defaultAgent.workspace_dir -Parent) -Parent
$pool = Join-Path $qwenpawWorkingDir "skill_pool"
New-Item -ItemType Directory -Force $pool | Out-Null
$ethicsSkillNames = @(
  "fairness-gate",
  "source-attribution",
  "anti-sycophancy",
  "content-safety-review"
)
$skillSources = @(
  "skills\route-adjust",
  "skills\requirement-understand",
  "skills\preference-guide",
  "skills\macau-guide",
  "skills\photo-recognize",
  "skills\postcard-scene",
  "skills\qwen-image-postcard",
  "skills\photo-abstract-editorial",
  "ethics\qwenpaw-skills\fairness-gate",
  "ethics\qwenpaw-skills\source-attribution",
  "ethics\qwenpaw-skills\anti-sycophancy",
  "ethics\qwenpaw-skills\content-safety-review"
)
foreach ($source in $skillSources) {
  $skillName = Split-Path $source -Leaf
  $destination = Join-Path $pool $skillName
  New-Item -ItemType Directory -Force $destination | Out-Null
  Copy-Item (Join-Path $source "SKILL.md") `
    (Join-Path $destination "SKILL.md") -Force
  if ($skillName -in $ethicsSkillNames) {
    Remove-Item (Join-Path $destination "prompt.md") `
      -Force -ErrorAction SilentlyContinue
  }
  & qwenpaw skills test $destination
  if ($LASTEXITCODE -ne 0) { throw "Skill 检查失败：$skillName" }
}
Invoke-RestMethod -Method Post "$qwenpawBaseUrl/api/skills/pool/refresh"
```

QwenPaw 不会仅因文件出现在 `skill_pool` 就自动登记；最后的 `pool/refresh` 是
必需步骤。可用 `qwenpaw skills list` 检查，更多原理和故障说明见
[`skills/README.md`](skills/README.md) 与
[QwenPaw Skills 文档](https://qwenpaw.agentscope.io/docs/skills/)。

### 2. 创建全部 Agents 并挂载 Skills

先用 `qwenpaw models list` 确认默认模型已配置。下面直接从正在运行的 QwenPaw
读取活动 Provider ID 和 Model ID，避免复制文档中的过期模型名。`photo` 和 `scene`
必须使用支持视觉的多模态模型；若默认模型不支持图片，请先在 QwenPaw 中换成
支持图片的模型。`qwenpaw init` 创建的 `default` Agent 请保留；下面另外创建的
7 个专用 Agent ID 是后端契约的一部分，不能随意改名。

```powershell
function Invoke-QwenPawChecked {
  & qwenpaw @args
  if ($LASTEXITCODE -ne 0) {
    throw "QwenPaw 命令失败：qwenpaw $($args -join ' ')"
  }
}

$activeModel = Invoke-RestMethod "$qwenpawBaseUrl/api/models/active"
$provider = $activeModel.active_llm.provider_id
$model = $activeModel.active_llm.model
if (-not $provider -or -not $model) { throw "QwenPaw 默认模型尚未配置" }
Write-Host "Agents 将使用：$provider / $model"

Invoke-QwenPawChecked agents create --agent-id route --name "路线微调" --language zh `
  --provider-id $provider --model-id $model --skill route-adjust
Invoke-QwenPawChecked agents create --agent-id intent --name "需求理解" --language zh `
  --provider-id $provider --model-id $model --skill requirement-understand `
  --skill fairness-gate
Invoke-QwenPawChecked agents create --agent-id pref-guide --name "偏好多轮引导" `
  --language zh --provider-id $provider --model-id $model --skill preference-guide
Invoke-QwenPawChecked agents create --agent-id guide --name "文化讲解" --language zh `
  --provider-id $provider --model-id $model --skill macau-guide `
  --skill source-attribution --skill anti-sycophancy
Invoke-QwenPawChecked agents create --agent-id photo --name "拍照识别" --language zh `
  --provider-id $provider --model-id $model --skill photo-recognize `
  --skill source-attribution
Invoke-QwenPawChecked agents create --agent-id scene --name "明信片场景" --language zh `
  --provider-id $provider --model-id $model --skill postcard-scene `
  --skill qwen-image-postcard --skill photo-abstract-editorial
Invoke-QwenPawChecked agents create --agent-id reviewer --name "独立审核" --language zh `
  --provider-id $provider --model-id $model --skill content-safety-review

Invoke-QwenPawChecked agents list
```

这些命令用于首次配置；若 Agent 已存在，不要删除重建，可运行
`qwenpaw skills config --agent-id <agent-id>` 交互式修正技能。`photo` 还必须保留
内置 `view_image` 工具为启用状态。

`intent` 用于把一段较完整的需求一次性解析为 Preference；`pref-guide` 用于信息
不足时进行多轮引导，每轮只追问一个缺失项，信息足够后再输出 Preference。后端
固定调用 `pref-guide`，因此不要把 Agent ID 改成下划线形式或其他名称。该 Agent
使用普通文本模型即可，不需要 `view_image`、多模态模型或 Qwen-Image Plugin。

### 3. 向所有项目 Agents 注入统一伦理基线

所有项目 Agent（包括 `qwenpaw init` 创建的 `default`）必须共享同一伦理提示词。
统一内容严格取自 [`ethics/prompts/_ethics_base.md`](ethics/prompts/_ethics_base.md)
第 9–42 行，并在首次执行时覆盖这 8 个项目工作区默认 `AGENTS.md` 的第 14–44 行。

下面的脚本会加入注释标记，因此可以安全重跑：首次按上述行号替换，以后只更新
标记区。它通过 QwenPaw API 取得工作区实际路径，只处理本项目的 `default` 和
7 个专用 Agent，不会修改 QwenPaw 内置 QA Agent 或用户的其他 Agent。请在所有
专用 Agent 创建完成后执行。内置 QA Agent 不属于本项目运行契约，并有自己的
专用问答指令，因此不覆盖它的 `AGENTS.md`。

```powershell
$ethicsPath = Join-Path (Get-Location) "ethics\prompts\_ethics_base.md"
$ethicsLines = @(Get-Content -LiteralPath $ethicsPath -Encoding UTF8)
if ($ethicsLines.Count -lt 42) { throw "_ethics_base.md 少于 42 行" }

$startMarker = "<!-- MACAU_ETHICS_BASE_START -->"
$endMarker = "<!-- MACAU_ETHICS_BASE_END -->"
$ethicsBlock = @($startMarker) + @($ethicsLines[8..41]) + @($endMarker)
$projectAgentIds = @(
  "default", "route", "intent", "pref-guide", "guide", "photo", "scene", "reviewer"
)
$agentResponse = Invoke-RestMethod "$qwenpawBaseUrl/api/agents"
$projectAgents = @($agentResponse.agents | Where-Object { $_.id -in $projectAgentIds })
$missingAgentIds = @($projectAgentIds | Where-Object { $_ -notin $projectAgents.id })
if ($missingAgentIds.Count -gt 0) {
  throw "缺少项目 Agent：$($missingAgentIds -join ', ')"
}
$agentFiles = @($projectAgents | ForEach-Object {
  Join-Path $_.workspace_dir "AGENTS.md"
})
foreach ($agentFile in $agentFiles) {
  if (-not (Test-Path -LiteralPath $agentFile)) { throw "文件不存在：$agentFile" }
}

foreach ($agentFile in $agentFiles) {
  $lines = @(Get-Content -LiteralPath $agentFile -Encoding UTF8)
  $markedStart = [Array]::IndexOf($lines, $startMarker)
  $markedEnd = [Array]::IndexOf($lines, $endMarker)

  if ($markedStart -ge 0 -and $markedEnd -gt $markedStart) {
    $before = if ($markedStart -gt 0) { @($lines[0..($markedStart - 1)]) } else { @() }
    $after = if ($markedEnd + 1 -lt $lines.Count) {
      @($lines[($markedEnd + 1)..($lines.Count - 1)])
    } else { @() }
  } else {
    if ($lines.Count -lt 44) { throw "$agentFile 少于 44 行" }
    $before = @($lines[0..12])
    $after = if ($lines.Count -gt 44) { @($lines[44..($lines.Count - 1)]) } else { @() }
  }

  $updated = @($before) + @($ethicsBlock) + @($after)
  Set-Content -LiteralPath $agentFile -Value $updated -Encoding UTF8
  Write-Host "伦理基线已更新：$agentFile"
}
```

只使用 `ethics/qwenpaw-skills/<skill>/SKILL.md` 作为伦理 Skill 内容。该目录内
的独立 `prompt.md` 不复制、不挂载，也不要再写入 `AGENTS.md` 或 Agent system
prompt；其规则与 `SKILL.md` 重复，重复注入会增加提示词冲突和上下文噪声。

### 4. 安装 Qwen-Image Tool Plugin

仓库已经包含与 AgentScope1.0/QwenPaw1.1.12 post3 兼容的官方插件副本：

```powershell
& qwenpaw plugin validate .\backend\app\tools\qwen-image
if ($LASTEXITCODE -ne 0) { throw "Qwen-Image Plugin 校验失败" }
& qwenpaw plugin install .\backend\app\tools\qwen-image --force
if ($LASTEXITCODE -ne 0) { throw "Qwen-Image Plugin 安装失败" }
& qwenpaw plugin list
if ($LASTEXITCODE -ne 0) { throw "无法读取 Plugin 列表" }
```

QwenPaw 运行时安装会热加载；未运行时会离线安装，并在下次
`qwenpaw app` 时加载。插件提供 `generate_image_qwen` 和
`edit_image_qwen`，只需给 `scene` Agent 启用。

下面的 PowerShell 从项目 `.env` 读取 Key，不把明文写进命令历史，并通过本机
QwenPaw API 配置、按需启用两个工具：

```powershell
$keyLine = Get-Content .env |
  Where-Object { $_ -match '^DASHSCOPE_API_KEY=' } |
  Select-Object -First 1
$dashscopeKey = (($keyLine -split '=', 2)[1]).Trim().Trim('"').Trim("'")
if (-not $dashscopeKey) { throw "DASHSCOPE_API_KEY 未配置" }

$headers = @{ "X-Agent-Id" = "scene" }
$toolNames = @("generate_image_qwen", "edit_image_qwen")
$toolConfig = @{
  config = @{
    api_key = $dashscopeKey
    endpoint = "https://dashscope.aliyuncs.com/api/v1"
    model = "qwen-image-2.0-pro"
    timeout = 180
  }
} | ConvertTo-Json -Depth 4

foreach ($toolName in $toolNames) {
  Invoke-RestMethod -Method Post `
    -Uri "$qwenpawBaseUrl/api/tools/$toolName/config" `
    -Headers $headers -ContentType "application/json" `
    -Body $toolConfig | Out-Null
}

$allTools = Invoke-RestMethod -Method Get `
  -Uri "$qwenpawBaseUrl/api/tools" -Headers $headers
foreach ($toolName in $toolNames) {
  $current = $null
  foreach ($candidate in $allTools) {
    if ($candidate.name -eq $toolName) { $current = $candidate }
  }
  if ($null -eq $current) { throw "未找到工具：$toolName" }
  if (-not $current.enabled) {
    Invoke-RestMethod -Method Patch `
      -Uri "$qwenpawBaseUrl/api/tools/$toolName/toggle" `
      -Headers $headers | Out-Null
  }
}
```

国际版 DashScope Key 应把 endpoint 改为
`https://dashscope-intl.aliyuncs.com/api/v1`，Key 与 endpoint 必须同区域。
若启用了 QwenPaw Web 鉴权，还需给上述请求补充相应 Authorization/Cookie。

用户提供授权照片时，使用 `photo-abstract-editorial`：通过 `edit_image_qwen` 保留
原片并提炼抽象记忆面板。没有个人照片时，`qwen-image-postcard` 可以调用
`generate_image_qwen`；展示结果必须标注为**“AI 场景示意”**。旧版
`postcard-scene` 不得作为图像工具失败时的回退。验收在线链路时应看到插件的
`plugin_call_output` 并取得图片。

### 5. 验证 QwenPaw 配置

下面的脚本可在新的 PowerShell 会话中独立运行。它会调用一次 QwenPaw 的模型
健康检查，并核对全部项目 Agent、Skill、伦理基线和图片工具；不会生成明信片图片。

```powershell
$qwenpawBaseUrl = "http://127.0.0.1:8088"
$projectAgentIds = @(
  "default", "route", "intent", "pref-guide", "guide", "photo", "scene", "reviewer"
)
$expectedSkills = [ordered]@{
  route = @("route-adjust")
  intent = @("requirement-understand", "fairness-gate")
  "pref-guide" = @("preference-guide")
  guide = @("macau-guide", "source-attribution", "anti-sycophancy")
  photo = @("photo-recognize", "source-attribution")
  scene = @("postcard-scene", "qwen-image-postcard", "photo-abstract-editorial")
  reviewer = @("content-safety-review")
}

& qwenpaw doctor
if ($LASTEXITCODE -ne 0) { throw "QwenPaw 健康检查失败" }
$agentList = @(& qwenpaw agents list 2>&1)
if ($LASTEXITCODE -ne 0) { throw "无法读取 Agent 列表" }
$pluginInfo = @(& qwenpaw plugin info qwen-image-tool 2>&1)
if ($LASTEXITCODE -ne 0) { throw "Qwen-Image Plugin 未安装" }

foreach ($entry in $expectedSkills.GetEnumerator()) {
  $skillOutput = @(& qwenpaw skills list --agent-id $entry.Key 2>&1)
  if ($LASTEXITCODE -ne 0) { throw "无法读取 $($entry.Key) 的 Skills" }
  $skillText = $skillOutput -join "`n"
  foreach ($skillName in $entry.Value) {
    if ($skillText -notmatch [regex]::Escape($skillName)) {
      throw "$($entry.Key) 缺少 Skill：$skillName"
    }
  }
  Write-Host "Skill 映射正确：$($entry.Key)"
}

$agentResponse = Invoke-RestMethod "$qwenpawBaseUrl/api/agents"
$projectAgents = @($agentResponse.agents | Where-Object { $_.id -in $projectAgentIds })
$missingAgentIds = @($projectAgentIds | Where-Object { $_ -notin $projectAgents.id })
if ($missingAgentIds.Count -gt 0) {
  throw "缺少项目 Agent：$($missingAgentIds -join ', ')"
}

$ethicsPath = Join-Path (Get-Location) "ethics\prompts\_ethics_base.md"
$ethicsLines = @(Get-Content -LiteralPath $ethicsPath -Encoding UTF8)
if ($ethicsLines.Count -lt 42) { throw "_ethics_base.md 少于 42 行" }
foreach ($agent in $projectAgents) {
  $agentFile = Join-Path $agent.workspace_dir "AGENTS.md"
  $lines = @(Get-Content -LiteralPath $agentFile -Encoding UTF8)
  $start = [Array]::IndexOf($lines, "<!-- MACAU_ETHICS_BASE_START -->")
  $end = [Array]::IndexOf($lines, "<!-- MACAU_ETHICS_BASE_END -->")
  if ($start -lt 0 -or $end -le $start) {
    throw "伦理基线未注入：$($agent.id)"
  }
  $actual = @($lines[($start + 1)..($end - 1)])
  if (($actual -join "`n") -cne ($ethicsLines[8..41] -join "`n")) {
    throw "伦理基线内容不一致：$($agent.id)"
  }
}

$ethicsSkillNames = @(
  "fairness-gate",
  "source-attribution",
  "anti-sycophancy",
  "content-safety-review"
)
$defaultAgent = @($projectAgents | Where-Object { $_.id -eq "default" })[0]
$qwenpawWorkingDir = Split-Path `
  (Split-Path $defaultAgent.workspace_dir -Parent) -Parent
$redundantPromptFiles = @()
foreach ($skillName in $ethicsSkillNames) {
  $poolPrompt = Join-Path $qwenpawWorkingDir "skill_pool\$skillName\prompt.md"
  if (Test-Path -LiteralPath $poolPrompt) { $redundantPromptFiles += $poolPrompt }
}
foreach ($agent in $projectAgents) {
  $redundantPromptFiles += @(Get-ChildItem -LiteralPath $agent.workspace_dir `
    -Recurse -File -Filter "prompt.md" -ErrorAction SilentlyContinue |
    Where-Object { $_.Directory.Name -in $ethicsSkillNames } |
    ForEach-Object { $_.FullName })
}
if ($redundantPromptFiles.Count -gt 0) {
  throw "发现不应复制的伦理 prompt.md：$($redundantPromptFiles -join ', ')"
}

function Get-AgentTools([string]$agentId) {
  $headers = @{ "X-Agent-Id" = $agentId }
  return @(Invoke-RestMethod -Uri "$qwenpawBaseUrl/api/tools" -Headers $headers)
}
$photoTools = @(Get-AgentTools "photo")
$viewImage = @($photoTools | Where-Object { $_.name -eq "view_image" })[0]
if ($null -eq $viewImage -or -not $viewImage.enabled) {
  throw "photo Agent 的 view_image 未启用"
}
$sceneTools = @(Get-AgentTools "scene")
foreach ($toolName in @("generate_image_qwen", "edit_image_qwen")) {
  $tool = @($sceneTools | Where-Object { $_.name -eq $toolName })[0]
  if ($null -eq $tool -or -not $tool.enabled) {
    throw "scene Agent 的 $toolName 未启用"
  }
  foreach ($field in @("api_key", "model", "endpoint")) {
    if (-not $tool.config_values.$field) {
      throw "$toolName 缺少配置：$field"
    }
  }
}

$version = Invoke-RestMethod "$qwenpawBaseUrl/api/version"
Write-Host "QwenPaw 配置验证通过：$($version.version)"
```

确认无误后，把 `.env` 中六个 Agent 开关改为 `true`，并保持
`POSTCARD_AI_IMAGE_ENABLED=true`，再执行：

```powershell
docker compose up -d --build
```

QwenPaw 详细分工、结构化输出约束和回退机制见
[`skills/README.md`](skills/README.md)，明信片插件细节见
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
