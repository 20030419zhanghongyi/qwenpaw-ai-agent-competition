#!/usr/bin/env bash
# Configure the project-specific QwenPaw skills, agents, ethics baseline, and image plugin on macOS.
# Run from any directory: bash scripts/configure_qwenpaw_macos.sh

set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$repo_root"
qwenpaw_base_url="${QWENPAW_BASE_URL:-http://127.0.0.1:8088}"

for command_name in curl python3 qwenpaw; do
  command -v "$command_name" >/dev/null || {
    echo "Missing required command: $command_name" >&2
    exit 1
  }
done

curl -fsS "$qwenpaw_base_url/api/version" >/dev/null || {
  echo "QwenPaw is not reachable at $qwenpaw_base_url. Start 'qwenpaw app' first." >&2
  exit 1
}

agents_json="$(curl -fsS "$qwenpaw_base_url/api/agents")"
default_workspace="$(printf '%s' "$agents_json" | python3 -c '
import json, sys
agents = json.load(sys.stdin).get("agents", [])
default = next((item for item in agents if item.get("id") == "default"), None)
if default is None:
    raise SystemExit("The default QwenPaw agent is missing")
print(default["workspace_dir"])
')"
qwenpaw_working_dir="$(dirname "$(dirname "$default_workspace")")"
skill_pool="$qwenpaw_working_dir/skill_pool"
mkdir -p "$skill_pool"

skill_sources=(
  "skills/route-adjust"
  "skills/requirement-understand"
  "skills/preference-guide"
  "skills/macau-guide"
  "skills/photo-recognize"
  "skills/postcard-scene"
  "skills/qwen-image-postcard"
  "ethics/qwenpaw-skills/fairness-gate"
  "ethics/qwenpaw-skills/source-attribution"
  "ethics/qwenpaw-skills/anti-sycophancy"
  "ethics/qwenpaw-skills/content-safety-review"
)
ethics_skills=(fairness-gate source-attribution anti-sycophancy content-safety-review)

for source_dir in "${skill_sources[@]}"; do
  skill_name="$(basename "$source_dir")"
  destination="$skill_pool/$skill_name"
  mkdir -p "$destination"
  cp "$source_dir/SKILL.md" "$destination/SKILL.md"
  for ethics_skill in "${ethics_skills[@]}"; do
    [[ "$skill_name" == "$ethics_skill" ]] && rm -f "$destination/prompt.md"
  done
  qwenpaw skills test "$destination"
done
curl -fsS -X POST "$qwenpaw_base_url/api/skills/pool/refresh" >/dev/null

active_model="$(curl -fsS "$qwenpaw_base_url/api/models/active")"
provider="$(printf '%s' "$active_model" | python3 -c 'import json,sys; print(json.load(sys.stdin).get("active_llm", {}).get("provider_id", ""))')"
model="$(printf '%s' "$active_model" | python3 -c 'import json,sys; print(json.load(sys.stdin).get("active_llm", {}).get("model", ""))')"
[[ -n "$provider" && -n "$model" ]] || {
  echo "No active QwenPaw model is configured. Run 'qwenpaw models config' first." >&2
  exit 1
}

create_agent_if_missing() {
  local agent_id="$1"
  local agent_name="$2"
  shift 2
  if printf '%s' "$agents_json" | python3 -c 'import json,sys; aid=sys.argv[1]; raise SystemExit(0 if any(x.get("id") == aid for x in json.load(sys.stdin).get("agents", [])) else 1)' "$agent_id"; then
    echo "Agent already exists: $agent_id"
    return
  fi
  local args=(agents create --agent-id "$agent_id" --name "$agent_name" --language zh --provider-id "$provider" --model-id "$model")
  for skill_name in "$@"; do args+=(--skill "$skill_name"); done
  qwenpaw "${args[@]}"
}

create_agent_if_missing route "路线微调" route-adjust
create_agent_if_missing intent "需求理解" requirement-understand fairness-gate
create_agent_if_missing pref-guide "偏好多轮引导" preference-guide
create_agent_if_missing guide "文化讲解" macau-guide source-attribution anti-sycophancy
create_agent_if_missing photo "拍照识别" photo-recognize source-attribution
create_agent_if_missing scene "明信片场景" postcard-scene qwen-image-postcard
create_agent_if_missing reviewer "独立审核" content-safety-review

