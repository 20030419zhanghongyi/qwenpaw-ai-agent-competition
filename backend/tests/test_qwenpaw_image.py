"""QwenPaw image-tool integration tests without real model calls."""

from __future__ import annotations

import json
from io import BytesIO
from pathlib import PurePosixPath, PureWindowsPath

import pytest
from PIL import Image

from app.agents import qwenpaw_client
from app.agents.qwenpaw_client import QwenPawClient, _extract_image_refs
from app.features.postcards import scene_image


def test_extract_image_refs_prefers_local_tool_output():
    local = PurePosixPath("/qwenpaw-test/media/qwen_image/scene.png").as_uri()
    event = {
        "content": [
            {"type": "text", "text": "Saved to: /tmp/qwenpaw-fallback.png"},
            {"type": "image", "source": {"type": "url", "url": local}},
        ]
    }

    refs = _extract_image_refs(event)

    assert refs[0] == local
    assert PurePosixPath("/tmp/qwenpaw-fallback.png").as_uri() in refs


def test_ask_for_image_stops_after_plugin_image(monkeypatch):
    reference = PurePosixPath("/qwenpaw-test/media/qwen_image/scene.png").as_uri()
    event = {
        "object": "message",
        "type": "plugin_call_output",
        "content": [{"type": "image", "source": {"type": "url", "url": reference}}],
    }

    class FakeResponse:
        status_code = 200
        text = ""

        def read(self):
            return b""

        def iter_lines(self):
            yield f"data: {json.dumps(event)}"
            yield ""
            raise AssertionError("stream should stop after the image event")

    class FakeStream:
        def __enter__(self):
            return FakeResponse()

        def __exit__(self, *_args):
            return False

    stopped: list[tuple[str, str]] = []
    monkeypatch.setattr(qwenpaw_client.httpx, "stream", lambda *_args, **_kwargs: FakeStream())
    monkeypatch.setattr(qwenpaw_client, "record_trace", lambda **_kwargs: None)
    monkeypatch.setattr(qwenpaw_client, "record_audit", lambda **_kwargs: None)
    monkeypatch.setattr(
        QwenPawClient,
        "_stop_chat_for_session",
        lambda _self, session_id, agent_id: stopped.append((session_id, agent_id)),
    )

    result = QwenPawClient(base_url="http://qwenpaw", timeout=5).ask_for_image(
        "scene",
        "generate",
        session_id="postcard-scene-test",
    )

    assert result == reference
    assert stopped == [("postcard-scene-test", "scene")]


@pytest.mark.parametrize(
    ("reference", "preview_path"),
    [
        (
            "file://C:\\QwenPaw Test\\media\\scene.png",
            "C:/QwenPaw%20Test/media/scene.png",
        ),
        (
            PureWindowsPath("C:/QwenPaw Test/media/scene.png").as_uri(),
            "C:/QwenPaw%20Test/media/scene.png",
        ),
        (
            PurePosixPath("/Users/qwenpaw tester/.qwenpaw/media/scene.png").as_uri(),
            "/Users/qwenpaw%20tester/.qwenpaw/media/scene.png",
        ),
    ],
)
def test_download_media_uses_qwenpaw_preview_for_local_file(
    monkeypatch, reference, preview_path
):
    seen: dict[str, str] = {}

    class FakeResponse:
        status_code = 200
        text = ""
        content = b"image"

    def fake_get(url, **_kwargs):
        seen["url"] = url
        return FakeResponse()

    monkeypatch.setattr(qwenpaw_client.httpx, "get", fake_get)

    result = QwenPawClient(base_url="http://qwenpaw").download_media(reference)

    assert result == b"image"
    assert seen["url"] == f"http://qwenpaw/api/files/preview/{preview_path}"


def test_upload_media_targets_scene_agent(monkeypatch):
    seen: dict[str, object] = {}

    class FakeResponse:
        status_code = 200
        text = ""

        @staticmethod
        def json():
            return {"url": "/qwenpaw-test/media/postcard.jpg"}

    def fake_post(url, **kwargs):
        seen["url"] = url
        seen["headers"] = kwargs["headers"]
        seen["files"] = kwargs["files"]
        return FakeResponse()

    monkeypatch.setattr(qwenpaw_client.httpx, "post", fake_post)

    result = QwenPawClient(base_url="http://qwenpaw").upload_media(
        b"jpeg",
        filename="postcard.jpg",
        agent_id="scene",
    )

    assert result == "/qwenpaw-test/media/postcard.jpg"
    assert seen["url"] == "http://qwenpaw/api/console/upload"
    assert seen["headers"]["X-Agent-Id"] == "scene"
    assert seen["files"] == {"file": ("postcard.jpg", b"jpeg", "image/jpeg")}


