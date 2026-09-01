from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from models import Settlement
from payments import validate_partner
from schemas import SettlementCreate, SettlementRead

router = APIRouter(prefix="/settlements", tags=["settlements"])


@router.get("", response_model=List[SettlementRead])
async def list_settlements(db: AsyncSession = Depends(get_db)) -> List[Settlement]:
    stmt = select(Settlement).order_by(Settlement.settlement_date.desc(), Settlement.id.desc())
    return list((await db.scalars(stmt)).all())


@router.post("", response_model=SettlementRead, status_code=201)
async def create_settlement(
    payload: SettlementCreate, db: AsyncSession = Depends(get_db)
) -> Settlement:
    validate_partner(payload.paid_by)
    validate_partner(payload.paid_to)
    if payload.paid_by == payload.paid_to:
        raise HTTPException(status_code=422, detail="paid_by and paid_to must differ")

    settlement = Settlement(**payload.model_dump())
    db.add(settlement)
    await db.commit()
    await db.refresh(settlement)
    return settlement


@router.delete("/{settlement_id}", status_code=204)
async def delete_settlement(settlement_id: int, db: AsyncSession = Depends(get_db)) -> None:
    settlement = await db.get(Settlement, settlement_id)
    if settlement is None:
        raise HTTPException(status_code=404, detail=f"Settlement {settlement_id} not found")
    await db.delete(settlement)
    await db.commit()
