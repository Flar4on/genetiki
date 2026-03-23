import uuid
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.notification import Notification, NotificationStatus
from src.models.screening import ResultType, ScreeningResult


async def get_result_by_id(
    session: AsyncSession, result_id: uuid.UUID
) -> ScreeningResult | None:
    return await session.get(ScreeningResult, result_id)


async def list_results_by_baby(
    session: AsyncSession, baby_id: uuid.UUID
) -> list[ScreeningResult]:
    result = await session.execute(
        select(ScreeningResult)
        .where(ScreeningResult.baby_id == baby_id)
        .order_by(ScreeningResult.received_at.desc())
    )
    return list(result.scalars().all())


async def count_results(
    session: AsyncSession, result_type: ResultType | None = None
) -> int:
    stmt = select(func.count(ScreeningResult.id))
    if result_type:
        stmt = stmt.where(ScreeningResult.result_type == result_type)
    result = await session.execute(stmt)
    return result.scalar_one()


async def create_screening_result(
    session: AsyncSession,
    baby_id: uuid.UUID,
    result_type: ResultType,
    disease_code: str | None = None,
    disease_name: str | None = None,
    source: str = "api",
) -> ScreeningResult:
    screening = ScreeningResult(
        baby_id=baby_id,
        result_type=result_type,
        disease_code=disease_code,
        disease_name=disease_name,
        source=source,
    )
    session.add(screening)
    await session.commit()
    await session.refresh(screening)

    # If positive or repeat_needed, create notification
    if result_type in (ResultType.positive, ResultType.repeat_needed):
        from src.models.baby import Baby

        baby = await session.get(Baby, baby_id)
        if baby:
            baby_name = baby.name or "вашего ребёнка"
            if result_type == ResultType.positive:
                text = (
                    f"Внимание! Получены результаты скрининга {baby_name}.\n"
                    f"Диагноз: {disease_name or disease_code or 'требуется консультация'}.\n"
                    f"Пожалуйста, свяжитесь с вашим педиатром как можно скорее."
                )
            else:
                text = (
                    f"Результаты скрининга {baby_name} требуют повторного анализа.\n"
                    f"Пожалуйста, свяжитесь с вашим педиатром для назначения повторного забора крови."
                )

            notification = Notification(
                parent_id=baby.parent_id,
                screening_result_id=screening.id,
                message_text=text,
                status=NotificationStatus.pending,
            )
            session.add(notification)
            await session.commit()

    return screening
