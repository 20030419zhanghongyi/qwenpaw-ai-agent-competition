"""QwenPaw tool: approved text -> MP3 file in the QwenPaw media directory."""

from __future__ import annotations

import asyncio
import logging
import re
import time
from pathlib import Path
from typing import Any

import httpx
from agentscope.message import TextBlock
from agentscope.tool import ToolResponse
from qwenpaw.constant import DEFAULT_MEDIA_DIR
from qwenpaw.plugins import get_tool_config

logger = logging.getLogger(__name__)

_VOICE_BY_LANGUAGE = {
    "zh-CN": "Cherry",
    "zh-TW": "Rocky",
    "yue": "Rocky",
    "en": "Cherry",
    "pt": "Cherry",
}
_DEFAULT_MODEL = "qwen3-tts-flash"
_MAX_TEXT_LENGTH = 20_000
_SAFE_LANGUAGE = re.compile(r"^[a-zA-Z-]{2,10}$")


def _text_response(text: str) -> ToolResponse:
    return ToolResponse(content=[TextBlock(type="text", text=text)])


def _config() -> tuple[str, str, float]:
    config = get_tool_config("synthesize_speech_qwen") or {}
    api_key = str(config.get("api_key") or "").strip()
    model = str(config.get("model") or _DEFAULT_MODEL).strip()
    try:
        timeout = float(config.get("timeout") or 60)
    except (TypeError, ValueError):
        timeout = 60.0
    return api_key, model, min(max(timeout, 15.0), 180.0)


def _audio_url(result: Any) -> str:
    if isinstance(result, dict):
        candidate = (result.get("output") or {}).get("audio_url") or result.get("audio_url")
    else:
        output = getattr(result, "output", None)
        candidate = getattr(output, "audio_url", None) if output is not None else None
    if not isinstance(candidate, str) or not candidate.startswith(("http://", "https://")):
        raise ValueError("provider returned no audio URL")
    return candidate


def _synthesize(*, api_key: str, model: str, voice: str, text: str, timeout: float) -> bytes:
    from dashscope.audio.http_tts.http_speech_synthesizer import HttpSpeechSynthesizer

    result = HttpSpeechSynthesizer.call(
        model=model,
        text=text,
        voice=voice,
        format="mp3",
        sample_rate=24000,
        stream=False,
        api_key=api_key,
    )
    response = httpx.get(_audio_url(result), timeout=timeout)
    response.raise_for_status()
    if not response.content:
        raise ValueError("provider returned empty audio")
    return response.content


async def synthesize_speech_qwen(text: str, language: str = "zh-CN") -> ToolResponse:
    """Synthesize an approved narration script without rewriting its content.

    The tool deliberately accepts only language and text. Voice choice is fixed
    by product locale, keeping an agent from selecting an inconsistent persona.
    """
    script = str(text or "").strip()
    if not script:
        return _text_response("Error: text is required.")
    if len(script) > _MAX_TEXT_LENGTH:
        return _text_response(f"Error: text must be at most {_MAX_TEXT_LENGTH} characters.")
    if not _SAFE_LANGUAGE.fullmatch(language) or language not in _VOICE_BY_LANGUAGE:
        return _text_response("Error: unsupported language.")
    api_key, model, timeout = _config()
    if not api_key:
        return _text_response("Error: Tool not configured. Set its DashScope API key first.")

    voice = _VOICE_BY_LANGUAGE[language]
    try:
        audio = await asyncio.to_thread(
            _synthesize,
            api_key=api_key,
            model=model,
            voice=voice,
            text=script,
            timeout=timeout,
        )
        output_dir = Path(DEFAULT_MEDIA_DIR) / "qwen_tts"
        output_dir.mkdir(parents=True, exist_ok=True)
        path = output_dir / f"qwen_tts_{int(time.time() * 1000)}.mp3"
        await asyncio.to_thread(path.write_bytes, audio)
    except Exception as exc:  # noqa: BLE001 - tool errors must remain agent-visible
        logger.exception("Qwen TTS synthesis failed")
        return _text_response(f"Error: speech synthesis failed - {exc}")

    return _text_response(
        f"Audio ready. Language: {language}; Voice: {voice}; Model: {model}; "
        f"Saved to: {path}"
    )
