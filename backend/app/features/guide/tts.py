"""QwenPaw-first TTS with private OSS delivery and direct-provider fallback."""

from __future__ import annotations

from datetime import timedelta
import logging
from pathlib import Path
import re
import tempfile
import time
from typing import Any
from uuid import uuid4

import httpx

from app.core.config import settings
from app.agents.qwenpaw_client import QwenPawClient, QwenPawError

logger = logging.getLogger("macau_storywalk.tts")

_LOCAL_AUDIO_DIR = Path(tempfile.gettempdir()) / "macau-storywalk-tts"
_LOCAL_AUDIO_FILE = re.compile(r"^[0-9a-f]{32}\.mp3$")

# Qwen3 TTS system voices: Cherry covers Mandarin/English/Portuguese.
# The product's Traditional Chinese mode is the Macau-facing Cantonese narration
# mode, so it must be accepted by the public UI contract as well as ``yue``.
VOICE_BY_LANGUAGE = {
    "zh-CN": "Cherry",
    "zh-TW": "Rocky",
    "yue": "Rocky",
    "en": "Cherry",
    "pt": "Cherry",
}


class TTSUnavailableError(RuntimeError):
    pass


def _require_oss_config() -> None:
    required = {
        "OSS_ENDPOINT": settings.oss_endpoint,
        "OSS_REGION": settings.oss_region,
        "OSS_BUCKET": settings.oss_bucket,
        "OSS_ACCESS_KEY_ID": settings.oss_access_key_id,
        "OSS_ACCESS_KEY_SECRET": settings.oss_access_key_secret,
    }
    missing = [name for name, value in required.items() if not value]
    if missing:
        raise TTSUnavailableError(f"TTS delivery is not configured ({', '.join(missing)})")


def _has_oss_config() -> bool:
    return all(
        (
            settings.oss_endpoint,
            settings.oss_region,
            settings.oss_bucket,
            settings.oss_access_key_id,
            settings.oss_access_key_secret,
        )
    )


def _local_delivery_allowed() -> bool:
    return settings.app_env.lower() in {"dev", "development", "test"}


def _cleanup_local_audio(*, max_age_seconds: int) -> None:
    if not _LOCAL_AUDIO_DIR.exists():
        return
    cutoff = time.time() - max_age_seconds
    for path in _LOCAL_AUDIO_DIR.glob("*.mp3"):
        try:
            if path.stat().st_mtime < cutoff:
                path.unlink()
        except OSError:
            logger.debug("Unable to clean local TTS file %s", path, exc_info=True)


def store_local_audio(audio: bytes) -> tuple[str, str]:
    """Store development audio temporarily and return its same-origin API URL."""
    _LOCAL_AUDIO_DIR.mkdir(parents=True, exist_ok=True)
    _cleanup_local_audio(max_age_seconds=settings.oss_signed_url_ttl_seconds)
    filename = f"{uuid4().hex}.mp3"
    (_LOCAL_AUDIO_DIR / filename).write_bytes(audio)
    return f"/api/v1/guide/tts/audio/{filename}", filename


def local_audio_path(filename: str) -> Path | None:
    """Resolve a generated local audio token without allowing path traversal."""
    if not _LOCAL_AUDIO_FILE.fullmatch(filename):
        return None
    path = _LOCAL_AUDIO_DIR / filename
    return path if path.is_file() else None


def _require_direct_provider_config() -> None:
    if not (settings.dashscope_api_key or settings.tts_api_key):
        raise TTSUnavailableError("DASHSCOPE_API_KEY or TTS_API_KEY is not configured")


def _audio_url(result: Any) -> str:
    if isinstance(result, dict):
        candidate = (result.get("output") or {}).get("audio_url") or result.get("audio_url")
    else:
        output = getattr(result, "output", None)
        candidate = getattr(output, "audio_url", None) if output is not None else None
    if not isinstance(candidate, str) or not candidate.startswith("http"):
        raise TTSUnavailableError("TTS provider returned no audio URL")
    return candidate


