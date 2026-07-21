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
                                {
                                    "name": "6B路(妈阁交通枢纽--山顶医院)",
                                    "type": "普通公交线路",
                                    "departure_stop": {"name": "妈阁交通枢纽"},
                                    "arrival_stop": {"name": "亚婆井前地"},
                                },
                                {
                                    "name": "18路(妈阁--白鸽巢)",
                                    "type": "普通公交线路",
                                    "departure_stop": {"name": "妈阁交通枢纽"},
                                    "arrival_stop": {"name": "亚婆井前地"},
                                },
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
    assert segment["bus_from_stop"] == "妈阁交通枢纽"
    assert segment["bus_to_stop"] == "亚婆井前地"
    # 420s walk ≈ 7 min → still walk-primary; bus listed as alternative.
    assert segment["preferred_mode"] == "walk"
    assert {"kind": "walk", "label": "步行"} in segment["modes"]
    assert {"kind": "bus", "label": "6B路"} in segment["modes"]


class FakeLongWalkWithTransit(FakeWalkingClientWithTransit):
    def segment(self, _origin, _destination):
        return {
            "distance": "1800",
            "cost": {"duration": "1200"},  # 20 min → prefer bus
            "steps": [{"polyline": "113.1,22.1;113.2,22.2"}],
        }


def test_build_walk_path_prefers_bus_when_walk_over_15_min():
    with SessionLocal() as session:
        result = build_walk_path(IDS[:2], session, client=FakeLongWalkWithTransit())
    segment = result["segments"][0]
    assert segment["walk_min"] >= 15
    assert segment["preferred_mode"] == "bus"
    assert segment["modes"][0]["kind"] == "bus"
    assert any(m["kind"] == "walk" for m in segment["modes"])


class FakeLongWalkNoTransit(FakeWalkingClient):
    def segment(self, _origin, _destination):
        return {
            "distance": "5700",
            "cost": {"duration": "4320"},  # 72 min
            "steps": [{"polyline": "113.1,22.1;113.2,22.2"}],
        }

    def transit_options(self, _origin, _destination, *, city: str = "1852", city2: str | None = None):
        return []


def test_long_hop_without_amap_lines_still_prefers_bus_fallback():
    with SessionLocal() as session:
        result = build_walk_path(IDS[:2], session, client=FakeLongWalkNoTransit())
    segment = result["segments"][0]
    assert segment["walk_min"] >= 15
    assert segment["preferred_mode"] == "bus"
    assert "建议乘巴士" in segment["bus_lines"][0]
    assert segment["modes"][0]["kind"] == "bus"


class FakeWalkFailsButTransitWorks:
    """Walking throws; transit still returns real lines (full-itinerary soft-fail case)."""

    def segment(self, _origin, _destination):
        raise WalkingPathError("AMap walking service rejected the route request")

    def transit_options_resilient(self, _origin, _destination):
        return [
            {
                "distance": "6200",
                "segments": [
                    {
                        "bus": {
                            "buslines": [
                                {
                                    "name": "新濠影汇穿梭巴士(横琴澳方口岸--新濠影汇)",
                                    "departure_stop": {"name": "横琴澳方口岸"},
                                    "arrival_stop": {"name": "连贯公路/新濠影汇"},
                                }
                            ]
                        }
                    },
                    {
                        "bus": {
                            "buslines": [
                                {
                                    "name": "26A路(连贯公路/新濠影汇--新马路/华侨)",
                                    "departure_stop": {"name": "连贯公路/新濠影汇"},
                                    "arrival_stop": {"name": "新马路/华侨"},
                                }
                            ]
                        }
                    },
                ],
            },
            {
                "distance": "6400",
                "segments": [
                    {
                        "bus": {
                            "buslines": [
                                {
                                    "name": "25B路(横琴澳方口岸--水坑尾/天神巷)",
                                    "departure_stop": {"name": "横琴澳方口岸"},
                                    "arrival_stop": {"name": "水坑尾/天神巷"},
                                }
                            ]
                        }
                    }
                ],
            },
        ]


def test_walking_failure_still_returns_amap_bus_lines():
    # Port → heritage distances so haversine estimate clears the 15 min bus gate.
    far_ids = ["test_walk_port", "test_walk_heritage"]
    now = datetime.now(timezone.utc)
    with SessionLocal() as session:
        session.execute(delete(Poi).where(Poi.poi_id.in_(far_ids)))
        session.commit()
    upsert_pois(
        [
            PoiImportRow(
                poi_id="test_walk_port",
                poi_name="hengqin",
                alias=None,
                address="Hengqin",
                longitude=113.5476,
                latitude=22.1398,
                category="test",
                source="pytest",
                created_at=now,
                updated_at=now,
            ),
            PoiImportRow(
                poi_id="test_walk_heritage",
                poi_name="senado",
                alias=None,
                address="Macau",
                longitude=113.545322,
                latitude=22.191104,
                category="test",
                source="pytest",
                created_at=now,
                updated_at=now,
            ),
        ]
    )
    try:
        with SessionLocal() as session:
            result = build_walk_path(far_ids, session, client=FakeWalkFailsButTransitWorks())
        assert len(result["segments"]) == 1
        segment = result["segments"][0]
        assert segment["walk_m"] > 3000
        assert segment["walk_min"] >= 15
        assert segment["polyline"] == ""
        assert segment["preferred_mode"] == "bus"
        assert segment["bus_lines"][0] == "新濠影汇穿梭巴士 → 26A路"
        assert "25B路" in segment["bus_lines"]
        assert "建议乘巴士" not in "".join(segment["bus_lines"])
        assert segment["bus_from_stop"] == "横琴澳方口岸"
        assert segment["bus_to_stop"] == "新马路/华侨"
    finally:
        with SessionLocal() as session:
            session.execute(delete(Poi).where(Poi.poi_id.in_(far_ids)))
            session.commit()


def test_multi_hop_continues_after_one_walking_failure():
    """One bad hop must not abort later segments."""

    class MixedClient(FakeWalkingClientWithTransit):
        def __init__(self) -> None:
            self.calls = 0

        def segment(self, _origin, _destination):
            self.calls += 1
            if self.calls == 1:
                raise WalkingPathError("QPS")
            return {
                "distance": "120",
                "cost": {"duration": "95"},
                "steps": [{"polyline": "113.1,22.1;113.2,22.2"}],
            }

        def transit_options_resilient(self, _origin, _destination):
            return []

    fake = MixedClient()
    with SessionLocal() as session:
        result = build_walk_path(IDS, session, client=fake)
    assert len(result["segments"]) == 2
    assert result["segments"][0]["polyline"] == ""
    assert result["segments"][1]["walk_m"] == 120
    assert result["segments"][1]["polyline"]


def test_walk_path_api_contract_and_errors(monkeypatch):
    monkeypatch.setattr(
        routes_api,
        "build_walk_path",
        lambda poi_ids, _database: {"segments": [], "total_walk_m": 0, "total_walk_min": 0, "polyline": ""},
    )
    assert client.post("/api/v1/routes/walk-path", json={"poi_ids": IDS[:2]}).status_code == 200
    assert client.post("/api/v1/routes/walk-path", json={"poi_ids": [IDS[0]]}).status_code == 422
    # Consecutive duplicates are invalid; same entry/exit port is not.
    assert client.post("/api/v1/routes/walk-path", json={"poi_ids": [IDS[0], IDS[0]]}).status_code == 422
    assert (
        client.post(
            "/api/v1/routes/walk-path",
            json={"poi_ids": [IDS[0], IDS[1], IDS[0]]},
        ).status_code
        == 200
    )


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
