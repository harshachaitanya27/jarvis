"""Feedback API tests over the HTTP stack."""

import asyncio
import os

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


async def _seed_episode(user_id: str) -> str:
    """Insert a minimal episode owned by the user via a throwaway engine."""
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

    from app.adapters.db.repositories import SqlEpisodeRepository
    from app.domain.entities import Episode

    engine = create_async_engine(os.environ["DATABASE_URL"])
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as s:
        ep = await SqlEpisodeRepository(s).create(
            Episode(id="", user_id=user_id, topics=["space"])
        )
        await s.commit()
    await engine.dispose()
    return ep.id


def _signup(email: str) -> dict:
    r = client.post("/auth/signup", json={"email": email, "password": "password123"})
    assert r.status_code == 201
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def test_log_and_list_feedback():
    auth = _signup("feedback@example.com")
    user_id = client.get("/me", headers=auth).json()["id"]
    episode_id = asyncio.run(_seed_episode(user_id))

    # log two events
    r = client.post(
        f"/me/episodes/{episode_id}/feedback",
        headers=auth,
        json={"type": "complete", "position_seconds": 600.0},
    )
    assert r.status_code == 201
    assert client.post(
        f"/me/episodes/{episode_id}/feedback",
        headers=auth,
        json={"type": "skip", "position_seconds": 12.5},
    ).status_code == 201

    # read them back, newest first
    listed = client.get("/me/feedback", headers=auth)
    assert listed.status_code == 200
    events = listed.json()
    assert len(events) == 2
    assert {e["type"] for e in events} == {"complete", "skip"}
    assert all(e["episode_id"] == episode_id for e in events)


def test_invalid_feedback_type_is_422():
    auth = _signup("badtype@example.com")
    user_id = client.get("/me", headers=auth).json()["id"]
    episode_id = asyncio.run(_seed_episode(user_id))
    r = client.post(
        f"/me/episodes/{episode_id}/feedback",
        headers=auth,
        json={"type": "loved_it"},  # not a FeedbackType
    )
    assert r.status_code == 422


def test_feedback_on_unknown_or_foreign_episode_is_404():
    auth = _signup("fb-owner@example.com")
    user_id = client.get("/me", headers=auth).json()["id"]
    episode_id = asyncio.run(_seed_episode(user_id))

    # unknown episode
    assert client.post(
        "/me/episodes/nope/feedback", headers=auth, json={"type": "play"}
    ).status_code == 404

    # another user cannot log against this episode, and sees an empty log
    other = _signup("fb-intruder@example.com")
    assert client.post(
        f"/me/episodes/{episode_id}/feedback", headers=other, json={"type": "play"}
    ).status_code == 404
    assert client.get("/me/feedback", headers=other).json() == []
