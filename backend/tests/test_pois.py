"""Database import and PostGIS query tests for POIs."""

from datetime import datetime, timezone

from fastapi.testclient import TestClient
from sqlalchemy import delete, func, select

from app.db.models import Poi
from app.db.session import SessionLocal
from app.main import app
from scripts.import_pois import PoiImportRow, upsert_pois

client = TestClient(app)
TEST_IDS = {"test_poi_near_a", "test_poi_near_b"}


def _rows() -> list[PoiImportRow]:
    now = datetime.now(timezone.utc)
    return [
        PoiImportRow(
            poi_id="test_poi_near_a",
            poi_name="Test Senado",
            alias=None,
            address="Macau",
            longitude=120.0,
            latitude=20.0,
            category="test",
            source="pytest",
            created_at=now,
            updated_at=now,
        ),
        PoiImportRow(
            poi_id="test_poi_near_b",
            poi_name="Test Nearby",
            alias="Nearby alias",
            address="Macau",
            longitude=120.0005,
            latitude=20.0005,
            category="test",
            source="pytest",
            created_at=now,
            updated_at=now,
        ),
    ]


def _clear_test_pois() -> None:
    with SessionLocal() as session:
        session.execute(delete(Poi).where(Poi.poi_id.in_(TEST_IDS)))
        session.commit()


def setup_function() -> None:
    _clear_test_pois()


def teardown_function() -> None:
    _clear_test_pois()


def test_import_count_and_idempotency():
    first = upsert_pois(_rows())
    second = upsert_pois(_rows())
    assert (first.rows_read, first.inserted, first.updated) == (2, 2, 0)
    assert (second.rows_read, second.inserted, second.updated) == (2, 0, 2)
    with SessionLocal() as session:
        statement = select(func.count()).select_from(Poi).where(Poi.poi_id.in_(TEST_IDS))
        count = session.scalar(statement)
        assert count == 2


def test_poi_detail_preserves_coordinates():
    upsert_pois(_rows())
    response = client.get("/api/v1/pois/test_poi_near_a")
    assert response.status_code == 200
    assert response.json()["longitude"] == 120.0
    assert response.json()["latitude"] == 20.0


def test_poi_list_reads_database_rows():
    upsert_pois(_rows())
    response = client.get("/api/v1/pois?category=test")
    assert response.status_code == 200
    assert {item["poi_id"] for item in response.json()} == TEST_IDS


def test_nearby_pois_uses_postgis_distance():
    upsert_pois(_rows())
    response = client.get(
        "/api/v1/pois/nearby",
        params={
            "longitude": 120.0,
            "latitude": 20.0,
            "radius_m": 200,
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert [item["poi_id"] for item in data[:2]] == [
        "test_poi_near_a",
        "test_poi_near_b",
    ]
    assert data[0]["distance_m"] < 0.01
    assert 0 < data[1]["distance_m"] < 200
