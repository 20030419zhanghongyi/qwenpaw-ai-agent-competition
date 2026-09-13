"""Exercise the real PowerShell entry point against an isolated local QwenPaw API.

No backend conftest, real user workspace, credentials, or model services are used.
"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Thread

import pytest


REPO = Path(__file__).resolve().parents[2]
PWSH = shutil.which("pwsh")
pytestmark = pytest.mark.skipif(not PWSH, reason="PowerShell 7 is required")
MODEL = {"provider_id": "test-provider", "model": "test-vision"}
SKILLS = {
    "route": ["route-adjust"],
    "intent": ["requirement-understand", "fairness-gate"],
    "pref-guide": ["preference-guide"],
    "guide": ["macau-guide", "source-attribution", "anti-sycophancy"],
    "photo": ["photo-recognize", "source-attribution"],
    "scene": ["postcard-scene", "qwen-image-postcard", "photo-abstract-editorial"],
    "reviewer": ["content-safety-review"],
}


class Runtime:
    def __init__(self, root: Path):
        self.repo = root / "repo with spaces"
        self.root = root / "runtime with spaces"
        self.repo.mkdir()
        self.root.mkdir()
        for name in ("skills", "ethics", "backend/app/tools"):
            shutil.copytree(
                REPO / name, self.repo / name, ignore=shutil.ignore_patterns("__pycache__")
            )
        (self.repo / "scripts").mkdir()
        shutil.copy2(REPO / "scripts/configure_qwenpaw_windows.ps1", self.repo / "scripts")
        (self.root / "config.json").write_text("{}", encoding="utf-8")
        self.agents = {}
        self.configs = {}
        self.skills = {}
        self.plugins = {}
        self.calls = []
        self.fail_path = None
        for agent_id in ["default", *SKILLS, "QwenPaw_QA_Agent_0.2", "personal"]:
            self.create_agent({"id": agent_id, "name": agent_id, "active_model": MODEL})
            for name in SKILLS.get(agent_id, []):
                directory = self.workspace(agent_id) / "skills" / name
                directory.mkdir(parents=True)
                source = self.repo / "skills" / name / "SKILL.md"
                if not source.exists():
                    source = self.repo / "ethics/qwenpaw-skills" / name / "SKILL.md"
                shutil.copy2(source, directory / "SKILL.md")
                self.skills[agent_id][name] = True
        self.stale = self.workspace("pref-guide") / "skills/preference-guide/SKILL.md"
        self.stale.write_text("developer customized old skill\n", encoding="utf-8")
        (self.stale.parent / "notes.txt").write_text("keep this extra file", encoding="utf-8")
        redundant = self.workspace("guide") / "skills/source-attribution/prompt.md"
        redundant.write_text("redundant old prompt", encoding="utf-8")

    def workspace(self, agent_id):
        return self.root / "workspaces" / agent_id

    def create_agent(self, body):
        agent_id = body["id"]
        workspace = self.workspace(agent_id)
        workspace.mkdir(parents=True)
        (workspace / "AGENTS.md").write_text(
            "# Keep custom instructions\n\nOriginal safety rules.\n", encoding="utf-8"
        )
        self.agents[agent_id] = {
            "id": agent_id,
            "name": body["name"],
            "enabled": True,
            "workspace_dir": str(workspace),
            "active_model": body["active_model"],
        }
        self.configs[agent_id] = {
            "id": agent_id,
            "active_model": body["active_model"],
            "description": "keep description",
            "tools": {
                "builtin_tools": {
                    name: {"enabled": True, "config": {}}
                    for name in (
                        "view_image",
                        "generate_image_qwen",
                        "edit_image_qwen",
                        "synthesize_speech_qwen",
                    )
                }
            },
        }
        self.skills[agent_id] = {}
        (workspace / "agent.json").write_text(json.dumps(self.configs[agent_id]), encoding="utf-8")
        (workspace / "skill.json").write_text("{}", encoding="utf-8")
        for name in body.get("skill_names", []):
            self.mount(agent_id, name)

    def mount(self, agent_id, name):
        destination = self.workspace(agent_id) / "skills" / name
        shutil.copytree(self.root / "skill_pool" / name, destination)
        self.skills[agent_id][name] = True

    def dispatch(self, method, path, agent_id, body):
        self.calls.append((method, path, agent_id, body))
        if path == self.fail_path:
            return 400, {"detail": "must-not-leak-test-secret"}
        if path == "version":
            return 200, {"version": "test"}
        if path == "models/active":
            return 200, {"active_llm": MODEL}
        if path == "models":
            return 200, [
                {
                    "id": MODEL["provider_id"],
                    "models": [
                        {"id": MODEL["model"], "supports_multimodal": True},
                    ],
                    "extra_models": [],
                }
            ]
        if path == "agents":
            if method == "POST":
                self.create_agent(body)
            return 200, {"agents": list(self.agents.values())}
        if path.startswith("agents/"):
            target = path.split("/")[1]
            if method == "PUT":
                self.configs[target] = body
                self.agents[target]["active_model"] = body["active_model"]
            return 200, self.configs[target]
        if path == "skills/pool/refresh":
            return 200, []
        if path == "skills/pool/download":
            assert body["overwrite"] is False
            self.mount(body["targets"][0]["workspace_id"], body["skill_name"])
            return 200, {"downloaded": body["targets"]}
        if path in ("skills", "skills/refresh"):
            return 200, [
                {"name": name, "enabled": enabled}
                for name, enabled in self.skills[agent_id].items()
            ]
        if path.startswith("skills/"):
            _, name, action = path.split("/")
            self.skills[agent_id][name] = action == "enable"
            return 200, {"success": True}
        if path == "plugins":
            return 200, list(self.plugins.values())
        if path == "plugins/install":
            source = Path(body["source"])
            manifest = json.loads((source / "plugin.json").read_text(encoding="utf-8"))
            self.plugins[manifest["id"]] = {"id": manifest["id"], "loaded": True, "enabled": True}
            shutil.copytree(source, self.root / "plugins" / manifest["id"], dirs_exist_ok=True)
            return 200, self.plugins[manifest["id"]]
        if path == "tools":
            return 200, [
                {
                    "name": name,
                    "enabled": tool["enabled"],
                    "config_values": {
                        **tool["config"],
                        "api_key": "***" if tool["config"].get("api_key") else None,
                    },
                }
                for name, tool in self.configs[agent_id]["tools"]["builtin_tools"].items()
            ]
        if path.startswith("tools/"):
            _, name, action = path.split("/")
            tool = self.configs[agent_id]["tools"]["builtin_tools"][name]
            if action == "toggle":
                tool["enabled"] = not tool["enabled"]
            else:
                tool["config"] = body["config"]
            return 200, {"success": True}
        raise AssertionError(f"Unexpected API call: {method} {path}")

    def run(self, *args):
        env = {
            key: value
            for key, value in os.environ.items()
            if key
            not in (
                "QWENPAW_BASE_URL",
                "QWEN_IMAGE_API_KEY",
                "QWEN_IMAGE_MODEL",
                "QWEN_IMAGE_ENDPOINT",
                "DASHSCOPE_API_KEY",
            )
        }
        return subprocess.run(
            [
                PWSH,
                "-NoProfile",
                "-File",
                str(self.repo / "scripts/configure_qwenpaw_windows.ps1"),
                "-BaseUrl",
                f"http://127.0.0.1:{self.port}/",
                *args,
            ],
            cwd=self.root,
            env=env,
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=60,
        )

    def hashes(self):
        return {
            str(path.relative_to(self.root)): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in self.root.rglob("*")
            if path.is_file() and "backups" not in path.parts
        }


@pytest.fixture
def runtime(tmp_path):
    state = Runtime(tmp_path)

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            size = int(self.headers.get("Content-Length", 0))
            body = json.loads(self.rfile.read(size)) if size else None
            status, result = state.dispatch(
                self.command,
                self.path.removeprefix("/api/"),
                self.headers.get("X-Agent-Id"),
                body,
            )
            payload = json.dumps(result).encode()
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

        do_POST = do_GET
        do_PUT = do_GET
        do_PATCH = do_GET

        def log_message(self, *_args):
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    state.port = server.server_port
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield state
    finally:
        server.shutdown()
        server.server_close()
        thread.join()


def assert_ok(result):
    assert result.returncode == 0, result.stdout + result.stderr


def test_upgrade_preserves_custom_data_and_is_repeatable(runtime):
    untouched = {
        key: value
        for key, value in runtime.hashes().items()
        if "QwenPaw_QA_Agent_0.2" in key or "personal" in key
    }
    assert_ok(runtime.run())
    assert runtime.stale.read_text() == "developer customized old skill\n"
    assert runtime.run("-VerifyOnly").returncode != 0
    runtime.calls.clear()
    assert_ok(runtime.run("-UpdateExistingSkills"))
    assert (
        runtime.stale.read_bytes()
        == (runtime.repo / "skills/preference-guide/SKILL.md").read_bytes()
    )
    assert (runtime.stale.parent / "notes.txt").read_text() == "keep this extra file"
    backups = list((runtime.root / "backups").rglob("SKILL.md"))
    assert any(path.read_text() == "developer customized old skill\n" for path in backups)
    assert "scene-photo" in runtime.agents
    assert not runtime.skills["scene"]["postcard-scene"]
    assert runtime.skills["scene"]["gc-minimal-zine-poster"]
    for agent in runtime.agents:
        assert "Original safety rules." in (runtime.workspace(agent) / "AGENTS.md").read_text(
            encoding="utf-8"
        )
    before = runtime.hashes()
    runtime.calls.clear()
    assert_ok(runtime.run("-UpdateExistingSkills"))
    assert runtime.hashes() == before
    assert not any(path == "plugins/install" for _, path, _, _ in runtime.calls)
    runtime.calls.clear()
    assert_ok(runtime.run("-VerifyOnly"))
    assert all(method == "GET" for method, *_ in runtime.calls)
    assert runtime.hashes() == before
    assert all(runtime.hashes()[key] == value for key, value in untouched.items())


def test_keys_and_image_endpoint_are_separate_and_never_logged(runtime):
    (runtime.repo / ".env").write_text(
        'QWEN_IMAGE_API_KEY="test-image-secret"\nDASHSCOPE_API_KEY=test-tts-secret\n'
        "QWEN_IMAGE_ENDPOINT=https://dashscope-intl.aliyuncs.com/compatible-mode/v1/\n"
        "QWEN_IMAGE_MODEL=qwen-image-2.0-pro\n",
        encoding="utf-8",
    )
    result = runtime.run("-UpdateExistingSkills")
    assert_ok(result)
    assert "test-image-secret" not in result.stdout + result.stderr
    assert "test-tts-secret" not in result.stdout + result.stderr
    scene = runtime.configs["scene"]["tools"]["builtin_tools"]
    photo = runtime.configs["scene-photo"]["tools"]["builtin_tools"]
    guide = runtime.configs["guide"]["tools"]["builtin_tools"]
    assert scene["generate_image_qwen"]["config"]["api_key"] == "test-image-secret"
    assert (
        scene["generate_image_qwen"]["config"]["endpoint"]
        == "https://dashscope-intl.aliyuncs.com/api/v1"
    )
    assert guide["synthesize_speech_qwen"]["config"]["api_key"] == "test-tts-secret"
    assert scene["generate_image_qwen"]["config"]["model"] == "qwen-image-2.0-pro"
    assert photo["edit_image_qwen"]["enabled"]
    assert not photo["generate_image_qwen"]["enabled"]
    assert not scene["edit_image_qwen"]["enabled"]


def test_verify_only_detects_stale_enabled_image_model_without_leaking_keys(runtime):
    (runtime.repo / ".env").write_text(
        "QWEN_IMAGE_API_KEY=test-image-secret\n"
        "DASHSCOPE_API_KEY=test-tts-secret\n"
        "QWEN_IMAGE_MODEL=qwen-image-2.0-pro\n",
        encoding="utf-8",
    )
    assert_ok(runtime.run("-UpdateExistingSkills"))
    runtime.configs["scene"]["tools"]["builtin_tools"]["generate_image_qwen"]["config"][
        "model"
    ] = "wanx2.1-t2i-turbo"
    before = runtime.hashes()
    runtime.calls.clear()

    result = runtime.run("-VerifyOnly")

    output = result.stdout + result.stderr
    assert result.returncode != 0
    assert "Tool configuration differs from .env/defaults" in output
    assert "scene/generate_image_qwen/model" in output
    assert "test-image-secret" not in output
    assert "test-tts-secret" not in output
    assert all(method == "GET" for method, *_ in runtime.calls)
    assert runtime.hashes() == before


def test_invalid_shared_image_model_fails_before_runtime_writes(runtime):
    (runtime.repo / ".env").write_text(
        "QWEN_IMAGE_API_KEY=test-image-secret\n"
        "QWEN_IMAGE_MODEL=wanx2.1-t2i-turbo\n",
        encoding="utf-8",
    )
    before = runtime.hashes()

    result = runtime.run("-UpdateExistingSkills")

    output = result.stdout + result.stderr
    assert result.returncode != 0
    assert "QWEN_IMAGE_MODEL 'wanx2.1-t2i-turbo'" in output
    assert "Valid shared options" in output
    assert "test-image-secret" not in output
    assert runtime.hashes() == before
    assert not (runtime.root / "backups").exists()
    assert all(method == "GET" for method, *_ in runtime.calls)


@pytest.mark.parametrize("corruption", ["markers", "outside_workspace"])
def test_preflight_fails_without_partial_writes(runtime, corruption):
    if corruption == "markers":
        (runtime.workspace("guide") / "AGENTS.md").write_text(
            "<!-- MACAU_ETHICS_BASE_START -->\n", encoding="utf-8"
        )
    else:
        runtime.agents["guide"]["workspace_dir"] = str(runtime.repo)
    before = runtime.hashes()
    assert runtime.run("-UpdateExistingSkills").returncode != 0
    assert runtime.hashes() == before
    assert not (runtime.root / "backups").exists()
    assert all(method == "GET" for method, *_ in runtime.calls)


def test_api_error_does_not_echo_response_secrets(runtime):
    runtime.fail_path = "version"
    result = runtime.run()
    assert result.returncode != 0
    assert "must-not-leak-test-secret" not in result.stdout + result.stderr
