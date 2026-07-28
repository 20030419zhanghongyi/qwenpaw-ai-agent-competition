# qwenpaw-ai-agent-competition

**English** | [简体中文](README.zh-CN.md)

![Python 3.11–3.13](https://img.shields.io/badge/Python-3.11%E2%80%933.13-3776AB?logo=python&logoColor=white)
![Node.js 18+](https://img.shields.io/badge/Node.js-18%2B-339933?logo=nodedotjs&logoColor=white)
![React 18](https://img.shields.io/badge/React-18-61DAFB?logo=react&logoColor=black)
![FastAPI](https://img.shields.io/badge/FastAPI-backend-009688?logo=fastapi&logoColor=white)
[![GitHub stars](https://img.shields.io/github/stars/20030419zhanghongyi/qwenpaw-ai-agent-competition)](https://github.com/20030419zhanghongyi/qwenpaw-ai-agent-competition/stargazers)
[![GitHub forks](https://img.shields.io/github/forks/20030419zhanghongyi/qwenpaw-ai-agent-competition)](https://github.com/20030419zhanghongyi/qwenpaw-ai-agent-competition/forks)
[![Last commit on master](https://img.shields.io/github/last-commit/20030419zhanghongyi/qwenpaw-ai-agent-competition/master)](https://github.com/20030419zhanghongyi/qwenpaw-ai-agent-competition/commits/master)
[![Repository size](https://img.shields.io/github/repo-size/20030419zhanghongyi/qwenpaw-ai-agent-competition)](https://github.com/20030419zhanghongyi/qwenpaw-ai-agent-competition)

Team project repository for the "千模百炼 AI Developer Student Competition."

**Macau StoryWalk** is a full-stack AI travel guide for visitors to Macau. The
React frontend handles routes, maps, guided commentary, and postcard
interactions; the FastAPI backend orchestrates application logic and safe
fallbacks; and QwenPaw provides multi-turn preference guidance, intent
understanding, route adjustment, cultural commentary, photo recognition,
content review, and image generation.

## Quick Start

Windows PowerShell instructions remain below, alongside native macOS/zsh
commands. After installing and initializing QwenPaw, macOS users can run
`bash scripts/configure_qwenpaw_macos.sh` to configure the project's Skills,
Agents, ethics baseline, and Qwen-Image Plugin without installing PowerShell 7.

### 1. Install the Prerequisites

Install:

- Git;
- Docker Desktop, with `docker compose version` available;
- Node.js 18+ (the current LTS is recommended) and npm;
- Python 3.11–3.13 for QwenPaw. If the backend runs in Docker, you do not need
  to install its dependencies locally.

```powershell
git --version
docker compose version
node --version
npm --version
py --version
```

macOS/zsh:

```zsh
git --version
docker compose version
node --version
npm --version
python3 --version
```

### 2. Clone the Repository and Prepare Environment Variables

```powershell
git clone https://github.com/20030419zhanghongyi/qwenpaw-ai-agent-competition.git
cd qwenpaw-ai-agent-competition
Copy-Item .env.example .env
notepad .env
```

macOS/zsh:

```zsh
git clone https://github.com/20030419zhanghongyi/qwenpaw-ai-agent-competition.git
cd qwenpaw-ai-agent-competition
cp .env.example .env
open -e .env
```

At minimum, set `DASHSCOPE_API_KEY`, `AMAP_WEB_SERVICE_KEY`,
`VITE_AMAP_API_KEY`, and `VITE_AMAP_SECURITY_CODE`. Do not commit `.env`; it is
already ignored by Git. See "Configuration Requirements" below for every
field.

### 3. Install and Initialize QwenPaw

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip qwenpaw
qwenpaw --version
qwenpaw init
qwenpaw models config
```

macOS/zsh:

```zsh
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip qwenpaw
qwenpaw --version
qwenpaw init
qwenpaw models config
```

`qwenpaw init` and `qwenpaw models config` are interactive. Select an available
cloud provider, enter the model API key, and choose the default model. Then
continue to step 4 to start the services. For a complete first-time setup, also
follow "Configure QwenPaw Runtime Assets" to create the Agents, Skills, and
Plugin required by this project.

### 4. Start the Three Processes

Terminal A:

```powershell
.\.venv\Scripts\Activate.ps1
qwenpaw app
```

Terminal B:

```powershell
docker compose up -d --build
docker compose ps
```

Terminal C:

```powershell
cd frontend
npm install
npm run dev
```

Open:

- Frontend: <http://localhost:5173>
- Backend OpenAPI: <http://localhost:8000/docs>
- QwenPaw Console: <http://127.0.0.1:8088>

```powershell
Invoke-RestMethod http://127.0.0.1:8000/api/v1/health
Invoke-RestMethod http://127.0.0.1:8088/api/version
```

Use three macOS/zsh terminals:

```zsh
# Terminal A: QwenPaw
source .venv/bin/activate
qwenpaw app
```

```zsh
# Terminal B: backend and database
docker compose up -d --build
docker compose ps
```

```zsh
# Terminal C: frontend
cd frontend
npm install
npm run dev
```

```zsh
curl -fsS http://127.0.0.1:8000/api/v1/health
curl -fsS http://127.0.0.1:8088/api/version
```

If the Agents have not been configured yet, route and related endpoints still
fall back to rule-based or local-resource implementations. Complete the
QwenPaw setup below to enable all AI features.

## Configuration Requirements

### Software and Ports

| Item | Requirement | Purpose |
|---|---|---|
| Docker Desktop | Compose v2 | PostGIS/pgvector, data initialization, and FastAPI |
| Python | QwenPaw requires 3.11–3.13; backend source supports 3.10+ | QwenPaw, local backend development, and testing |
| Node.js | 18+; current LTS recommended | React + Vite frontend |
| `8088` | Available on the host | QwenPaw; containers access it through `host.docker.internal` |
| `8000` | Available on the host | FastAPI |
| `5173` | Available on the host | Vite development server |
| `5432` | Available on the host | PostGIS/pgvector in Compose |

### `.env` and External Services

The root `.env.example` is the single template. Both the backend and frontend
read configuration from the root `.env`. For complete functionality, prepare
the following credentials:

| Variable | Requirement | Description |
|---|---|---|
| `DASHSCOPE_API_KEY` | Required for complete AI functionality | Model Studio/DashScope; used by TTS, images, and some backend capabilities |
| `QWEN_EMBEDDING_API_KEY` | Optional | Dedicated RAG embedding key; falls back to the DashScope key when empty |
| `AMAP_WEB_SERVICE_KEY` | Required for walking-route planning | AMap "Web Service" key |
| `VITE_AMAP_API_KEY` | Required for the frontend map | AMap "Web (JS API)" key |
| `VITE_AMAP_SECURITY_CODE` | Required for the frontend map | Security code paired with the Web key |
| `AMAP_API_KEY` / `AMAP_SECURITY_CODE` | Recommended | Backend compatibility fields; keep them consistent with the frontend key/security code |
| `QWENPAW_BASE_URL` | Has a default | Use `http://127.0.0.1:8088` for local development |

Create AMap keys on the [AMap Open Platform](https://lbs.amap.com/) and a
DashScope key in the [Alibaba Cloud Model Studio
console](https://bailian.console.aliyun.com/). You must also configure the key
separately in QwenPaw's model provider. QwenPaw does not automatically use the
project `.env` as model-provider configuration.

Agent switches are disabled by default. Set each switch to `true` after its
Agent has been configured:

```dotenv
ROUTE_AGENT_ENABLED=true
INTENT_AGENT_ENABLED=true
PREFERENCE_GUIDE_AGENT_ENABLED=true
REVIEWER_AGENT_ENABLED=true
GUIDE_AGENT_ENABLED=true
PHOTO_AGENT_ENABLED=true
```

RAG is an optional enhancement. Run `docker compose run --rm rag-seed` to seed
the vector database, set `PGVECTOR_ENABLED=true`, and rebuild the backend.
Otherwise, commentary falls back to keyword retrieval. Production deployments
should also configure a strong random `JWT_SECRET`, OSS credentials, and an
audit salt; see [`backend/README.md`](backend/README.md).

## Download and Initialize QwenPaw

QwenPaw officially supports pip, an installation script, Docker, and a desktop
application. This project recommends pip for developers because it gives you a
controlled environment and makes it easy to install the Qwen-Image Plugin from
the repository. QwenPaw currently requires Python 3.11–3.13.

### Recommended: Install with pip

Windows PowerShell:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip qwenpaw
qwenpaw init
qwenpaw models config
qwenpaw app
```

macOS/Linux:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip qwenpaw
qwenpaw init
qwenpaw models config
qwenpaw app
```

The default working directory is `~/.qwenpaw`, and secrets are stored
separately in `~/.qwenpaw.secret`. Do not copy either directory into the
repository or commit them. The service listens on `127.0.0.1:8088` by default.

For other installation methods and current version requirements, consult the
official pages:

- [QwenPaw Quick Start](https://qwenpaw.agentscope.io/docs/quickstart/)
- [QwenPaw Downloads](https://qwenpaw.agentscope.io/downloads)
- [QwenPaw CLI](https://qwenpaw.agentscope.io/docs/cli/)
- [Configuration and Working Directory](https://qwenpaw.agentscope.io/docs/config/)

## Configure QwenPaw Runtime Assets

The following is a one-time setup on a new machine. Keep `qwenpaw app` running
in terminal A, open another terminal at the repository root, and activate the
same QwenPaw virtual environment. Complete `qwenpaw init` and
`qwenpaw models config` before running this section.

All PowerShell snippets use one base-URL variable. A default installation uses
port `8088`. If you change the port, update it here, in the project `.env`, and
in `host.docker.internal:8088` in `compose.yml`:

```powershell
$qwenpawBaseUrl = "http://127.0.0.1:8088"
Invoke-RestMethod "$qwenpawBaseUrl/api/version"
```

The following blocks are intended to run sequentially in the same PowerShell
session. If you open a new terminal, set `$qwenpawBaseUrl` again first.

#### macOS/zsh one-command setup

macOS users do not need to translate each PowerShell block below. With
`qwenpaw app` still running, execute:

```zsh
cd /path/to/qwenpaw-ai-agent-competition
source .venv/bin/activate
bash scripts/configure_qwenpaw_macos.sh
```

The script validates and imports local Skills, creates only missing project
Agents, injects the shared ethics baseline, installs the Qwen-Image Plugin, and
configures/enables its two image tools for `scene` when the root `.env`
contains `DASHSCOPE_API_KEY`. It never prints the key. Without a key, it leaves
the plugin installed while keeping the image tools unconfigured and disabled.
Set `QWENPAW_BASE_URL` before the command to override the default endpoint.

### 1. Import All Local Skills

The project contains six business Skills and four ethics Skills:

| Skill | Purpose | Mounted on |
|---|---|---|
| `route-adjust` | Natural-language route refinement | `route` |
| `requirement-understand` | Structure travel requirements | `intent` |
| `preference-guide` | Multi-turn route-preference completion | `pref-guide` |
| `macau-guide` | Evidence-grounded cultural commentary | `guide` |
| `photo-recognize` | Image descriptions and POI identification | `photo` |
| `postcard-scene` | SVG postcard-scene constraints | `scene` |
| `qwen-image-postcard` | Real travel-memory images through Qwen-Image | `scene` |
| `fairness-gate` | Preference fairness checks | `intent` |
| `source-attribution` | Source and confidence attribution | `guide`, `photo` |
| `anti-sycophancy` | Avoid agreement-seeking and unsupported assertions | `guide` |
| `content-safety-review` | Independent content-safety decisions | `reviewer` |

Import them with PowerShell:

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

QwenPaw does not register a Skill merely because its file appears in
`skill_pool`; the final `pool/refresh` call is required. Check the result with
`qwenpaw skills list`. For background and troubleshooting, see
[`skills/README.md`](skills/README.md) and the [QwenPaw Skills
documentation](https://qwenpaw.agentscope.io/docs/skills/).

### 2. Create All Agents and Mount Their Skills

First run `qwenpaw models list` to confirm that the default model is configured.
The commands below read the active Provider ID and Model ID from the running
QwenPaw instance, avoiding stale model names copied from documentation. `photo`
and `scene` must use a vision-capable multimodal model. If the default model
cannot process images, switch to a compatible model in QwenPaw first. Keep the
`default` Agent created by `qwenpaw init`; the seven dedicated Agent IDs below
are part of the backend contract and must not be renamed.

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
  --skill qwen-image-postcard
Invoke-QwenPawChecked agents create --agent-id reviewer --name "独立审核" --language zh `
  --provider-id $provider --model-id $model --skill content-safety-review

Invoke-QwenPawChecked agents list
```

These commands are for first-time setup. If an Agent already exists, do not
delete and recreate it; run `qwenpaw skills config --agent-id <agent-id>` to
correct its Skills interactively. The built-in `view_image` tool must remain
enabled for `photo`.

`intent` parses a relatively complete request into a Preference in one pass.
`pref-guide` handles incomplete input through multiple turns, asking for only
one missing item in each turn and emitting a Preference once enough information
has been collected. The backend always calls `pref-guide`, so do not rename its
Agent ID to an underscore form or any other value. This Agent can use a regular
text model; it does not need `view_image`, a multimodal model, or the Qwen-Image
Plugin.

### 3. Inject the Shared Ethics Baseline into All Project Agents

Every project Agent, including the `default` created by `qwenpaw init`, must use
the same ethics prompt. Its contents come exactly from lines 9–42 of
[`ethics/prompts/_ethics_base.md`](ethics/prompts/_ethics_base.md), and the
first run replaces lines 14–44 in the default `AGENTS.md` files of all eight
project workspaces.

The script below adds comment markers, making it safe to rerun. The first run
replaces the lines described above; subsequent runs only update the marked
region. It obtains actual workspace paths through the QwenPaw API and only
processes this project's `default` and seven dedicated Agents. It does not
change QwenPaw's built-in QA Agent or any other user Agents. Run it after
creating every dedicated Agent. The built-in QA Agent is not part of this
project's runtime contract and has its own QA instructions, so its `AGENTS.md`
is intentionally left unchanged.

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

Use only `ethics/qwenpaw-skills/<skill>/SKILL.md` as the contents of an ethics
Skill. Do not copy or mount the standalone `prompt.md` files in that directory,
and do not add them to `AGENTS.md` or an Agent system prompt. Their rules
duplicate `SKILL.md`; injecting both increases prompt conflicts and context
noise.

### 4. Install the Qwen-Image Tool Plugin

The repository includes a copy of the official Plugin compatible with
AgentScope 1.0 / QwenPaw 1.1.12 post3:

```powershell
& qwenpaw plugin validate .\backend\app\tools\qwen-image
if ($LASTEXITCODE -ne 0) { throw "Qwen-Image Plugin 校验失败" }
& qwenpaw plugin install .\backend\app\tools\qwen-image --force
if ($LASTEXITCODE -ne 0) { throw "Qwen-Image Plugin 安装失败" }
& qwenpaw plugin list
if ($LASTEXITCODE -ne 0) { throw "无法读取 Plugin 列表" }
```

If QwenPaw is running, installation hot-loads the Plugin. If it is stopped, the
Plugin is installed offline and loads the next time `qwenpaw app` starts. It
provides `generate_image_qwen` and `edit_image_qwen`; enable them only for the
`scene` Agent.

The following PowerShell reads the key from the project `.env` without writing
the plaintext value to command history, configures the tools through the local
QwenPaw API, and enables them when necessary:

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

For an international DashScope key, change the endpoint to
`https://dashscope-intl.aliyuncs.com/api/v1`. The key and endpoint must belong
to the same region. If QwenPaw web authentication is enabled, add the
appropriate Authorization header or Cookie to these requests.

The `postcard-scene` Skill retains legacy SVG-output constraints. In the online
postcard flow, the backend explicitly requests `generate_image_qwen` or
`edit_image_qwen`. A successful online test must show the Plugin's
`plugin_call_output` and return an image. If it only returns SVG, the legacy
constraints interfered with the tool call and the Qwen-Image setup has not
succeeded.

### 5. Verify the QwenPaw Configuration

The script below can run independently in a new PowerShell session. It performs
one QwenPaw model health check and verifies every project Agent, Skill, ethics
baseline, and image tool. It does not generate a postcard image.

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
  scene = @("postcard-scene", "qwen-image-postcard")
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

After verification, set all six Agent switches in `.env` to `true`, keep
`POSTCARD_AI_IMAGE_ENABLED=true`, and run:

```powershell
docker compose up -d --build
```

For QwenPaw responsibilities, structured-output constraints, and fallback
behavior, see [`skills/README.md`](skills/README.md). For postcard Plugin
details, see
[`backend/README.md`](backend/README.md#明信片-qwen-image-场景图与照片风格化).

## Project Overview

An AI-powered travel companion for exploring Macau's historic districts.
Delivered as a WeChat Mini Program / mobile app, it provides real-time
location-based commentary, intelligent route planning, and a gamified
experience for tourists.

## Core Features

### 1. Historic District Guide

- **Location-aware commentary**: When users enter a district, the app generates
  contextual descriptions of its history, landmarks, and culture based on
  their current location.
- **Audio narration**: All content is delivered with voice commentary.
- **Tour route generation**: Automatically creates optimized walking routes
  with guided narration.

### 2. Intelligent Route Planning

- **Route optimization**: Combines local attractions and trending spots into
  curated routes.
- **Dynamic adjustments**: Fine-tunes routes based on crowd levels, weather,
  and seasonality.
- **Map visualization**: Highlights key stops and connections on a map; tapping
  a stop reveals a timeline with detailed content.
- **Itinerary view**: A memo-style trip plan for easy reference.
- **Gamification**: Check-in points encourage exploration, following an
  engagement model similar to Duolingo.

#### Input Factors

- Real-time crowd levels
- Weather conditions
- Optimal local routes
- User-defined travel type and purpose
- Macau festivals and cultural events
- Casino shuttle-bus routes

### 3. User Management

- **Registration and login**: Collects name, contact details (email/phone),
  country of origin, language preference, visit duration, and travel type
  (solo, family, or post-conference leisure).
- **Preference checklist**: Learns what the user wants to explore in Macau,
  such as entertainment, culture, or history.
- **Tutorial**: An onboarding video walkthrough of app features.
- **Personal center**: Profile and trip management.

### 4. Human-in-the-Loop Curation

- **Offline research data**: Uses the team's existing Xiaohongshu dataset (100
  high-engagement notes and 751 comments, 2023–2025) as a static source for POI
  popularity, pain points, and route priors. Real-time social-media monitoring
  and continued crawling are outside the competition scope.
- **Crowd intelligence**: Monitors crowd levels at ports and attractions when
  available through CrowdPass or similar data sources.
- **Manual curation and feedback**: Team-reviewed content updates and in-app
  user feedback replace live social listening for knowledge iteration.

## Current Stage

The core frontend-to-backend loop is operational: multi-turn preference
guidance, route matching and Agent refinement, RAG commentary, photo
recognition, AMap maps and walking routes, location triggers, four-language
TTS, postcards, and Qwen-Image generation/stylization are all integrated. The
current priority is validating reproducible deployment in a clean environment,
running end-to-end smoke tests with real AMap, DashScope, OSS, and QwenPaw
services, and continuing to build evaluation evidence.

## Project Goal

Build an interactive AI Agent application prototype based on QwenPaw that
delivers a seamless, personalized tour experience for Macau visitors.

## Team Collaboration

- Keep documentation updated as decisions become clearer.
- Use `docs/idea-pool.md` to collect and compare project ideas.
- Use `docs/team-roles.md` to clarify ownership and collaboration boundaries.
- Keep frontend, backend, RAG, assets, and scripts in their dedicated folders.
- Prefer small, frequent commits with clear messages.
- Discuss major architecture, product, and competition-track decisions before
  implementation.
