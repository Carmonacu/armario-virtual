"""Outfits the nightly job stored for a user to wear without calling the model."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.outfit import FamilyOutfitRating, Outfit, OutfitItem, OutfitSource, OutfitStatus
from app.models.user import User
from app.utils.timezone import get_user_today

PREPARED_STATUSES = (
    OutfitStatus.pending,
    OutfitStatus.sent,
    OutfitStatus.viewed,
)


async def load_prepared_outfits(
    db: AsyncSession,
    user: User,
    *,
    occasion: str | None = None,
    limit: int = 3,
) -> list[Outfit]:
    """Pending scheduled outfits for the user's local today.

    When ``occasion`` matches any of them, only those are returned. Otherwise the
    day's prepared outfits are returned anyway: a daytime request must still show
    something when the text model is off.
    """
    day = get_user_today(user)
    result = await db.execute(
        select(Outfit)
        .where(
            Outfit.user_id == user.id,
            Outfit.scheduled_for == day,
            Outfit.source == OutfitSource.scheduled,
            Outfit.status.in_(PREPARED_STATUSES),
        )
        .options(
            selectinload(Outfit.items).selectinload(OutfitItem.item),
            selectinload(Outfit.feedback),
            selectinload(Outfit.family_ratings).selectinload(FamilyOutfitRating.user),
        )
        .order_by(Outfit.created_at.asc())
        .limit(12)
    )
    rows = list(result.scalars().unique().all())
    if occasion:
        matching = [row for row in rows if row.occasion == occasion]
        if matching:
            rows = matching
    return rows[:limit]


async def has_scheduled_outfits(db: AsyncSession, user_id: UUID, day) -> bool:
    result = await db.execute(
        select(Outfit.id)
        .where(
            Outfit.user_id == user_id,
            Outfit.scheduled_for == day,
            Outfit.source == OutfitSource.scheduled,
            Outfit.status != OutfitStatus.skipped,
        )
        .limit(1)
    )
    return result.scalar_one_or_none() is not None