# Copy any missing pool skill into existing workspaces without overwriting user-edited copies.
for mapping in \
  'route:route-adjust' \
  'intent:requirement-understand,fairness-gate' \
  'pref-guide:preference-guide' \
  'guide:macau-guide,source-attribution,anti-sycophancy' \
  'photo:photo-recognize,source-attribution' \
  'scene:postcard-scene,qwen-image-postcard' \
  'reviewer:content-safety-review'; do
  agent_id="${mapping%%:*}"
  IFS=',' read -r -a agent_skills <<< "${mapping#*:}"
  for skill_name in "${agent_skills[@]}"; do
    status="$(curl -s -o /dev/null -w '%{http_code}' -X POST "$qwenpaw_base_url/api/skills/pool/download" \
      -H 'Content-Type: application/json' \
      -d "{\"skill_name\":\"$skill_name\",\"targets\":[{\"workspace_id\":\"$agent_id\"}],\"overwrite\":false}")"
    [[ "$status" == "200" || "$status" == "409" ]] || {
      echo "Unable to mount $skill_name on $agent_id (HTTP $status)" >&2
      exit 1
    }
  done
done

AGENTS_JSON="$(curl -fsS "$qwenpaw_base_url/api/agents")" python3 - "$repo_root" <<'PY'
from pathlib import Path
import json
import os
import sys

root = Path(sys.argv[1])
ethics_lines = (root / "ethics/prompts/_ethics_base.md").read_text(encoding="utf-8").splitlines()[8:42]
block = ["<!-- MACAU_ETHICS_BASE_START -->", *ethics_lines, "<!-- MACAU_ETHICS_BASE_END -->"]
ids = {"default", "route", "intent", "pref-guide", "guide", "photo", "scene", "reviewer"}
agents = [a for a in json.loads(os.environ["AGENTS_JSON"]).get("agents", []) if a.get("id") in ids]
missing = ids - {a["id"] for a in agents}
if missing:
    raise SystemExit(f"Missing project agents: {', '.join(sorted(missing))}")
for agent in agents:
    path = Path(agent["workspace_dir"]) / "AGENTS.md"
    lines = path.read_text(encoding="utf-8").splitlines()
    try:
        start = lines.index("<!-- MACAU_ETHICS_BASE_START -->")
        end = lines.index("<!-- MACAU_ETHICS_BASE_END -->", start + 1)
        updated = lines[:start] + block + lines[end + 1:]
    except ValueError:
        if len(lines) < 44:
            raise SystemExit(f"Unexpected short AGENTS.md: {path}")
        updated = lines[:13] + block + lines[44:]
    path.write_text("\n".join(updated) + "\n", encoding="utf-8")
    print(f"Updated ethics baseline: {agent['id']}")
PY

qwenpaw plugin validate backend/app/tools/qwen-image
qwenpaw plugin install backend/app/tools/qwen-image --force

if [[ -f .env && -z "${DASHSCOPE_API_KEY:-}" ]]; then
  DASHSCOPE_API_KEY="$(python3 - <<'PY'
from pathlib import Path
for line in Path('.env').read_text(encoding='utf-8').splitlines():
    if line.startswith('DASHSCOPE_API_KEY='):
        print(line.split('=', 1)[1].strip().strip(chr(34) + chr(39)))
        break
PY
)"
fi

if [[ -n "${DASHSCOPE_API_KEY:-}" ]]; then
  config_file="$(mktemp)"
  trap 'rm -f "$config_file"' EXIT
  DASHSCOPE_API_KEY="$DASHSCOPE_API_KEY" python3 - "$config_file" <<'PY'
import json
import os
import sys
from pathlib import Path
Path(sys.argv[1]).write_text(json.dumps({"config": {
    "api_key": os.environ["DASHSCOPE_API_KEY"],
    "endpoint": "https://dashscope.aliyuncs.com/api/v1",
    "model": "qwen-image-2.0-pro",
    "timeout": 180,
}}), encoding="utf-8")
PY
  for tool_name in generate_image_qwen edit_image_qwen; do
    curl -fsS -X POST "$qwenpaw_base_url/api/tools/$tool_name/config" \
      -H 'X-Agent-Id: scene' -H 'Content-Type: application/json' \
      --data-binary "@$config_file" >/dev/null
    enabled="$(curl -fsS -H 'X-Agent-Id: scene' "$qwenpaw_base_url/api/tools" | python3 -c '
import json, sys
name = sys.argv[1]
print("true" if next((x.get("enabled") for x in json.load(sys.stdin) if x.get("name") == name), False) else "false")
' "$tool_name")"
    [[ "$enabled" == "true" ]] || curl -fsS -X PATCH "$qwenpaw_base_url/api/tools/$tool_name/toggle" -H 'X-Agent-Id: scene' >/dev/null
  done
  echo "Configured Qwen-Image for scene."
else
  echo "DASHSCOPE_API_KEY is absent; Qwen-Image is installed but left unconfigured and disabled."
fi

qwenpaw doctor
qwenpaw agents list
qwenpaw skills list --agent-id scene
qwenpaw plugin info qwen-image-tool
echo "QwenPaw macOS configuration completed."
