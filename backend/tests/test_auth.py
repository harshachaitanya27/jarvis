"""End-to-end auth + onboarding tests over the real HTTP stack (SQLite-backed)."""

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_signup_login_onboarding_flow():
    email, password = "harsha@example.com", "password123"

    # signup returns a token
    r = client.post(
        "/auth/signup",
        json={"email": email, "password": password, "topics": ["space"]},
    )
    assert r.status_code == 201
    token = r.json()["access_token"]
    auth = {"Authorization": f"Bearer {token}"}

    # duplicate email is rejected
    assert client.post("/auth/signup", json={"email": email, "password": password}).status_code == 409

    # login works; wrong password does not
    assert client.post("/auth/login", json={"email": email, "password": password}).status_code == 200
    assert client.post("/auth/login", json={"email": email, "password": "nope"}).status_code == 401

    # /me reflects onboarding state
    me = client.get("/me", headers=auth)
    assert me.status_code == 200
    body = me.json()
    assert body["email"] == email
    assert body["topics"] == ["space"]
    assert body["configured_providers"] == []

    # unauthenticated /me is blocked
    assert client.get("/me").status_code in (401, 403)

    # storing a BYO key: configured but never echoed back
    r = client.put("/me/keys", headers=auth, json={"keys": {"openai": "sk-secret-value"}})
    assert r.status_code == 200
    assert r.json()["configured_providers"] == ["openai"]
    assert "sk-secret-value" not in r.text

    # updating topics
    r = client.put("/me/topics", headers=auth, json={"topics": ["ai", "music"]})
    assert r.json()["topics"] == ["ai", "music"]


def test_bad_and_missing_tokens_rejected():
    assert client.get("/me", headers={"Authorization": "Bearer not.a.real.jwt"}).status_code == 401
    assert client.get("/me").status_code in (401, 403)


def test_short_password_rejected():
    r = client.post("/auth/signup", json={"email": "x@y.com", "password": "short"})
    assert r.status_code == 422  # pydantic min_length


def test_empty_provider_key_rejected():
    r = client.post(
        "/auth/signup", json={"email": "emptykey@example.com", "password": "password123"}
    )
    auth = {"Authorization": f"Bearer {r.json()['access_token']}"}

    # empty, whitespace-only, and no-keys are all rejected with 422
    assert client.put("/me/keys", headers=auth, json={"keys": {"openai": ""}}).status_code == 422
    assert client.put("/me/keys", headers=auth, json={"keys": {"openai": "   "}}).status_code == 422
    assert client.put("/me/keys", headers=auth, json={"keys": {}}).status_code == 422

    # a real key still works
    ok = client.put("/me/keys", headers=auth, json={"keys": {"openai": "sk-real"}})
    assert ok.status_code == 200
    assert ok.json()["configured_providers"] == ["openai"]
