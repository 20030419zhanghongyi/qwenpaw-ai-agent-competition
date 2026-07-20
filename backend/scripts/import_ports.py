"""Upsert border-crossing ports from data/ports.json into PostgreSQL."""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = BACKEND_ROOT.parent
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from sqlalchemy import func  # noqa: E402
from sqlalchemy.dialects.postgresql import insert  # noqa: E402

from app.db.models import Poi  # noqa: E402
from app.db.session import SessionLocal  # noqa: E402


def upsert_ports(ports_path: Path | None = None) -> tuple[int, int]:
    path = ports_path or (REPO_ROOT / "data" / "ports.json")
    payload = json.loads(path.read_text(encoding="utf-8"))
    ports = payload.get("ports") or []
    now = datetime.now(timezone.utc)
    inserted = updated = 0
    with SessionLocal() as session:
        for port in ports:
            poi_id = str(port["poi_id"])
            lng = float(port["lng"])
            lat = float(port["lat"])
            location = func.ST_SetSRID(func.ST_MakePoint(lng, lat), 4326)
            values = {
                "poi_id": poi_id,
                "poi_name": port["name_zh"],
                "alias": port.get("alias") or None,
                "address": port.get("address") or "",
                "longitude": lng,
                "latitude": lat,
                "category": port.get("amap_type") or "交通设施服务;过境口岸;口岸",
                "source": "ports.json",
                "location": location,
                "created_at": now,
                "updated_at": now,
            }
            stmt = insert(Poi).values(**values)
            stmt = stmt.on_conflict_do_update(
                index_elements=[Poi.poi_id],
                set_={
                    "poi_name": stmt.excluded.poi_name,
                    "alias": stmt.excluded.alias,
                    "address": stmt.excluded.address,
                    "longitude": stmt.excluded.longitude,
                    "latitude": stmt.excluded.latitude,
                    "category": stmt.excluded.category,
                    "source": stmt.excluded.source,
                    "location": stmt.excluded.location,
                    "updated_at": now,
                },
            )
            result = session.execute(stmt)
            # rowcount is 1 for insert or update on PG
            if result.rowcount:
                # Heuristic: treat existing rows as updates when source was already set
                existing = session.get(Poi, poi_id)
                if existing and existing.source == "ports.json":
                    updated += 1
                else:
                    inserted += 1
        session.commit()
    return inserted, updated


if __name__ == "__main__":
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else None
    ins, upd = upsert_ports(path)
    print(f"ports upserted insert≈{ins} update≈{upd}")
