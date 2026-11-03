"""Pre-generate the next day's outfits while the text model is running.

The phone can host one heavy process at a time, so this entrypoint is meant to
run from ``deploy/gt2/nightly.sh`` after llama-server is up and the API is stopped.
It reuses the same scoring, model pick and validation as an on-demand suggestion,
with the forecast for the target date and the user's default occasion.

Vision tagging cannot run on that text-only server. Items still waiting for a
description are counted and, only when internal vision is enabled, enqueued on
the existing tagging queue so a vision endpoint in the same window can drain them.

Usage (from the backend directory)::

    python -m app.jobs.nightly_outfits
    python -m app.jobs.nightly_outfits --for-today
    python -m app.jobs.nightly_outfits --date 2026-11-04 --force
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import sys
from datetime import date, timedelta
from uuid import UUID

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.config import get_settings
from app.database import async_session_maker
from app.logging_config import configure_logging
from app.models.item import ClothingItem, ItemStatus, TaggingStatus
from app.models.outfit import Outfit, OutfitSource, OutfitStatus, TimeOfDay
from app.models.user import User
from app.services.image_service import ImageService
from app.services.prepared_outfits import has_scheduled_outfits
from app.services.recommendation_service import (
    AIRecommendationError,
    InsufficientWardrobeError,
    RecommendationService,
)
from app.services.weather_service import GeocodingServiceError, WeatherService, WeatherServiceError
from app.utils.preference_defaults import DEFAULT_OCCASION
from app.utils.timezone import get_user_today
from app.workers.queues import TAGGING_QUEUE

logger = logging.getLogger(__name__)


def target_day(user: User, *, for_today: bool, explicit: date | None) -> date:
    if explicit is not None:
        return explicit
    today = get_user_today(user)
    if for_today:
        return today
    return today + timedelta(days=1)


async def _coordinates(weather: WeatherService, user: User) -> tuple[float, float] | None:
    if user.location_lat is not None and user.location_lon is not None:
        return float(user.location_lat), float(user.location_lon)
    if not user.location_name:
        return None
    geocoded = await weather.geocode_location_name(user.location_name)
    if not geocoded:
        return None
    lat, lon, _name = geocoded
    return lat, lon


async def generate_for_user(
    session: AsyncSession,
    user: User,
    *,
    day: date,
    force: bool,
    count: int,
    weather: WeatherService | None = None,
) -> str:
    """Return a short status: created, skipped, or failed."""
    if not force and await has_scheduled_outfits(session, user.id, day):
        logger.info("User %s already has outfits for %s", user.id, day)
        return "skipped"
    weather = weather or WeatherService()
    coords = await _coordinates(weather, user)
    if coords is None:
        logger.info("User %s has no location; skipping", user.id)
        return "skipped"
    forecast = await weather.get_weather_for_date(coords[0], coords[1], day.isoformat())
    if force:
        await session.execute(
            update(Outfit)
            .where(
                Outfit.user_id == user.id,
                Outfit.scheduled_for == day,
                Outfit.source == OutfitSource.scheduled,
                Outfit.status.in_((OutfitStatus.pending, OutfitStatus.sent, OutfitStatus.viewed)),
            )
            .values(status=OutfitStatus.skipped)
        )
    occasion = (
        user.preferences.default_occasion
        if user.preferences and user.preferences.default_occasion
        else DEFAULT_OCCASION
    )
    service = RecommendationService(session)
    await service.generate_recommendations(
        user=user,
        occasion=occasion,
        weather_override=forecast,
        source=OutfitSource.scheduled,
        time_of_day=TimeOfDay.full_day,
        count=count,
        scheduled_date=day,
    )
    logger.info("Prepared %s outfit(s) for user %s on %s (%s)", count, user.id, day, occasion)
    return "created"


async def queue_pending_tagging(session: AsyncSession, *, limit: int = 20) -> dict[str, int | str]:
    """Count items still waiting for a description.

    The nightly llama-server is text-only, so photos are left queued unless
    internal vision is actually enabled for this process.
    """
    pending = int(
        await session.scalar(
            select(func.count())
            .select_from(ClothingItem)
            .where(
                ClothingItem.tagging_status == TaggingStatus.pending,
                ClothingItem.status == ItemStatus.ready,
                ClothingItem.is_archived.is_(False),
            )
        )
        or 0
    )
    settings = get_settings()
    if not settings.effective_ai_vision_enabled:
        logger.info(
            "%s item(s) still need a description. The text model cannot tag photos; "
            "they stay queued until a vision endpoint is enabled.",
            pending,
        )
        return {"pending": pending, "enqueued": 0, "reason": "vision_disabled"}
    if pending == 0:
        return {"pending": 0, "enqueued": 0, "reason": "none"}

    rows = (
        (
            await session.execute(
                select(ClothingItem)
                .where(
                    ClothingItem.tagging_status == TaggingStatus.pending,
                    ClothingItem.status == ItemStatus.ready,
                    ClothingItem.is_archived.is_(False),
                )
                .order_by(ClothingItem.created_at.asc())
                .limit(limit)
            )
        )
        .scalars()
        .all()
    )
    from arq import create_pool

    from app.workers.settings import get_redis_settings

    enqueued = 0
    images = ImageService()
    redis = await create_pool(get_redis_settings())
    try:
        for item in rows:
            path = str(images.get_image_path(item.image_path))
            job = await redis.enqueue_job(
                "tag_item_image",
                str(item.id),
                path,
                _queue_name=TAGGING_QUEUE,
            )
            if job is not None:
                item.status = ItemStatus.processing
                item.ai_job_id = job.job_id
                enqueued += 1
        await session.commit()
    finally:
        await redis.aclose()
    logger.info("Enqueued %s vision tagging job(s) (%s pending)", enqueued, pending)
    return {"pending": pending, "enqueued": enqueued, "reason": "queued"}


async def run(
    *,
    for_today: bool = False,
    explicit: date | None = None,
    force: bool = False,
    count: int = 3,
    user_id: UUID | None = None,
) -> int:
    """Process every active user. Returns the number of users who got new outfits."""
    created = 0
    failed = 0
    async with async_session_maker() as session:
        query = select(User).where(User.is_active.is_(True)).options(selectinload(User.preferences))
        if user_id is not None:
            query = query.where(User.id == user_id)
        users = list((await session.execute(query)).scalars().all())
        user_ids = [user.id for user in users]

    weather = WeatherService()
    for uid in user_ids:
        async with async_session_maker() as session:
            user = await session.scalar(
                select(User).where(User.id == uid).options(selectinload(User.preferences))
            )
            if user is None:
                continue
            day = target_day(user, for_today=for_today, explicit=explicit)
            try:
                status = await generate_for_user(
                    session, user, day=day, force=force, count=count, weather=weather
                )
            except (
                InsufficientWardrobeError,
                AIRecommendationError,
                WeatherServiceError,
                GeocodingServiceError,
                ValueError,
            ) as exc:
                failed += 1
                logger.warning("Outfit batch failed for user %s: %s", uid, exc)
                await session.rollback()
                continue
            except Exception:
                failed += 1
                logger.exception("Outfit batch failed for user %s", uid)
                await session.rollback()
                continue
            if status == "created":
                created += 1

    async with async_session_maker() as session:
        try:
            await queue_pending_tagging(session)
        except Exception:
            logger.exception("Could not review the pending description queue")

    logger.info(
        "Nightly outfits finished: %s created, %s failed, %s users", created, failed, len(user_ids)
    )
    if user_ids and created == 0 and failed == len(user_ids):
        return 1
    return 0


def _parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Pre-generate the next day's outfits")
    parser.add_argument("--date", help="Target date (YYYY-MM-DD) for every user")
    parser.add_argument(
        "--for-today",
        action="store_true",
        help="Use each user's local today instead of tomorrow (for a run after midnight)",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Replace still-pending outfits already stored for the target date",
    )
    parser.add_argument("--count", type=int, default=3, help="Outfits to store per user")
    parser.add_argument("--user", help="Only this user id")
    args = parser.parse_args(argv)
    if args.count < 1:
        parser.error("--count must be at least 1")
    return args


def main(argv: list[str] | None = None) -> int:
    configure_logging(get_settings())
    args = _parse_args(sys.argv[1:] if argv is None else argv)
    explicit = date.fromisoformat(args.date) if args.date else None
    user_id = UUID(args.user) if args.user else None
    code = asyncio.run(
        run(
            for_today=args.for_today,
            explicit=explicit,
            force=args.force,
            count=args.count,
            user_id=user_id,
        )
    )
    return code


if __name__ == "__main__":
    raise SystemExit(main())
