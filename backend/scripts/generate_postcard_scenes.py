#!/usr/bin/env python3
"""Collect postcard scene assets for POIs.

**Current focus (phase 1):** ``--research-only`` — search the web and save
reference photos (``_ref.jpg``) + landmark briefs. Do **not** batch-draw SVGs yet.

Phase 2 (later): QwenPaw ``scene`` agent draws morning/midday/dusk/night SVG
from each reference photo.

Checkpoint (resumable)::

    data/postcard_scenes/_checkpoint.json

Examples::

    # Phase A — search + download refs only (checkpoint), no SVG yet
    python scripts/generate_postcard_scenes.py --only-routed --research-only

    # Phase B — continue: draw SVGs with scene agent
    python scripts/generate_postcard_scenes.py --only-routed --agent scene

    python scripts/generate_postcard_scenes.py --poi poi_senado --force --force-research
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
import time
from pathlib import Path

_BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(_BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(_BACKEND_ROOT))

from app.agents.qwenpaw_client import QwenPawClient, QwenPawError  # noqa: E402
from app.core.config import settings  # noqa: E402
from app.features.postcards.scene_checkpoint import (  # noqa: E402
    load_checkpoint,
    mark_research,
    mark_slot,
    research_summary,
    save_checkpoint,
)
from app.features.postcards.scene_image import _sanitize_svg  # noqa: E402
from app.features.postcards.scene_library import (  # noqa: E402
    TIME_SLOTS,
    build_slot_prompt,
    scene_path,
    scenes_root,
)
from app.features.postcards.scene_research import research_poi  # noqa: E402

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)
logger = logging.getLogger("generate_postcard_scenes")

DEFAULT_AGENT = "scene"


def _load_pois() -> list[dict]:
    path = settings.data_dir / "pois.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    items = payload.get("pois") if isinstance(payload, dict) else payload
    if not isinstance(items, list):
        raise SystemExit(f"unexpected pois.json shape: {path}")
    return [p for p in items if isinstance(p, dict) and p.get("id")]


def _routed_poi_ids() -> set[str]:
    ids: set[str] = set()
    for name in ("routes.json", "route_templates.json", "ports.json"):
        path = settings.data_dir / name
        if not path.is_file():
            continue
        payload = json.loads(path.read_text(encoding="utf-8"))
        if name == "ports.json":
            ports = payload.get("ports") if isinstance(payload, dict) else payload
            for port in ports or []:
                pid = port.get("poi_id") or port.get("id")
                if pid:
                    ids.add(str(pid))
            continue
        routes = payload if isinstance(payload, list) else (
            payload.get("routes") or payload.get("templates") or []
        )
        for route in routes:
            for node in route.get("nodes") or route.get("stops") or []:
                if isinstance(node, str):
                    ids.add(node)
                else:
                    pid = node.get("poi_id") or node.get("id")
                    if pid:
                        ids.add(str(pid))
            for pid in route.get("poi_ids") or []:
                ids.add(str(pid))
    return ids


def _parse_slots(raw: str | None) -> tuple[str, ...]:
    if not raw:
        return TIME_SLOTS
    slots = tuple(s.strip() for s in raw.split(",") if s.strip())
    bad = [s for s in slots if s not in TIME_SLOTS]
    if bad:
        raise SystemExit(f"unknown slots {bad}; choose from {TIME_SLOTS}")
    return slots


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--limit", type=int, default=0, help="Max POIs to process (0=all)")
    parser.add_argument("--poi", action="append", default=[], help="Only these poi_id(s)")
    parser.add_argument(
        "--only-routed",
        action="store_true",
        help="Only POIs appearing in routes/templates/ports",
    )
    parser.add_argument(
        "--slots",
        default="",
        help="Comma list: morning,midday,dusk,night (default=all)",
    )
    parser.add_argument("--force", action="store_true", help="Overwrite existing SVG")
    parser.add_argument(
        "--force-research",
        action="store_true",
        help="Re-fetch reference photo / brief even if cached",
    )
    parser.add_argument(
        "--research-only",
        action="store_true",
        help="Phase A: search + download refs + write checkpoint; do not call QwenPaw",
    )
    parser.add_argument(
        "--no-web",
        action="store_true",
        help="Skip Openverse/web; use only local pois.json landmarks",
    )
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--sleep", type=float, default=1.0)
    parser.add_argument("--timeout", type=float, default=150.0)
    parser.add_argument(
        "--agent",
        default=DEFAULT_AGENT,
        help="QwenPaw agent id (default: scene)",
    )
    args = parser.parse_args()

    slots = _parse_slots(args.slots or None)
    pois = _load_pois()
    if args.poi:
        allow = set(args.poi)
        pois = [p for p in pois if p["id"] in allow]
    elif args.only_routed:
        allow = _routed_poi_ids()
        pois = [p for p in pois if p["id"] in allow]
    if args.limit and args.limit > 0:
        pois = pois[: args.limit]

    root = scenes_root()
    root.mkdir(parents=True, exist_ok=True)
    checkpoint = load_checkpoint()
    checkpoint["agent_id"] = args.agent

    logger.info(
        "plan pois=%s slots=%s root=%s research_only=%s agent=%s dry_run=%s",
        len(pois),
        slots,
        root,
        args.research_only,
        args.agent,
        args.dry_run,
    )

    client = None
    if not args.dry_run and not args.research_only:
        client = QwenPawClient(timeout=args.timeout)

    done = skipped = failed = researched = 0

    for index, poi in enumerate(pois, start=1):
        poi_id = str(poi["id"])
        name = str(poi.get("name_zh") or poi.get("name_en") or poi_id)
        district = str(poi.get("district") or "") or None

        if args.dry_run:
            logger.info("[%s/%s] dry-run %s", index, len(pois), poi_id)
            done += 1
            continue

        try:
            research = research_poi(
                poi,
                force=args.force_research,
                use_web=not args.no_web,
            )
        except Exception as exc:  # noqa: BLE001
            failed += 1
            logger.warning("fail research %s: %s", poi_id, exc)
            continue

        mark_research(
            checkpoint,
            poi_id=poi_id,
            name_zh=name,
            has_ref=bool(research.ref_image_path),
            landmarks_chars=len(research.landmarks or ""),
            sources=list(research.sources or []),
        )
        researched += 1
        logger.info(
            "[%s/%s] researched %s ref=%s",
            index,
            len(pois),
            poi_id,
            "yes" if research.ref_image_path else "no",
        )

        if args.research_only:
            save_checkpoint(checkpoint)
            continue

        assert client is not None
        pending_slots = [
            slot
            for slot in slots
            if args.force or not scene_path(poi_id, slot).is_file()
        ]
        if not pending_slots:
            skipped += len(slots)
            for slot in slots:
                mark_slot(checkpoint, poi_id=poi_id, slot=slot, status="done")
            save_checkpoint(checkpoint)
            logger.info("[%s/%s] skip all slots exist %s", index, len(pois), poi_id)
            continue

        for slot in pending_slots:
            prompt = build_slot_prompt(
                poi_name=name,
                district=district,
                slot=slot,
                language="zh-CN",
                landmarks=research.landmarks,
                ref_image_path=research.ref_image_path,
            )
            try:
                raw = client.ask(
                    args.agent,
                    prompt,
                    session_id=f"scene-{poi_id}-{slot}-{int(time.time() * 1000)}",
                )
            except QwenPawError as exc:
                failed += 1
                mark_slot(checkpoint, poi_id=poi_id, slot=slot, status="failed")
                save_checkpoint(checkpoint)
                logger.warning("fail %s/%s: %s", poi_id, slot, exc)
                continue
            svg = _sanitize_svg(raw)
            path = scene_path(poi_id, slot)
            # Some agents write the SVG via tools instead of returning it in chat text.
            if not svg and path.is_file():
                try:
                    svg = _sanitize_svg(path.read_text(encoding="utf-8"))
                except OSError:
                    svg = None
            if not svg:
                failed += 1
                mark_slot(checkpoint, poi_id=poi_id, slot=slot, status="failed")
                save_checkpoint(checkpoint)
                snippet = " ".join((raw or "").split())[:180]
                logger.warning(
                    "fail %s/%s: no usable SVG (reply_len=%s head=%r)",
                    poi_id,
                    slot,
                    len(raw or ""),
                    snippet,
                )
                continue
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(svg, encoding="utf-8")
            mark_slot(checkpoint, poi_id=poi_id, slot=slot, status="done")
            save_checkpoint(checkpoint)
            done += 1
            logger.info("ok %s/%s (%s bytes)", poi_id, slot, path.stat().st_size)
            if args.sleep > 0:
                time.sleep(args.sleep)

    save_checkpoint(checkpoint)
    summary = research_summary(checkpoint)
    logger.info(
        "finished researched=%s done=%s skipped=%s failed=%s checkpoint=%s",
        researched,
        done,
        skipped,
        failed,
        summary,
    )
    if args.research_only:
        logger.info(
            "CHECKPOINT ready at %s — next: run without --research-only "
            "(requires QwenPaw scene agent)",
            scenes_root() / "_checkpoint.json",
        )
    return 1 if failed and not done and not args.research_only else 0


if __name__ == "__main__":
    raise SystemExit(main())
