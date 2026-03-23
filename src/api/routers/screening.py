import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.deps import get_db, verify_api_key
from src.models.screening import ResultType
from src.services.screening_service import (
    create_screening_result,
    get_result_by_id,
    list_results_by_baby,
)

router = APIRouter(prefix="/api/screening", tags=["screening"])


class ScreeningResultCreate(BaseModel):
    baby_id: uuid.UUID
    result_type: ResultType
    disease_code: str | None = None
    disease_name: str | None = None
    source: str = "api"


class ScreeningResultResponse(BaseModel):
    id: uuid.UUID
    baby_id: uuid.UUID
    result_type: ResultType
    disease_code: str | None
    disease_name: str | None
    source: str | None

    model_config = {"from_attributes": True}


@router.post(
    "/results",
    response_model=ScreeningResultResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(verify_api_key)],
)
async def add_screening_result(
    data: ScreeningResultCreate,
    session: AsyncSession = Depends(get_db),
):
    result = await create_screening_result(
        session=session,
        baby_id=data.baby_id,
        result_type=data.result_type,
        disease_code=data.disease_code,
        disease_name=data.disease_name,
        source=data.source,
    )
    return result


@router.get(
    "/results",
    response_model=list[ScreeningResultResponse],
    dependencies=[Depends(verify_api_key)],
)
async def get_screening_results(
    baby_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
):
    return await list_results_by_baby(session, baby_id)


@router.get(
    "/results/{result_id}",
    response_model=ScreeningResultResponse,
    dependencies=[Depends(verify_api_key)],
)
async def get_screening_result(
    result_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
):
    result = await get_result_by_id(session, result_id)
    if not result:
        raise HTTPException(status_code=404, detail="Result not found")
    return result
