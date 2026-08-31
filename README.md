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

Windows users can run `pwsh -NoProfile -File scripts/configure_qwenpaw_windows.ps1`
after initialization, adding `-UpdateExistingSkills` after pulling Skill updates.
PowerShell instructions remain below, alongside native macOS/zsh
commands. After installing and initializing QwenPaw, macOS users can run
`bash scripts/configure_qwenpaw_macos.sh` to configure the project's Skills,
Agents, ethics baseline, Qwen-Image Plugin, and Qwen TTS Plugin without
installing PowerShell 7.

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

At minimum, set your own `DASHSCOPE_API_KEY`, `AMAP_WEB_SERVICE_KEY`,
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
- Backend OpenAPI: <http://localhost:8001/docs>
- QwenPaw Console: <http://127.0.0.1:8088>

```powershell
Invoke-RestMethod http://127.0.0.1:8001/api/v1/health
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
curl -fsS http://127.0.0.1:8001/api/v1/health
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
| `DASHSCOPE_API_KEY` | Required for complete AI functionality | Your own Alibaba Cloud Model Studio/DashScope key, used by TTS, images, and some backend capabilities; it is not provided by the competition organizer |
| `QWEN_EMBEDDING_API_KEY` | Optional | Dedicated RAG embedding key; falls back to the DashScope key when empty |
| `AMAP_WEB_SERVICE_KEY` | Required for walking-route planning | AMap "Web Service" key |
| `VITE_AMAP_API_KEY` | Required for the frontend map | AMap "Web (JS API)" key |
| `VITE_AMAP_SECURITY_CODE` | Required for the frontend map | Security code paired with the Web key |
| `AMAP_API_KEY` / `AMAP_SECURITY_CODE` | Recommended | Backend compatibility fields; keep them consistent with the frontend key/security code |
| `QWENPAW_BASE_URL` | Has a default | Use `http://127.0.0.1:8088` for local development |

