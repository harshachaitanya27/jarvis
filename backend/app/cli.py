"""Command-line trigger for episode generation.

    python -m app.cli --user <id>     # one user
    python -m app.cli --all           # every user (the nightly batch)

Opens a database session, wires the real adapters, and runs the job runner.
The scheduler calls the same ``run_for_all`` coroutine on a cron.
"""

import argparse
import asyncio
import logging

from app.adapters.db.repositories import (
    SqlEpisodeRepository,
    SqlTranscriptRepository,
    SqlUserRepository,
)
from app.adapters.db.session import SessionFactory
from app.config import get_settings
from app.core.providers import build_storage
from app.domain.entities import User
from app.services.crypto import KeyVault
from app.services.jobs import GenerationJobRunner, generate_for_user
from app.services.users import UserService
from app.tracing import get_tracer

log = logging.getLogger(__name__)
tracer = get_tracer(__name__)


async def _generate(users: list[User]) -> None:
    settings = get_settings()
    log.info("generation batch starting for %d user(s)", len(users))
    produced_total = skipped = 0
    with tracer.start_as_current_span("jobs.batch") as span:
        span.set_attribute("users.total", len(users))
        async with SessionFactory() as session:
            user_repo = SqlUserRepository(session)
            runner = GenerationJobRunner(
                SqlEpisodeRepository(session),
                SqlTranscriptRepository(session),
                build_storage(settings),
            )
            user_service = UserService(user_repo, KeyVault())

            for user in users:
                try:
                    episodes = await generate_for_user(
                        user, runner=runner, user_service=user_service, settings=settings
                    )
                    produced_total += len(episodes)
                    print(f"user {user.id}: generated {len(episodes)} episode(s)")
                except KeyError as exc:
                    skipped += 1
                    log.warning(
                        "user %s skipped: missing provider key %s", user.id, exc
                    )
                    print(f"user {user.id}: skipped — missing provider key {exc}")
            await session.commit()
        span.set_attribute("episodes.produced", produced_total)
        span.set_attribute("users.skipped", skipped)
    log.info(
        "generation batch done: %d episode(s) across %d user(s), %d skipped",
        produced_total,
        len(users),
        skipped,
    )


async def run_for_all() -> None:
    async with SessionFactory() as session:
        users = await SqlUserRepository(session).list_all()
    await _generate(users)


async def run_for_user_id(user_id: str) -> None:
    async with SessionFactory() as session:
        user = await SqlUserRepository(session).get(user_id)
    if user is None:
        log.warning("no such user: %s", user_id)
        print(f"no such user: {user_id}")
        return
    await _generate([user])


def main() -> None:
    logging.basicConfig(level=get_settings().log_level)
    parser = argparse.ArgumentParser(description="Trigger Jarvis episode generation")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--user", help="generate for a single user id")
    group.add_argument("--all", action="store_true", help="generate for all users")
    args = parser.parse_args()

    if args.all:
        asyncio.run(run_for_all())
    else:
        asyncio.run(run_for_user_id(args.user))


if __name__ == "__main__":
    main()