def synthesize_audio(text: str, language: str) -> tuple[bytes, str]:
    """Generate MP3 bytes through the DashScope HTTP Qwen3-TTS client."""
    _require_direct_provider_config()
    voice = VOICE_BY_LANGUAGE[language]
    api_key = settings.tts_api_key or settings.dashscope_api_key
    try:
        from dashscope.audio.http_tts.http_speech_synthesizer import HttpSpeechSynthesizer

        result = HttpSpeechSynthesizer.call(
            model=settings.qwen_tts_model,
            text=text,
            voice=voice,
            format="mp3",
            sample_rate=24000,
            stream=False,
            api_key=api_key,
        )
        download = httpx.get(_audio_url(result), timeout=30.0)
        download.raise_for_status()
    except TTSUnavailableError:
        raise
    except Exception as exc:  # noqa: BLE001
        raise TTSUnavailableError("TTS synthesis failed") from exc
    if not download.content:
        raise TTSUnavailableError("TTS provider returned empty audio")
    return download.content, voice


def upload_audio(audio: bytes, *, language: str) -> tuple[str, str]:
    """Upload an MP3 to private OSS and return its short-lived signed URL."""
    try:
        import alibabacloud_oss_v2 as oss

        credentials = oss.credentials.StaticCredentialsProvider(
            settings.oss_access_key_id, settings.oss_access_key_secret
        )
        config = oss.config.load_default()
        config.credentials_provider = credentials
        config.region = settings.oss_region
        config.endpoint = settings.oss_endpoint
        client = oss.Client(config)
        key = f"{settings.oss_audio_prefix.strip('/')}/{language}/{uuid4()}.mp3"
        client.put_object(oss.PutObjectRequest(bucket=settings.oss_bucket, key=key, body=audio))
        signed = client.presign(
            oss.GetObjectRequest(bucket=settings.oss_bucket, key=key),
            expires=timedelta(seconds=settings.oss_signed_url_ttl_seconds),
        )
        url = signed.url
    except Exception as exc:  # noqa: BLE001
        raise TTSUnavailableError("OSS audio upload failed") from exc
    return url, key


def _qwenpaw_tts_prompt(text: str, language: str) -> str:
    """Ask the guide agent to render an already-approved script verbatim."""
    return (
        "TTS_RENDER_REQUEST\n"
        "Use the synthesize_speech_qwen tool exactly once. Do not answer with JSON, "
        "do not rewrite, translate, summarize, or add to the script. Use language "
        f"`{language}` and synthesize this approved narration verbatim:\n---\n{text}\n---"
    )


def synthesize_audio_via_qwenpaw(text: str, language: str) -> tuple[bytes, str]:
    """Use the mounted QwenPaw TTS tool on the existing guide agent."""
    try:
        client = QwenPawClient()
        reference = client.ask_for_audio(
            settings.qwenpaw_tts_agent_id,
            _qwenpaw_tts_prompt(text, language),
            session_id=f"storywalk-tts-{uuid4()}",
        )
        audio = client.download_media(reference)
    except QwenPawError as exc:
        raise TTSUnavailableError(f"QwenPaw TTS tool unavailable: {exc}") from exc
    if not audio:
        raise TTSUnavailableError("QwenPaw TTS tool returned empty audio")
    return audio, VOICE_BY_LANGUAGE[language]


def synthesize_to_oss(text: str, language: str) -> dict[str, str | int]:
    use_oss = _has_oss_config()
    if not use_oss and not _local_delivery_allowed():
        _require_oss_config()
    if settings.qwenpaw_tts_enabled:
        try:
            audio, voice = synthesize_audio_via_qwenpaw(text, language)
        except TTSUnavailableError:
            if not settings.qwenpaw_tts_direct_fallback_enabled:
                raise
            logger.warning("QwenPaw TTS failed; using explicit direct-provider fallback")
            audio, voice = synthesize_audio(text, language)
    else:
        audio, voice = synthesize_audio(text, language)
    if use_oss:
        audio_url, object_key = upload_audio(audio, language=language)
    else:
        audio_url, object_key = store_local_audio(audio)
    return {
        "audio_url": audio_url,
        "object_key": object_key,
        "voice": voice,
        "content_type": "audio/mpeg",
        "expires_in": settings.oss_signed_url_ttl_seconds,
    }
