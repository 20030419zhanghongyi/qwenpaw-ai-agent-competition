#!/usr/bin/env python3
"""离线脱敏自检 CLI：python scripts/scrub_image.py a.jpg [b.jpg ...] → *.scrubbed.jpg

规范实现在 ``backend/app/tools/scrub.py``（可被后端 import）；本脚本只是个薄 CLI，
把 repo 根下的 backend 加进 sys.path 后调用同一个 ``scrub``，便于不上传、不联网地
肉眼核对 EXIF 是否清掉、人脸是否糊掉。
"""

from __future__ import annotations

import sys
from pathlib import Path

# scripts/ → parents[1] = repo 根 → backend/ 在 sys.path 上，app.tools.scrub 可 import
_REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_REPO_ROOT / "backend"))

from app.tools.scrub import scrub  # noqa: E402


def main(argv: list[str]) -> int:
    if not argv:
        print(__doc__)
        return 1
    for path in argv:
        src = Path(path)
        if not src.is_file():
            print(f"skip（找不到）：{src}", file=sys.stderr)
            continue
        out = src.with_suffix(".scrubbed.jpg")
        out.write_bytes(scrub(src.read_bytes()))
        print(f"{src} -> {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
