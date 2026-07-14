"""Tests for user persistence + minimal JWT login (F1)."""

import pytest
from fastapi.testclient import TestClient

from app.features.users.repository import user_repository
from app.main import app

client = TestClient(app)


@pytest.fixture(autouse=True)
def clear_users():
    user_repository.clear()
    yield
    user_repository.clear()


def _register(user_id: str | None = None, name: str | None = None, language: str = "zh-CN") -> dict:
    payload: dict = {"language": language}
    if user_id is not None:
        payload["user_id"] = user_id
    if name is not None:
        payload["name"] = name
    response = client.post("/api/v1/users/register", json=payload)
    assert response.status_code == 201, response.text
    return response.json()


def test_register_generates_user_id_and_issues_token():
    body = _register(name="Grace", language="en")
    assert body["user_id"].startswith("u_")
    assert body["token"]
    assert body["user"]["name"] == "Grace"
    assert body["user"]["language"] == "en"
    assert body["user"]["preference"] is None


def test_register_with_explicit_user_id():
    body = _register(user_id="demo-auth-001", name="Tester")
    assert body["user_id"] == "demo-auth-001"
    assert body["user"]["user_id"] == "demo-auth-001"


def test_register_duplicate_returns_409():
    _register(user_id="dup-001")
    response = client.post("/api/v1/users/register", json={"user_id": "dup-001", "language": "zh-CN"})
    assert response.status_code == 409


def test_register_invalid_language_returns_422():
    response = client.post("/api/v1/users/register", json={"language": "fr"})
    assert response.status_code == 422


def test_login_unknown_user_returns_404():
    response = client.post("/api/v1/users/login", json={"user_id": "no-such-user"})
    assert response.status_code == 404


def test_login_issues_token():
    _register(user_id="login-001")
    response = client.post("/api/v1/users/login", json={"user_id": "login-001"})
    assert response.status_code == 200
    assert response.json()["token"]


def test_me_without_token_returns_401():
    response = client.get("/api/v1/users/me")
    assert response.status_code == 401


def test_me_with_invalid_token_returns_401():
    response = client.get("/api/v1/users/me", headers={"Authorization": "Bearer not-a-real-token"})
    assert response.status_code == 401


def test_me_with_valid_token_returns_user():
    body = _register(user_id="me-001", name="Me")
    response = client.get("/api/v1/users/me", headers={"Authorization": f"Bearer {body['token']}"})
    assert response.status_code == 200
    assert response.json()["user"]["user_id"] == "me-001"
    assert response.json()["user"]["name"] == "Me"


def test_get_user_unknown_returns_404():
    response = client.get("/api/v1/users/no-such-user")
    assert response.status_code == 404


def test_get_user_returns_registered_user():
    _register(user_id="get-001", name="Getter", language="zh-TW")
    response = client.get("/api/v1/users/get-001")
    assert response.status_code == 200
    user = response.json()["user"]
    assert user["name"] == "Getter"
    assert user["language"] == "zh-TW"


def test_update_preferences_persists_and_round_trips():
    _register(user_id="pref-001", language="zh-CN")
    pref = {
        "duration": "half-day",
        "party_size": 2,
        "travel_type": ["friends"],
        "interests": ["history", "photo"],
        "physical": ["less-walk"],
        "language": "zh-TW",
    }
    response = client.put("/api/v1/users/pref-001/preferences", json=pref)
    assert response.status_code == 200, response.text
    assert response.json()["preference"]["interests"] == ["history", "photo"]

    # 偏好落库：重新查询能拿回完整 preference
    got = client.get("/api/v1/users/pref-001").json()["user"]
    assert got["preference"] is not None
    assert got["preference"]["duration"] == "half-day"
    assert got["preference"]["party_size"] == 2
    assert got["preference"]["physical"] == ["less-walk"]
    # 顶层 language 与 preference.language 同步
    assert got["language"] == "zh-TW"


def test_update_preferences_for_unknown_user_upserts():
    """保留旧行为：偏好写入时用户不存在则顺带创建。"""
    pref = {"duration": "full-day", "language": "en"}
    response = client.put("/api/v1/users/auto-create-001/preferences", json=pref)
    assert response.status_code == 200
    assert client.get("/api/v1/users/auto-create-001").status_code == 200


def test_preference_survives_new_login_session():
    """DB 持久化铁证：写偏好后重新 login，me 仍带偏好。"""
    _register(user_id="persist-001")
    client.put(
        "/api/v1/users/persist-001/preferences",
        json={"duration": "evening", "interests": ["food"], "language": "zh-CN"},
    )
    login = client.post("/api/v1/users/login", json={"user_id": "persist-001"}).json()
    me = client.get("/api/v1/users/me", headers={"Authorization": f"Bearer {login['token']}"}).json()
    assert me["user"]["preference"]["interests"] == ["food"]
    assert me["user"]["preference"]["duration"] == "evening"
