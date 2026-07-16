"""Database foundation tests using an isolated PostgreSQL test database."""

from collections.abc import Iterator
from pathlib import Path

import psycopg
import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from psycopg import sql
from sqlalchemy import CheckConstraint, UniqueConstraint, inspect, text
from sqlalchemy.engine import make_url

from app.api import health as health_api
from app.core.config import Settings, settings
from app.db import models  # noqa: F401 - registers ORM tables
from app.db.base import Base
from app.db.health import ping_database
from app.db.models import (
    AuditEvent,
    Checkin,
    Favorite,
    RouteTemplate,
    RouteTemplateStop,
    Trip,
    TripFeedback,
    TripStop,
    User,
)
from app.db.session import SessionLocal, build_engine, engine
from app.main import app

BACKEND_ROOT = Path(__file__).resolve().parents[1]
TEST_DATABASE_NAME = "qwenpaw_test"
EXPECTED_TABLES = {
    "audit_events",
    "users",
    "trips",
    "trip_stops",
    "checkins",
    "favorites",
    "trip_feedback",
    "pois",
    "route_templates",
    "route_template_stops",
}
client = TestClient(app)


def _admin_connection():
    url = make_url(settings.database_url)
    return psycopg.connect(
        host=url.host,
        port=url.port,
        dbname=url.database,
        user=url.username,
        password=url.password,
        autocommit=True,
    )


@pytest.fixture(scope="module")
def test_database_url() -> Iterator[str]:
    with _admin_connection() as connection:
        connection.execute(
            sql.SQL("DROP DATABASE IF EXISTS {} WITH (FORCE)").format(
                sql.Identifier(TEST_DATABASE_NAME)
            )
        )
        connection.execute(
            sql.SQL("CREATE DATABASE {}").format(sql.Identifier(TEST_DATABASE_NAME))
        )

    url = make_url(settings.database_url).set(database=TEST_DATABASE_NAME)
    try:
        yield url.render_as_string(hide_password=False)
    finally:
        with _admin_connection() as connection:
            connection.execute(
                sql.SQL("DROP DATABASE IF EXISTS {} WITH (FORCE)").format(
                    sql.Identifier(TEST_DATABASE_NAME)
                )
            )


def _alembic_config(database_url: str) -> Config:
    config = Config(str(BACKEND_ROOT / "alembic.ini"))
    config.set_main_option("script_location", str(BACKEND_ROOT / "alembic"))
    config.set_main_option("sqlalchemy.url", database_url)
    return config


def _unique_constraint_names(table) -> set[str | None]:
    return {
        constraint.name
        for constraint in table.constraints
        if isinstance(constraint, UniqueConstraint)
    }


def test_settings_exposes_database_configuration():
    configured = Settings(_env_file=None)
    assert configured.database_url.startswith("postgresql+psycopg://")
    assert configured.db_echo is False


def test_engine_and_session_factory_are_synchronous():
    assert engine.dialect.name == "postgresql"
    assert SessionLocal.kw["bind"] is engine
    assert SessionLocal.kw["autoflush"] is False


def test_metadata_contains_core_tables():
    assert set(Base.metadata.tables) == EXPECTED_TABLES


def test_audit_event_table_columns():
    assert {"event_id", "kind", "status", "subject_hash", "metadata_json", "created_at"} <= set(
        AuditEvent.__table__.columns.keys()
    )


def test_users_table_columns():
    expected = {
        "id",
        "language",
        "travel_type",
        "duration_minutes",
        "interests",
        "created_at",
        "updated_at",
    }
    assert expected <= set(User.__table__.columns.keys())


def test_trips_user_foreign_key():
    foreign_key = next(iter(Trip.__table__.c.user_id.foreign_keys))
    assert foreign_key.target_fullname == "users.id"


def test_trip_stops_order_unique_constraint():
    assert "uq_trip_stops_trip_order" in _unique_constraint_names(TripStop.__table__)


def test_checkins_unique_constraint():
    assert "uq_checkins_trip_poi" in _unique_constraint_names(Checkin.__table__)


def test_favorites_unique_constraint():
    assert "uq_favorites_user_poi" in _unique_constraint_names(Favorite.__table__)


def test_trip_feedback_trip_unique_constraint():
    assert "uq_trip_feedback_trip" in _unique_constraint_names(TripFeedback.__table__)


def test_trip_feedback_rating_check_constraint():
    names = {
        constraint.name
        for constraint in TripFeedback.__table__.constraints
        if isinstance(constraint, CheckConstraint)
    }
    assert "ck_trip_feedback_rating_range" in names


def test_route_template_stop_constraints_and_foreign_keys():
    assert "uq_route_template_stops_template_order" in _unique_constraint_names(
        RouteTemplateStop.__table__
    )
    foreign_keys = {
        foreign_key.target_fullname
        for column in RouteTemplateStop.__table__.columns
        for foreign_key in column.foreign_keys
    }
    assert foreign_keys == {"route_templates.id", "pois.poi_id"}
    assert RouteTemplate.__table__.c.id.primary_key is True


def test_database_select_one():
    assert ping_database() is True
    with engine.connect() as connection:
        assert connection.execute(text("SELECT 1")).scalar_one() == 1


def test_health_reports_database_unavailable(monkeypatch):
    def unavailable() -> bool:
        raise ConnectionError("offline")

    monkeypatch.setattr(health_api, "ping_database", unavailable)
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json()["database_status"] == "unavailable"


def test_health_reports_database_ok(monkeypatch):
    monkeypatch.setattr(health_api, "ping_database", lambda: True)
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json()["database_status"] == "ok"


def test_health_preserves_existing_fields(monkeypatch):
    monkeypatch.setattr(health_api, "ping_database", lambda: True)
    data = client.get("/api/v1/health").json()
    assert {"status", "env", "dashscope_configured", "amap_configured"} <= set(data)
    assert data["status"] == "ok"


def test_health_recognizes_amap_web_service_key(monkeypatch):
    monkeypatch.setattr(health_api, "ping_database", lambda: True)
    monkeypatch.setattr(health_api.settings, "amap_api_key", "")
    monkeypatch.setattr(health_api.settings, "amap_web_service_key", "web-service-key")

    assert client.get("/api/v1/health").json()["amap_configured"] is True


def test_alembic_upgrade_downgrade_reupgrade_cycle(test_database_url: str):
    config = _alembic_config(test_database_url)
    isolated_engine = build_engine(test_database_url)
    try:
        command.upgrade(config, "head")
        assert EXPECTED_TABLES <= set(inspect(isolated_engine).get_table_names())

        command.downgrade(config, "base")
        assert not (EXPECTED_TABLES & set(inspect(isolated_engine).get_table_names()))

        command.upgrade(config, "head")
        assert EXPECTED_TABLES <= set(inspect(isolated_engine).get_table_names())
    finally:
        isolated_engine.dispose()
