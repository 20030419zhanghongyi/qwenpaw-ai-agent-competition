"""Qwen TTS Tool Plugin entry point."""

import importlib.util
import logging
import os

from qwenpaw.plugins.api import PluginApi

logger = logging.getLogger(__name__)
_PLUGIN_DIR = os.path.dirname(os.path.abspath(__file__))


def _load_tool_module():
    path = os.path.join(_PLUGIN_DIR, "qwen_tts_tool.py")
    spec = importlib.util.spec_from_file_location("qwen_tts_tool", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("Unable to load qwen_tts_tool.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class QwenTtsToolPlugin:
    """Register the audio-delivery tool for explicitly approved narration."""

    def register(self, api: PluginApi):
        tool = _load_tool_module()
        api.register_tool(
            tool_name="synthesize_speech_qwen",
            tool_func=tool.synthesize_speech_qwen,
            description=(
                "Synthesize approved narration text into an MP3. "
                "Do not rewrite or expand the supplied text."
            ),
            icon="🔊",
        )
        logger.info("Qwen TTS tool plugin registered")


plugin = QwenTtsToolPlugin()
