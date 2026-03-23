from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.deps import get_current_user, get_db
from src.models.baby import Baby
from src.models.notification import Notification, NotificationStatus
from src.models.parent import Parent
from src.models.screening import ResultType, ScreeningResult
from src.models.user import User

router = APIRouter(prefix="/api/analytics", tags=["analytics"])


class OverviewResponse(BaseModel):
    total_parents: int
    total_babies: int
    total_screenings: int
    positive_results: int
    pending_notifications: int
    confirmed_notifications: int
    escalated_notifications: int


class RegionStats(BaseModel):
    region: str
    parents_count: int


class RegionStatsResponse(BaseModel):
    regions: list[RegionStats]


@router.get("/overview", response_model=OverviewResponse)
async def get_overview(
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    total_parents = (
        await session.execute(select(func.count(Parent.id)))
    ).scalar_one()

    total_babies = (
        await session.execute(select(func.count(Baby.id)))
    ).scalar_one()

    total_screenings = (
        await session.execute(select(func.count(ScreeningResult.id)))
    ).scalar_one()

    positive_results = (
        await session.execute(
            select(func.count(ScreeningResult.id)).where(
                ScreeningResult.result_type == ResultType.positive
            )
        )
    ).scalar_one()

    pending_notifications = (
        await session.execute(
            select(func.count(Notification.id)).where(
                Notification.status.in_(
                    [NotificationStatus.pending, NotificationStatus.sent]
                )
            )
        )
    ).scalar_one()

    confirmed_notifications = (
        await session.execute(
            select(func.count(Notification.id)).where(
                Notification.status == NotificationStatus.confirmed
            )
        )
    ).scalar_one()

    escalated_notifications = (
        await session.execute(
            select(func.count(Notification.id)).where(
                Notification.status == NotificationStatus.escalated
            )
        )
    ).scalar_one()

    return OverviewResponse(
        total_parents=total_parents,
        total_babies=total_babies,
        total_screenings=total_screenings,
        positive_results=positive_results,
        pending_notifications=pending_notifications,
        confirmed_notifications=confirmed_notifications,
        escalated_notifications=escalated_notifications,
    )


@router.get("/regions", response_model=RegionStatsResponse)
async def get_region_stats(
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await session.execute(
        select(Parent.region, func.count(Parent.id).label("cnt"))
        .where(Parent.is_active.is_(True), Parent.region.isnot(None))
        .group_by(Parent.region)
        .order_by(func.count(Parent.id).desc())
    )
    regions = [
        RegionStats(region=row.region, parents_count=row.cnt)
        for row in result.all()
    ]
    return RegionStatsResponse(regions=regions)
