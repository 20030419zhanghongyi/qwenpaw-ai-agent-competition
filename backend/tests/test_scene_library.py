"""Tests for postcard time-of-day scene library."""

from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from app.features.postcards.scene_library import (
    load_pregenerated_svg,
    slot_for_datetime,
)


MACAU = ZoneInfo("Asia/Macau")


def test_slot_for_datetime_buckets():
    assert slot_for_datetime(datetime(2026, 7, 21, 7, 0, tzinfo=MACAU)) == "morning"
    assert slot_for_datetime(datetime(2026, 7, 21, 12, 30, tzinfo=MACAU)) == "midday"
    assert slot_for_datetime(datetime(2026, 7, 21, 17, 0, tzinfo=MACAU)) == "dusk"
    assert slot_for_datetime(datetime(2026, 7, 21, 21, 0, tzinfo=MACAU)) == "night"
    assert slot_for_datetime(datetime(2026, 7, 21, 2, 0, tzinfo=MACAU)) == "night"


def test_load_pregenerated_prefers_matching_slot(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "app.features.postcards.scene_library.scenes_root",
        lambda: tmp_path,
    )
    poi = "poi_port_hengqin"
    dusk = tmp_path / poi / "dusk.svg"
    dusk.parent.mkdir(parents=True)
    dusk.write_text(
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 960 720">'
        '<rect width="960" height="720" fill="#c47a4a"/></svg>',
        encoding="utf-8",
    )
    morning = tmp_path / poi / "morning.svg"
    morning.write_text(
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 960 720">'
        '<rect width="960" height="720" fill="#7eb6c9"/></svg>',
        encoding="utf-8",
    )

    hit = load_pregenerated_svg(
        poi, when=datetime(2026, 7, 21, 18, 0, tzinfo=MACAU)
    )
    assert hit is not None
    slot, svg = hit
    assert slot == "dusk"
    assert "#c47a4a" in svg


def test_load_pregenerated_falls_back_to_neighbor(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "app.features.postcards.scene_library.scenes_root",
        lambda: tmp_path,
    )
    poi = "poi_0001"
    path = tmp_path / poi / "midday.svg"
    path.parent.mkdir(parents=True)
    path.write_text(
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 10 10"><rect width="10" height="10"/></svg>',
        encoding="utf-8",
    )
    # Ask for night; only midday exists → neighbor fallback.
    hit = load_pregenerated_svg(poi, when=datetime(2026, 7, 21, 22, 0, tzinfo=MACAU))
    assert hit is not None
    assert hit[0] == "midday"


def test_postcard_uses_library_scene_over_placeholder(monkeypatch, tmp_path):
    from fastapi.testclient import TestClient

    from app.features.trips.store import trip_store
    from app.main import app

    client = TestClient(app)
    trip_store.clear()

    monkeypatch.setattr(
        "app.features.postcards.scene_library.scenes_root",
        lambda: tmp_path,
    )
    monkeypatch.setattr("app.features.postcards.service._agent_caption", lambda *_: None)

    created = client.post(
        "/api/v1/trips", json={"user_id": "lib-user", "route_id": "photo_halfday"}
    ).json()
    trip_id = created["trip"]["trip_id"]
    poi_id = created["trip"]["stop_poi_ids"][0]
    assert client.post(f"/api/v1/trips/{trip_id}/checkins", json={"poi_id": poi_id}).status_code == 200

    svg = (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 960 720">'
        '<rect width="960" height="720" fill="#224466"/></svg>'
    )
    # Write all slots so whichever wall-clock bucket wins, library hits.
    for slot in ("morning", "midday", "dusk", "night"):
        path = Path(tmp_path) / poi_id / f"{slot}.svg"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(svg, encoding="utf-8")

    response = client.post(
        f"/api/v1/trips/{trip_id}/postcards",
        data={"poi_id": poi_id, "language": "zh-CN"},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["scene_source"] == "library"
    image = client.get(data["image_url"])
    assert b'data-scene-source="library"' in image.content
    assert b"#224466" in image.content

    trip_store.clear()
