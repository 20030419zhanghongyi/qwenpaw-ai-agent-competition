"""Generate a text-free StoryWalk bitmap through the QwenPaw Scene Agent."""

from __future__ import annotations

import argparse
from io import BytesIO
from pathlib import Path
from uuid import uuid4

from PIL import Image, ImageOps

from app.agents.qwenpaw_client import QwenPawClient
from app.core.config import settings


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--subject", required=True)
    parser.add_argument("--width", type=int, default=900)
    parser.add_argument("--height", type=int, default=1125)
    args = parser.parse_args()

    prompt = (
        "Load and strictly follow the gc-minimal-zine-poster skill. Call "
        "generate_image_qwen exactly once. Create a portrait editorial travel-zine "
        f"illustration of {args.subject}. Use a tactile cut-paper collage, subtle "
        "risograph grain, warm off-white paper, deep forest green, muted celadon, "
        "restrained ochre, vermilion and cobalt accents. The central prop must be "
        "immediately recognizable and fully visible, with generous negative space. "
        "No people or faces. Absolutely no text, Chinese characters, Latin letters, "
        "numbers, labels, signs, logos, captions, UI, borders, or watermarks anywhere "
        "in the image. The application renders all language-dependent text separately. "
        "Use size 1140*1472, n 1, prompt_extend true. Return only the generated image."
    )
    timeout = max(30.0, float(settings.postcard_ai_scene_timeout or 210.0))
    client = QwenPawClient(timeout=timeout)
    session_id = f"story-asset-{uuid4().hex}"
    reference = client.ask_for_image(
        settings.scene_agent_id or "scene",
        prompt,
        session_id=session_id,
    )
    raw = client.download_media(reference)
    image = Image.open(BytesIO(raw)).convert("RGB")
    image = ImageOps.fit(
        image,
        (args.width, args.height),
        method=Image.Resampling.LANCZOS,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    image.save(args.output, format="WEBP", quality=92, method=6)
    print(f"Saved Qwen story asset to {args.output} ({image.width}x{image.height})")


if __name__ == "__main__":
    main()
