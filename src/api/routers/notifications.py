import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.deps import get_current_user, get_db
from src.models.notification import Notification, NotificationStatus
from src.models.user import User
from src.services.notification_service import (
    count_notifications,
    list_notifications,
)

router = APIRouter(prefix="/api/notifications", tags=["notifications"])


class NotificationResponse(BaseModel):
    id: uuid.UUID
    parent_id: uuid.UUID
    screening_result_id: uuid.UUID
    message_text: str
    sent_at: datetime | None
    confirmed_at: datetime | None
    retry_count: int
    status: NotificationStatus

    model_config = {"from_attributes": True}


class NotificationListResponse(BaseModel):
    items: list[NotificationResponse]
    total: int


@router.get("/", response_model=NotificationListResponse)
async def get_notifications(
    status: NotificationStatus | None = None,
    offset: int = 0,
    limit: int = 50,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    items = await list_notifications(session, status=status, offset=offset, limit=limit)
    total = await count_notifications(session, status=status)
    return NotificationListResponse(items=items, total=total)


@router.post("/{notification_id}/resend")
async def resend_notification(
    notification_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    notification = await session.get(Notification, notification_id)
    if not notification:
        raise HTTPException(status_code=404, detail="Notification not found")

    notification.status = NotificationStatus.pending
    notification.retry_count = 0
    await session.commit()

    return {"message": "Notification queued for resend"}
