import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.deps import get_current_user, get_db
from src.models.user import User
from src.services.baby_service import get_baby_by_id, list_babies, count_babies

router = APIRouter(prefix="/api/babies", tags=["babies"])


class BabyResponse(BaseModel):
    id: uuid.UUID
    parent_id: uuid.UUID
    name: str | None
    birth_date: str | None
    birth_hospital: str | None
    sample_collected: bool

    model_config = {"from_attributes": True}


class BabyListResponse(BaseModel):
    items: list[BabyResponse]
    total: int


@router.get("/", response_model=BabyListResponse)
async def get_babies(
    offset: int = 0,
    limit: int = 50,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    babies = await list_babies(session, offset=offset, limit=limit)
    total = await count_babies(session)
    items = [
        BabyResponse(
            id=b.id,
            parent_id=b.parent_id,
            name=b.name,
            birth_date=b.birth_date.isoformat() if b.birth_date else None,
            birth_hospital=b.birth_hospital,
            sample_collected=b.sample_collected,
        )
        for b in babies
    ]
    return BabyListResponse(items=items, total=total)


@router.get("/{baby_id}", response_model=BabyResponse)
async def get_baby(
    baby_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    baby = await get_baby_by_id(session, baby_id)
    if not baby:
        raise HTTPException(status_code=404, detail="Baby not found")
    return BabyResponse(
        id=baby.id,
        parent_id=baby.parent_id,
        name=baby.name,
        birth_date=baby.birth_date.isoformat() if baby.birth_date else None,
        birth_hospital=baby.birth_hospital,
        sample_collected=baby.sample_collected,
    )
