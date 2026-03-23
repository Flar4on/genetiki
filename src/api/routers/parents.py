import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.deps import get_current_user, get_db
from src.models.user import User
from src.services.parent_service import (
    count_parents,
    get_decrypted_name,
    get_decrypted_phone,
    get_parent_by_id,
    list_parents,
)

router = APIRouter(prefix="/api/parents", tags=["parents"])


class ParentResponse(BaseModel):
    id: uuid.UUID
    telegram_id: int
    full_name: str
    phone: str
    region: str | None
    consent_given: bool
    is_active: bool

    model_config = {"from_attributes": True}


class ParentListResponse(BaseModel):
    items: list[ParentResponse]
    total: int


@router.get("/", response_model=ParentListResponse)
async def get_parents(
    region: str | None = None,
    offset: int = 0,
    limit: int = 50,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    parents = await list_parents(session, region=region, offset=offset, limit=limit)
    total = await count_parents(session, region=region)

    items = []
    for p in parents:
        items.append(
            ParentResponse(
                id=p.id,
                telegram_id=p.telegram_id,
                full_name=get_decrypted_name(p),
                phone=get_decrypted_phone(p),
                region=p.region,
                consent_given=p.consent_given,
                is_active=p.is_active,
            )
        )

    return ParentListResponse(items=items, total=total)


@router.get("/{parent_id}", response_model=ParentResponse)
async def get_parent(
    parent_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    parent = await get_parent_by_id(session, parent_id)
    if not parent:
        raise HTTPException(status_code=404, detail="Parent not found")

    return ParentResponse(
        id=parent.id,
        telegram_id=parent.telegram_id,
        full_name=get_decrypted_name(parent),
        phone=get_decrypted_phone(parent),
        region=parent.region,
        consent_given=parent.consent_given,
        is_active=parent.is_active,
    )