Create AMap keys on the [AMap Open Platform](https://lbs.amap.com/) and create
your own DashScope key in the [Alibaba Cloud Model Studio
console](https://bailian.console.aliyun.com/). The DashScope image-generation
key is not supplied by the competition organizer: use an account and key you
control, and make sure its quota, billing, and region are suitable for your
deployment. You must also configure the key
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

Complete `qwenpaw init` and configure a model first. Keep `qwenpaw app` running
on this machine at `http://127.0.0.1:8088`; configuration does not start or
restart the backend or frontend.

### Windows / PowerShell 7

From the repository root:

```powershell
# First-time setup: preserve existing workspace Skill copies.
pwsh -NoProfile -File .\scripts\configure_qwenpaw_windows.ps1

# After pulling updated Skills: back up and update existing project copies.
pwsh -NoProfile -File .\scripts\configure_qwenpaw_windows.ps1 -UpdateExistingSkills

# Read-only local verification, including Skill content parity.
pwsh -NoProfile -File .\scripts\configure_qwenpaw_windows.ps1 -VerifyOnly
```

The script derives the repository root from its own location, so an absolute
script path also works from another directory. It uses the running QwenPaw
HTTP API and needs no activated Python environment or additional PowerShell
modules. Set `-BaseUrl http://127.0.0.1:8088` or `QWENPAW_BASE_URL` to select a
different local port. Only loopback endpoints are accepted; redirects are
rejected. For authenticated instances, pass the appropriate headers with
`-Headers` from your session without putting credentials in command history.

The default mode updates the shared pool and mounts missing Skills with
`overwrite=false`; it warns about differing workspace copies and preserves
them. Pool refresh alone does **not** update an Agent's existing copy.
`-UpdateExistingSkills` explicitly refreshes repository-owned `SKILL.md`
files in project workspaces, while preserving unrelated files and Skills.
Before modifying existing files, it saves originals and configuration manifests
under the discovered QwenPaw directory at `backups/storywalk/<timestamp-id>/`.
The printed backup location is local; backups may contain credentials and must
not be committed or shared. A failed run stops with an error; retain its backup
for recovery. Re-running applies the same configuration without duplicating
Agents or prompt blocks.

These commands replace the previous inline Windows setup and verification
snippets, which used the older combined `scene` Agent.

### Current Agent and Skill mapping

There are **nine project Agents** (`default` plus eight dedicated Agents) and
**13 pool Skills** (nine business Skills plus four ethics Skills):

| Agent | Required Skills | Responsibility |
| --- | --- | --- |
| `default` | No additional required Skill | Shared ethics baseline |
| `route` | `route-adjust` | Route adjustments |
| `intent` | `requirement-understand`, `fairness-gate` | Complete requests |
| `pref-guide` | `preference-guide` | Ask for one missing preference per turn |
| `guide` | `macau-guide`, `source-attribution`, `anti-sycophancy` | Grounded narration and approved-text TTS |
| `photo` | `photo-recognize`, `source-attribution` | Photo recognition |
| `scene` | `gc-minimal-zine-poster` | No-photo generation with `generate_image_qwen` |
| `scene-photo` | `qwen-image-postcard`, `photo-abstract-editorial` | Authorized, privacy-scrubbed photo edits with `edit_image_qwen` |
| `reviewer` | `content-safety-review` | Independent content review |

`postcard-scene` remains in the pool for legacy compatibility. The Windows
script disables the three old scene Skills on `scene` without deleting their
files. It disables `edit_image_qwen` on `scene` and `generate_image_qwen` on
`scene-photo`. Agent IDs are backend contracts; do not rename them.

The active model and workspace paths are discovered through `/api/models/active`
and `/api/agents`. Existing text models are preserved. For `photo`, `scene`,
and `scene-photo`, the script checks declared multimodal support and keeps
`view_image` enabled. If their model lacks that declaration, it uses the
existing `photo` model, then the active model, only when declared vision-capable;
otherwise it stops before changing configuration. This is a configuration check,
not a live model capability test.

All nine Agents receive exactly lines 9–42 of
[`ethics/prompts/_ethics_base.md`](ethics/prompts/_ethics_base.md) inside the
`MACAU_ETHICS_BASE` markers. Existing marked content is replaced; when markers
are absent, the block is appended without deleting existing instructions.
Malformed or duplicate markers cause an error before writes. Additional marked
blocks define guide TTS, no-photo generation, and photo-editing rules.
Only ethics `SKILL.md` files are copied; redundant ethics `prompt.md` files are
backed up and removed. Built-in QA and unrelated Agent instructions are untouched.

### Tool Plugins and credentials

Both scripts install the repository Plugins in
`backend/app/tools/qwen-image/` and `backend/app/tools/qwen-tts/`.
The Windows script hot-loads changed Plugins through the selected local API,
preserves unrelated Agent settings, and never reinstalls QwenPaw or upgrades
the Python environment.

Image tools use `QWEN_IMAGE_API_KEY`, `QWEN_IMAGE_ENDPOINT`, and
`QWEN_IMAGE_MODEL`. TTS uses `DASHSCOPE_API_KEY` for `guide/synthesize_speech_qwen`.
Nonempty process variables take precedence over the root `.env`.
The image endpoint defaults to `https://dashscope.aliyuncs.com/api/v1`;
a `/compatible-mode/v1` suffix is converted to `/api/v1`.
Use the regional endpoint matching your key. The project provides no API keys;
usage and charges belong to the deploying account.

The Windows script does not print keys or write temporary secret payload files.
If a key is absent, its corresponding tools are disabled and existing stored
credentials are preserved. Verification reports disabled tools explicitly.
`-VerifyOnly` checks local Agents, mounted Skills, ethics markers, Plugins,
vision declarations, and tool configuration; it does **not** call
`qwenpaw doctor`, chat models, image generation, or TTS.

### macOS / zsh

```zsh
cd /path/to/qwenpaw-ai-agent-competition
source .venv/bin/activate
bash scripts/configure_qwenpaw_macos.sh

# After changing only image credentials or the endpoint:
bash scripts/sync_qwen_image_config.sh
```

The macOS helper preserves existing workspace Skill copies and includes
`qwenpaw doctor`, which may check model connectivity. It does not have the
Windows script's update/backup or read-only verification modes.

After configuration, enable the desired backend flags in `.env`:
`ROUTE_AGENT_ENABLED`, `INTENT_AGENT_ENABLED`,
`PREFERENCE_GUIDE_AGENT_ENABLED`, `REVIEWER_AGENT_ENABLED`,
`GUIDE_AGENT_ENABLED`, `PHOTO_AGENT_ENABLED`, `POSTCARD_AI_IMAGE_ENABLED`, and
`QWENPAW_TTS_ENABLED`. Use `QWENPAW_TTS_DIRECT_FALLBACK_ENABLED=false` only if
QwenPaw TTS failures should be surfaced instead of using the direct fallback.
Rebuild/restart the backend only when its environment or code changes; Skill
synchronization alone does not require rebuilding it.

For structured output and fallbacks, see [`skills/README.md`](skills/README.md)
and [`backend/README.md`](backend/README.md#明信片-qwen-image-场景图与照片风格化).

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