def test_qwenpaw_scene_is_normalized_and_cached(monkeypatch, tmp_path):
    source = BytesIO()
    Image.new("RGB", (1200, 600), (80, 140, 160)).save(source, format="PNG")
    calls = {"ask": 0, "download": 0}
    reference = PurePosixPath("/qwenpaw-test/media/scene.png").as_uri()

    class FakeClient:
        def __init__(self, *, timeout):
            assert timeout >= 30

        def ask_for_image(self, agent_id, prompt, *, session_id):
            calls["ask"] += 1
            assert agent_id == "scene"
            assert "generate_image_qwen" in prompt
            assert session_id.startswith("postcard-scene-")
            return reference

        def download_media(self, reference):
            calls["download"] += 1
            assert reference == PurePosixPath("/qwenpaw-test/media/scene.png").as_uri()
            return source.getvalue()

    cache_dir = tmp_path / "postcard_scene_cache"
    cache_dir.mkdir()
    monkeypatch.setattr(scene_image, "_cache_dir", lambda: cache_dir)
    monkeypatch.setattr(scene_image.settings, "scene_agent_id", "scene")
    monkeypatch.setattr(scene_image, "QwenPawClient", FakeClient)

    first_jpeg, first_svg = scene_image.generate_ai_scene_via_qwenpaw(
        poi_name="大三巴牌坊",
        district="花王堂区",
        language="zh-CN",
    )
    second_jpeg, second_svg = scene_image.generate_ai_scene_via_qwenpaw(
        poi_name="大三巴牌坊",
        district="花王堂区",
        language="zh-CN",
    )

    assert first_svg is None
    assert second_svg is None
    assert first_jpeg is not None
    assert first_jpeg == second_jpeg
    assert calls == {"ask": 1, "download": 1}
    with Image.open(BytesIO(first_jpeg)) as image:
        assert image.size == (960, 720)
        assert image.format == "JPEG"


def test_qwenpaw_photo_style_uploads_scrubbed_reference(monkeypatch):
    output = BytesIO()
    Image.new("RGB", (800, 600), (120, 90, 70)).save(output, format="PNG")
    uploaded = "/qwenpaw-test/media/scrubbed.jpg"
    styled = PurePosixPath("/qwenpaw-test/media/styled.png").as_uri()

    class FakeClient:
        def __init__(self, *, timeout):
            assert timeout >= 30

        def upload_media(self, content, *, filename, agent_id):
            assert content == b"scrubbed"
            assert filename.startswith("postcard-edit-")
            assert filename.endswith(".jpg")
            assert agent_id == "scene"
            return uploaded

        def ask_for_image(self, agent_id, prompt, *, session_id):
            assert agent_id == "scene"
            assert "edit_image_qwen" in prompt
            assert uploaded in prompt
            assert "已模糊人脸必须继续保持模糊" in prompt
            assert session_id.startswith("postcard-edit-")
            return styled

        def download_media(self, reference):
            assert reference == styled
            return output.getvalue()

    monkeypatch.setattr(scene_image.settings, "postcard_ai_image_enabled", True)
    monkeypatch.setattr(scene_image.settings, "scene_agent_id", "scene")
    monkeypatch.setattr(scene_image, "QwenPawClient", FakeClient)

    result = scene_image.stylize_photo_via_qwenpaw(
        photo_jpeg=b"scrubbed",
        style="azulejo",
        poi_name="大三巴牌坊",
    )

    assert result is not None
    with Image.open(BytesIO(result)) as image:
        assert image.size == (960, 720)
        assert image.format == "JPEG"


def test_explicit_ai_scene_precedes_library(monkeypatch):
    monkeypatch.setattr(scene_image.settings, "postcard_ai_image_enabled", True)
    monkeypatch.setattr(
        scene_image,
        "generate_ai_scene_via_qwenpaw",
        lambda **_kwargs: (b"generated", None),
    )
    monkeypatch.setattr(
        scene_image,
        "load_pregenerated_svg",
        lambda *_args, **_kwargs: ("day", "<svg></svg>"),
    )

    source, jpeg, svg = scene_image.generate_ai_scene(
        poi_id="poi_0001",
        poi_name="大三巴牌坊",
        ai_scene=True,
    )

    assert (source, jpeg, svg) == ("ai", b"generated", None)
