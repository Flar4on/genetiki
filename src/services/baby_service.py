import uuid
from datetime import date

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.baby import Baby


async def get_baby_by_id(session: AsyncSession, baby_id: uuid.UUID) -> Baby | None:
    return await session.get(Baby, baby_id)


async def list_babies_by_parent(session: AsyncSession, parent_id: uuid.UUID) -> list[Baby]:
    result = await session.execute(
        select(Baby).where(Baby.parent_id == parent_id).order_by(Baby.created_at.desc())
    )
    return list(result.scalars().all())


async def list_babies(session: AsyncSession, offset: int = 0, limit: int = 50) -> list[Baby]:
    result = await session.execute(
        select(Baby).offset(offset).limit(limit).order_by(Baby.created_at.desc())
    )
    return list(result.scalars().all())


async def count_babies(session: AsyncSession) -> int:
    result = await session.execute(select(func.count(Baby.id)))
    return result.scalar_one()


async def create_baby(
    session: AsyncSession,
    parent_id: uuid.UUID,
    name: str,
    birth_date: date,
    birth_hospital: str,
) -> Baby:
    baby = Baby(
        parent_id=parent_id,
        name=name,
        birth_date=birth_date,
        birth_hospital=birth_hospital,
    )
    session.add(baby)
    await session.commit()
    await session.refresh(baby)
    return baby
