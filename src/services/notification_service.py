import logging
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.config import settings
from src.models.notification import Notification, NotificationStatus

logger = logging.getLogger(__name__)


async def get_pending_notifications(session: AsyncSession) -> list[Notification]:
    """Get notifications that need to be sent or retried."""
    now = datetime.now(timezone.utc)
    retry_delta = timedelta(hours=settings.notification_retry_interval_hours)

    stmt = select(Notification).where(
        Notification.status.in_([NotificationStatus.pending, NotificationStatus.sent]),
        Notification.retry_count < settings.notification_max_retries,
        # Either never sent, or enough time passed since last send
        (Notification.sent_at.is_(None))
        | (Notification.sent_at < now - retry_delta),
    )
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def get_notifications_to_escalate(session: AsyncSession) -> list[Notification]:
    """Get notifications that have not been confirmed within the escalation window."""
    now = datetime.now(timezone.utc)
    escalation_delta = timedelta(hours=settings.notification_escalation_hours)

    stmt = select(Notification).where(
        Notification.status.in_([NotificationStatus.sent, NotificationStatus.delivered]),
        Notification.confirmed_at.is_(None),
        Notification.sent_at.isnot(None),
        Notification.sent_at < now - escalation_delta,
        Notification.retry_count >= settings.notification_max_retries,
    )
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def mark_sent(session: AsyncSession, notification_id: uuid.UUID) -> None:
    notification = await session.get(Notification, notification_id)
    if notification:
        notification.sent_at = datetime.now(timezone.utc)
        notification.retry_count += 1
        notification.status = NotificationStatus.sent
        await session.commit()


async def mark_confirmed(session: AsyncSession, notification_id: uuid.UUID) -> None:
    notification = await session.get(Notification, notification_id)
    if notification:
        notification.confirmed_at = datetime.now(timezone.utc)
        notification.status = NotificationStatus.confirmed
        await session.commit()


async def mark_escalated(session: AsyncSession, notification_id: uuid.UUID) -> None:
    notification = await session.get(Notification, notification_id)
    if notification:
        notification.status = NotificationStatus.escalated
        await session.commit()


async def list_notifications(
    session: AsyncSession,
    status: NotificationStatus | None = None,
    offset: int = 0,
    limit: int = 50,
) -> list[Notification]:
    stmt = select(Notification)
    if status:
        stmt = stmt.where(Notification.status == status)
    stmt = stmt.offset(offset).limit(limit).order_by(Notification.created_at.desc())
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def count_notifications(
    session: AsyncSession, status: NotificationStatus | None = None
) -> int:
    from sqlalchemy import func

    stmt = select(func.count(Notification.id))
    if status:
        stmt = stmt.where(Notification.status == status)
    result = await session.execute(stmt)
    return result.scalar_one()
