"""Tests for email-based user registration + JWT login (F1 v2)."""

import pytest
from fastapi.testclient import TestClient

from app.features.users.repository import user_repository
from app.main import app

client = TestClient(app)
TEST_PASSWORD = "TestPassword123!"


@pytest.fixture(autouse=True)
def clear_users():
    user_repository.clear()
    yield
    user_repository.clear()


def _register(
    email: str = "test@example.com",
    name: str = "Tester",
    language: str = "zh-CN",
    country: str | None = None,
) -> dict:
    payload: dict = {
        "email": email,
        "password": TEST_PASSWORD,
        "name": name,
        "language": language,
    }
    if country is not None:
        payload["country"] = country
    response = client.post("/api/v1/users/register", json=payload)
    assert response.status_code == 201, response.text
    return response.json()


def test_register_generates_numeric_user_id_and_issues_token():
    body = _register(email="grace@test.com", name="Grace", language="en", country="CN")
    # user_id should be numeric (like QQ number)
    assert body["user_id"].isdigit()
    assert body["email"] == "grace@test.com"
    assert body["token"]
    assert body["user"]["name"] == "Grace"
    assert body["user"]["language"] == "en"
    assert body["user"]["country"] == "CN"
    assert body["user"]["email"] == "grace@test.com"
    assert body["user"]["preference"] is None


def test_register_name_is_required():
    """name is required now — missing should return 422."""
    response = client.post(
        "/api/v1/users/register",
        json={"email": "x@test.com", "password": TEST_PASSWORD, "language": "zh-CN"},
    )
    assert response.status_code == 422


def test_register_email_is_required():
    response = client.post(
        "/api/v1/users/register",
        json={"password": TEST_PASSWORD, "name": "X", "language": "zh-CN"},
    )
    assert response.status_code == 422


def test_register_password_is_required():
    response = client.post(
        "/api/v1/users/register",
        json={"email": "x@test.com", "name": "X", "language": "zh-CN"},
    )
    assert response.status_code == 422


def test_register_duplicate_email_returns_409():
    _register(email="dup@test.com")
    response = client.post(
        "/api/v1/users/register",
        json={
            "email": "dup@test.com",
            "password": TEST_PASSWORD,
            "name": "Dup",
            "language": "zh-CN",
        },
    )
    assert response.status_code == 409


def test_register_invalid_language_returns_422():
    response = client.post(
        "/api/v1/users/register",
        json={
            "email": "x@test.com",
            "password": TEST_PASSWORD,
            "name": "X",
            "language": "fr",
        },
    )
    assert response.status_code == 422


def test_login_unknown_email_returns_404():
    response = client.post(
        "/api/v1/users/login",
        json={"email": "no-such@test.com", "password": TEST_PASSWORD},
    )
    assert response.status_code == 404


def test_login_issues_token():
    body = _register(email="login@test.com")
    response = client.post(
        "/api/v1/users/login",
        json={"email": "login@test.com", "password": TEST_PASSWORD},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["token"]
    assert data["email"] == "login@test.com"
    assert data["user_id"] == body["user_id"]


def test_login_with_wrong_password_returns_404():
    _register(email="wrong-password@test.com")
    response = client.post(
        "/api/v1/users/login",
        json={"email": "wrong-password@test.com", "password": "WrongPassword123!"},
    )
    assert response.status_code == 404


def test_phone_registration_and_login():
    registered = client.post(
        "/api/v1/users/register",
        json={
            "phone": "+85360000001",
            "password": TEST_PASSWORD,
            "name": "Phone User",
            "language": "zh-CN",
            "country": "MO",
        },
    )
    assert registered.status_code == 201, registered.text
    assert registered.json()["phone"] == "+85360000001"
    assert registered.json()["email"] is None

    login = client.post(
        "/api/v1/users/login",
        json={"phone": "+85360000001", "password": TEST_PASSWORD},
    )
    assert login.status_code == 200, login.text
    assert login.json()["user_id"] == registered.json()["user_id"]


def test_me_without_token_returns_401():
    response = client.get("/api/v1/users/me")
    assert response.status_code == 401


def test_me_with_invalid_token_returns_401():
    response = client.get("/api/v1/users/me", headers={"Authorization": "Bearer not-a-real-token"})
    assert response.status_code == 401


def test_me_with_valid_token_returns_user():
    body = _register(email="me@test.com", name="Me")
    response = client.get("/api/v1/users/me", headers={"Authorization": f"Bearer {body['token']}"})
    assert response.status_code == 200
    assert response.json()["user"]["user_id"] == body["user_id"]
    assert response.json()["user"]["name"] == "Me"
    assert response.json()["user"]["email"] == "me@test.com"


def test_get_user_unknown_returns_404():
    response = client.get("/api/v1/users/no-such-user")
    assert response.status_code == 404


def test_get_user_returns_registered_user():
    body = _register(email="get@test.com", name="Getter", language="zh-TW", country="MO")
    uid = body["user_id"]
    response = client.get(f"/api/v1/users/{uid}")
    assert response.status_code == 200
    user = response.json()["user"]
    assert user["name"] == "Getter"
    assert user["language"] == "zh-TW"
    assert user["country"] == "MO"
    assert user["email"] == "get@test.com"


def test_update_preferences_persists_and_round_trips():
    body = _register(email="pref@test.com", language="zh-CN")
    uid = body["user_id"]
    pref = {
        "duration": "half-day",
        "party_size": 2,
        "travel_type": ["friends"],
        "interests": ["history", "photo"],
        "physical": ["less-walk"],
        "language": "zh-TW",
    }
    response = client.put(f"/api/v1/users/{uid}/preferences", json=pref)
    assert response.status_code == 200, response.text
    assert response.json()["preference"]["interests"] == ["history", "photo"]

    got = client.get(f"/api/v1/users/{uid}").json()["user"]
    assert got["preference"] is not None
    assert got["preference"]["duration"] == "half-day"
    assert got["preference"]["party_size"] == 2
    assert got["preference"]["physical"] == ["less-walk"]
    assert got["language"] == "zh-TW"


def test_update_preferences_for_unknown_user_upserts():
    pref = {"duration": "full-day", "language": "en"}
    response = client.put("/api/v1/users/auto-create-001/preferences", json=pref)
    assert response.status_code == 200
    assert client.get("/api/v1/users/auto-create-001").status_code == 200


def test_preference_survives_new_login_session():
    body = _register(email="persist@test.com")
    uid = body["user_id"]
    client.put(
        f"/api/v1/users/{uid}/preferences",
        json={"duration": "evening", "interests": ["food"], "language": "zh-CN"},
    )
    login = client.post(
        "/api/v1/users/login",
        json={"email": "persist@test.com", "password": TEST_PASSWORD},
    ).json()
    me = client.get("/api/v1/users/me", headers={"Authorization": f"Bearer {login['token']}"}).json()
    assert me["user"]["preference"]["interests"] == ["food"]
    assert me["user"]["preference"]["duration"] == "evening"
