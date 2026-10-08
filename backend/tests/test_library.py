"""Library API tests over the HTTP stack, with a seeded ready episode."""

import asyncio
import os

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


async def _seed_ready_episode(user_id: str) -> str:
    """Insert a READY episode + transcript via a throwaway engine (own loop)."""
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

    from app.adapters.db.repositories import (
        SqlEpisodeRepository,
        SqlTranscriptRepository,
    )
    from app.domain.entities import (
        Episode,
        EpisodeStatus,
        Transcript,
        TranscriptSegment,
    )

    engine = create_async_engine(os.environ["DATABASE_URL"])
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as s:
        episodes = SqlEpisodeRepository(s)
        transcripts = SqlTranscriptRepository(s)
        ep = await episodes.create(Episode(id="", user_id=user_id, topics=["space"]))
        await episodes.set_title(ep.id, "Seeded Episode")
        await episodes.set_audio(ep.id, f"{user_id}/{ep.id}.mp3", 123.4)
        await episodes.set_status(ep.id, EpisodeStatus.READY)
        await transcripts.save(
            Transcript(
                episode_id=ep.id,
                segments=[TranscriptSegment("host", "hello from the episode")],
            )
        )
        await s.commit()
    await engine.dispose()
    return ep.id


def _signup(email: str) -> dict:
    r = client.post("/auth/signup", json={"email": email, "password": "password123"})
    assert r.status_code == 201
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def test_library_lists_serves_and_isolates():
    auth = _signup("library@example.com")
    user_id = client.get("/me", headers=auth).json()["id"]
    episode_id = asyncio.run(_seed_ready_episode(user_id))

    # list shows the ready episode with a playable url
    r = client.get("/me/episodes", headers=auth)
    assert r.status_code == 200
    items = r.json()
    assert len(items) == 1
    ep = items[0]
    assert ep["id"] == episode_id
    assert ep["status"] == "ready"
    assert ep["title"] == "Seeded Episode"
    assert ep["duration_seconds"] == 123.4
    assert ep["audio_url"] and episode_id in ep["audio_url"]

    # detail
    assert client.get(f"/me/episodes/{episode_id}", headers=auth).status_code == 200

    # transcript
    t = client.get(f"/me/episodes/{episode_id}/transcript", headers=auth)
    assert t.status_code == 200
    assert t.json()["segments"][0]["text"] == "hello from the episode"

    # another user cannot see or fetch it
    other = _signup("intruder@example.com")
    assert client.get("/me/episodes", headers=other).json() == []
    assert client.get(f"/me/episodes/{episode_id}", headers=other).status_code == 404
    assert (
        client.get(f"/me/episodes/{episode_id}/transcript", headers=other).status_code
        == 404
    )


async def _seed_failed_episode(user_id: str, reason: str) -> str:
    """Insert a FAILED episode via a throwaway engine (own loop)."""
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

    from app.adapters.db.repositories import SqlEpisodeRepository
    from app.domain.entities import Episode, EpisodeStatus

    engine = create_async_engine(os.environ["DATABASE_URL"])
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as s:
        episodes = SqlEpisodeRepository(s)
        ep = await episodes.create(Episode(id="", user_id=user_id, topics=["space"]))
        await episodes.set_status(ep.id, EpisodeStatus.FAILED, error=reason)
        await s.commit()
    await engine.dispose()
    return ep.id


def test_failed_episode_surfaces_a_friendly_error():
    auth = _signup("failed@example.com")
    user_id = client.get("/me", headers=auth).json()["id"]
    # Store a raw, technical reason like generation would.
    asyncio.run(_seed_failed_episode(user_id, "Error code: 401 - Incorrect API key provided: sk-abc"))

    items = client.get("/me/episodes", headers=auth).json()
    assert len(items) == 1
    assert items[0]["status"] == "failed"
    assert items[0]["audio_url"] is None
    # The user sees calm guidance, not the raw status code / key fragment.
    assert items[0]["error"] == "Your AI provider key looks invalid or missing. Re-add it, then try again."
    assert "401" not in items[0]["error"]
    assert "sk-abc" not in items[0]["error"]


def test_unknown_episode_is_404():
    auth = _signup("nobody@example.com")
    assert client.get("/me/episodes/does-not-exist", headers=auth).status_code == 404


def test_generate_now_schedules_when_key_present():
    from app.api import deps

    auth = _signup("gen@example.com")
    client.put("/me/keys", headers=auth, json={"keys": {"openai": "sk-test"}})

    calls: list[str] = []

    async def fake(user_id: str) -> None:
        calls.append(user_id)

    app.dependency_overrides[deps.get_generate_task] = lambda: fake
    try:
        r = client.post("/me/episodes/generate", headers=auth)
        assert r.status_code == 202
        assert len(calls) == 1  # background task ran, with no real pipeline
    finally:
        app.dependency_overrides.pop(deps.get_generate_task, None)


def test_generate_now_requires_a_key():
    auth = _signup("nokey-gen@example.com")
    assert client.post("/me/episodes/generate", headers=auth).status_code == 400
