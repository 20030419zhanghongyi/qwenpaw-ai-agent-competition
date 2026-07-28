"""Non-streaming Qwen3 TTS plus private OSS delivery."""

from __future__ import annotations

from datetime import timedelta
import logging
from typing import Any
from uuid import uuid4

import httpx

from app.core.config import settings

logger = logging.getLogger("macau_storywalk.tts")

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


def _require_config() -> None:
    required = {
        "DASHSCOPE_API_KEY or TTS_API_KEY": settings.dashscope_api_key or settings.tts_api_key,
        "OSS_ENDPOINT": settings.oss_endpoint,
        "OSS_REGION": settings.oss_region,
        "OSS_BUCKET": settings.oss_bucket,
        "OSS_ACCESS_KEY_ID": settings.oss_access_key_id,
        "OSS_ACCESS_KEY_SECRET": settings.oss_access_key_secret,
    }
    missing = [name for name, value in required.items() if not value]
    if missing:
        raise TTSUnavailableError(f"TTS delivery is not configured ({', '.join(missing)})")


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


def synthesize_to_oss(text: str, language: str) -> dict[str, str | int]:
    _require_config()
    audio, voice = synthesize_audio(text, language)
    audio_url, object_key = upload_audio(audio, language=language)
    return {
        "audio_url": audio_url,
        "object_key": object_key,
        "voice": voice,
        "content_type": "audio/mpeg",
        "expires_in": settings.oss_signed_url_ttl_seconds,
    }
