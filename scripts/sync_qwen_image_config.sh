#!/usr/bin/env bash
# Synchronize Qwen-Image tool settings from the project .env into a running QwenPaw instance.

set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$repo_root"
qwenpaw_base_url="${QWENPAW_BASE_URL:-http://127.0.0.1:8088}"

for command_name in curl python3; do
  command -v "$command_name" >/dev/null || {
    echo "Missing required command: $command_name" >&2
    exit 1
  }
done

curl -fsS "$qwenpaw_base_url/api/version" >/dev/null || {
  echo "QwenPaw is not reachable at $qwenpaw_base_url. Start 'qwenpaw app' first." >&2
  exit 1
}

config_file="$(mktemp)"
trap 'rm -f "$config_file"' EXIT

if QWEN_IMAGE_API_KEY="${QWEN_IMAGE_API_KEY:-}" \
  QWEN_IMAGE_ENDPOINT="${QWEN_IMAGE_ENDPOINT:-}" \
  QWEN_IMAGE_MODEL="${QWEN_IMAGE_MODEL:-}" \
  python3 - "$config_file" <<'PY'
import json
import os
import sys
from pathlib import Path

values: dict[str, str] = {}
env_path = Path(".env")
if env_path.is_file():
    for line in env_path.read_text(encoding="utf-8").splitlines():
        if "=" not in line or line.lstrip().startswith("#"):
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip(chr(34) + chr(39))

api_key = os.environ.get("QWEN_IMAGE_API_KEY") or values.get("QWEN_IMAGE_API_KEY", "")
if not api_key:
    raise SystemExit(3)

endpoint = (
    os.environ.get("QWEN_IMAGE_ENDPOINT")
    or values.get("QWEN_IMAGE_ENDPOINT")
    or "https://dashscope.aliyuncs.com/api/v1"
).rstrip("/")
if endpoint.endswith("/compatible-mode/v1"):
    endpoint = endpoint.removesuffix("/compatible-mode/v1") + "/api/v1"

model = (
    os.environ.get("QWEN_IMAGE_MODEL")
    or values.get("QWEN_IMAGE_MODEL")
    or "qwen-image-2.0-pro"
)
Path(sys.argv[1]).write_text(
    json.dumps({"config": {
        "api_key": api_key,
        "endpoint": endpoint,
        "model": model,
        "timeout": 180,
    }}),
    encoding="utf-8",
)
PY
then
  for tool_mapping in generate_image_qwen:scene edit_image_qwen:scene-photo; do
    tool_name="${tool_mapping%%:*}"
    tool_agent="${tool_mapping#*:}"
    curl -fsS -X POST "$qwenpaw_base_url/api/tools/$tool_name/config" \
      -H "X-Agent-Id: $tool_agent" -H 'Content-Type: application/json' \
      --data-binary "@$config_file" >/dev/null
    enabled="$(curl -fsS -H "X-Agent-Id: $tool_agent" "$qwenpaw_base_url/api/tools" | python3 -c '
import json, sys
name = sys.argv[1]
print("true" if next((x.get("enabled") for x in json.load(sys.stdin) if x.get("name") == name), False) else "false")
' "$tool_name")"
    [[ "$enabled" == "true" ]] || curl -fsS -X PATCH \
      "$qwenpaw_base_url/api/tools/$tool_name/toggle" -H "X-Agent-Id: $tool_agent" >/dev/null
  done
  echo "Qwen-Image configuration synchronized from .env."
else
  status="$?"
  [[ "$status" == "3" ]] || exit "$status"
  for tool_mapping in generate_image_qwen:scene edit_image_qwen:scene-photo; do
    tool_name="${tool_mapping%%:*}"
    tool_agent="${tool_mapping#*:}"
    enabled="$(curl -fsS -H "X-Agent-Id: $tool_agent" "$qwenpaw_base_url/api/tools" | python3 -c '
import json, sys
name = sys.argv[1]
print("true" if next((x.get("enabled") for x in json.load(sys.stdin) if x.get("name") == name), False) else "false")
' "$tool_name")"
    [[ "$enabled" == "false" ]] || curl -fsS -X PATCH \
      "$qwenpaw_base_url/api/tools/$tool_name/toggle" -H "X-Agent-Id: $tool_agent" >/dev/null
  done
  echo "QWEN_IMAGE_API_KEY is absent; Qwen-Image tools were disabled."
fi

# Enforce the responsibility split even if an older QwenPaw workspace enabled both tools.
for tool_mapping in edit_image_qwen:scene generate_image_qwen:scene-photo; do
  tool_name="${tool_mapping%%:*}"
  tool_agent="${tool_mapping#*:}"
  enabled="$(curl -fsS -H "X-Agent-Id: $tool_agent" "$qwenpaw_base_url/api/tools" | python3 -c '
import json, sys
name = sys.argv[1]
print("true" if next((x.get("enabled") for x in json.load(sys.stdin) if x.get("name") == name), False) else "false")
' "$tool_name")"
  [[ "$enabled" == "false" ]] || curl -fsS -X PATCH \
    "$qwenpaw_base_url/api/tools/$tool_name/toggle" -H "X-Agent-Id: $tool_agent" >/dev/null
done
