"""AMap walking-path behavior without making external network calls."""

from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete

from app.db.models import Poi
from app.db.session import SessionLocal
from app.features.routes import api as routes_api
from app.features.routes import walking
from app.features.routes.walking import AmapWalkingClient, WalkingPathError, build_walk_path
from app.main import app
from scripts.import_pois import PoiImportRow, upsert_pois

client = TestClient(app)
IDS = ["test_walk_a", "test_walk_b", "test_walk_c"]


class FakeWalkingClient:
    def segment(self, _origin, _destination):
        return {
            "distance": "120",
            "cost": {"duration": "95"},
            "steps": [{"polyline": "113.1,22.1;113.2,22.2"}],
        }


class FakeWalkingClientWithTransit(FakeWalkingClient):
    def segment(self, _origin, _destination):
        return {
            "distance": "600",
            "cost": {"duration": "420"},
            "steps": [{"polyline": "113.1,22.1;113.2,22.2"}],
        }

    def transit_options(self, _origin, _destination, *, city: str = "1852"):
        return [
            {
                "distance": "900",
                "segments": [
                    {
                        "bus": {
                            "buslines": [
                                {"name": "6B路(妈阁交通枢纽--山顶医院)", "type": "普通公交线路"},
                                {"name": "18路(妈阁--白鸽巢)", "type": "普通公交线路"},
                            ]
                        }
                    }
                ],
            }
        ]


@pytest.fixture(autouse=True)
def walking_pois():
    with SessionLocal() as session:
        session.execute(delete(Poi).where(Poi.poi_id.in_(IDS)))
        session.commit()
    now = datetime.now(timezone.utc)
    upsert_pois(
        [
            PoiImportRow(
                poi_id=poi_id,
                poi_name=poi_id,
                alias=None,
                address="Macau",
                longitude=113.5 + index * 0.001,
                latitude=22.1,
                category="test",
                source="pytest",
                created_at=now,
                updated_at=now,
            )
            for index, poi_id in enumerate(IDS)
        ]
    )
    yield
    with SessionLocal() as session:
        session.execute(delete(Poi).where(Poi.poi_id.in_(IDS)))
        session.commit()


def test_build_walk_path_aggregates_segments():
    with SessionLocal() as session:
        result = build_walk_path(IDS, session, client=FakeWalkingClient())
    assert result["total_walk_m"] == 240
    assert result["total_walk_min"] == 4
    assert [segment["from_poi_id"] for segment in result["segments"]] == IDS[:-1]
    assert all(segment["walk_min"] == 2 for segment in result["segments"])
    assert all(segment["bus_lines"] == [] for segment in result["segments"])


def test_build_walk_path_includes_amap_bus_lines():
    with SessionLocal() as session:
        result = build_walk_path(IDS[:2], session, client=FakeWalkingClientWithTransit())
    segment = result["segments"][0]
    assert segment["bus_lines"] == ["6B路", "18路"]
    assert {"kind": "walk", "label": "步行"} in segment["modes"]
    assert {"kind": "bus", "label": "6B路"} in segment["modes"]


def test_walk_path_api_contract_and_errors(monkeypatch):
    monkeypatch.setattr(
        routes_api,
        "build_walk_path",
        lambda poi_ids, _database: {"segments": [], "total_walk_m": 0, "total_walk_min": 0, "polyline": ""},
    )
    assert client.post("/api/v1/routes/walk-path", json={"poi_ids": IDS[:2]}).status_code == 200
    assert client.post("/api/v1/routes/walk-path", json={"poi_ids": [IDS[0]]}).status_code == 422
    assert client.post("/api/v1/routes/walk-path", json={"poi_ids": [IDS[0], IDS[0]]}).status_code == 422


def test_walking_client_requires_web_service_key():
    with pytest.raises(WalkingPathError, match="not configured"):
        AmapWalkingClient(api_key="").segment((113.5, 22.1), (113.6, 22.2))


def test_walking_client_requests_cost_and_polyline(monkeypatch):
    captured: dict = {}

    class Response:
        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict:
            return {
                "status": "1",
                "route": {"paths": [{"distance": "100", "cost": {"duration": "80"}, "steps": []}]},
            }

    def fake_get(_url, *, params, timeout):
        captured.update(params)
        assert timeout == 10.0
        return Response()

    monkeypatch.setattr(walking.httpx, "get", fake_get)
    AmapWalkingClient(api_key="test-key").segment((113.5, 22.1), (113.6, 22.2))

    assert captured["show_fields"] == "cost,polyline"
