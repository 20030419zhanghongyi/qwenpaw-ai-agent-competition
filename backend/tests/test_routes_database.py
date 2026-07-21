"""Database persistence and canonical-ID tests for route templates."""

import json
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import func, select

from app.db.models import Poi, RouteTemplate, RouteTemplateStop
from app.db.session import SessionLocal
from app.main import app
from scripts.import_routes import import_route_file

ROUTES_SOURCE = Path(__file__).resolve().parents[2] / "data" / "routes.json"
ROUTES_PAYLOAD = json.loads(ROUTES_SOURCE.read_text(encoding="utf-8"))
EXPECTED_TEMPLATES = ROUTES_PAYLOAD["routes"]
EXPECTED_TEMPLATE_COUNT = len(EXPECTED_TEMPLATES)
EXPECTED_STOP_COUNT = sum(len(route["nodes"]) for route in EXPECTED_TEMPLATES)
client = TestClient(app)


def test_route_import_is_idempotent_and_writes_database():
    first = import_route_file(ROUTES_SOURCE)
    second = import_route_file(ROUTES_SOURCE)
    assert first.templates_read == second.templates_read == EXPECTED_TEMPLATE_COUNT
    assert first.stops_written == second.stops_written == EXPECTED_STOP_COUNT
    assert first.legacy_ids_converted == second.legacy_ids_converted == 48
    assert second.inserted == 0
    assert second.updated == EXPECTED_TEMPLATE_COUNT
    with SessionLocal() as session:
        assert (
            session.scalar(select(func.count()).select_from(RouteTemplate))
            == EXPECTED_TEMPLATE_COUNT
        )
        assert (
            session.scalar(select(func.count()).select_from(RouteTemplateStop))
            == EXPECTED_STOP_COUNT
        )


def test_route_stops_preserve_order_and_reference_canonical_pois():
    with SessionLocal() as session:
        stops = session.scalars(
            select(RouteTemplateStop)
            .where(RouteTemplateStop.route_template_id == "photo_halfday")
            .order_by(RouteTemplateStop.stop_order)
        ).all()
        assert [stop.stop_order for stop in stops] == [1, 2, 3, 4, 5]
        assert [stop.poi_id for stop in stops] == [
            "poi_0002",
            "poi_0001",
            "poi_0003",
            "poi_0018",
            "poi_0030",
        ]
        assert all(session.get(Poi, stop.poi_id) is not None for stop in stops)


def test_route_apis_return_database_templates_and_match_with_canonical_ids():
    routes = client.get("/api/v1/routes")
    detail = client.get("/api/v1/routes/photo_halfday")
    match = client.post(
        "/api/v1/routes/match",
        json={
            "duration": "half-day",
            "interests": ["photo"],
            "travel_type": ["solo"],
            "physical": [],
            "language": "zh-CN",
        },
    )
    assert routes.status_code == detail.status_code == match.status_code == 200
    assert len(routes.json()) == EXPECTED_TEMPLATE_COUNT
    assert detail.json()["id"] == "photo_halfday"
    assert all(
        node["poi_id"].startswith("poi_0") for node in detail.json()["nodes"]
    )
    assert match.json()["matches"]
