from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from models import Dress, TryOn
from payments import check_cash_amount, require_received_by, validate_partner
from schemas import TryOnCreate, TryOnRead, TryOnUpdate

router = APIRouter(prefix="/tryons", tags=["tryons"])


async def get_or_404(db: AsyncSession, tryon_id: int) -> TryOn:
    tryon = await db.get(TryOn, tryon_id)
    if tryon is None:
        raise HTTPException(status_code=404, detail=f"Try-on {tryon_id} not found")
    return tryon


@router.get("", response_model=List[TryOnRead])
async def list_tryons(
    db: AsyncSession = Depends(get_db),
    dress_id: Optional[int] = Query(default=None),
) -> List[TryOn]:
    stmt = select(TryOn).order_by(TryOn.tryon_date.desc(), TryOn.id.desc())
    if dress_id is not None:
        stmt = stmt.where(TryOn.dress_id == dress_id)
    return list((await db.scalars(stmt)).all())


@router.post("", response_model=TryOnRead, status_code=201)
async def create_tryon(payload: TryOnCreate, db: AsyncSession = Depends(get_db)) -> TryOn:
    if await db.get(Dress, payload.dress_id) is None:
        raise HTTPException(status_code=404, detail=f"Dress {payload.dress_id} not found")

    check_cash_amount(payload.cash_amount, payload.fee)
    data = payload.model_dump()
    if payload.cash_amount is not None:
        # cash_amount is authoritative once set — derive is_cash from it
        # instead of trusting a client-sent value that could disagree.
        data["is_cash"] = payload.fee is not None and payload.cash_amount >= payload.fee

    if data.get("received_by") is not None:
        data["received_by"] = validate_partner(data["received_by"])
    require_received_by(data["is_cash"], data.get("cash_amount"), data.get("received_by"))

    tryon = TryOn(**data)
    db.add(tryon)
    await db.commit()
    await db.refresh(tryon)
    return tryon


@router.put("/{tryon_id}", response_model=TryOnRead)
async def update_tryon(
    tryon_id: int, payload: TryOnUpdate, db: AsyncSession = Depends(get_db)
) -> TryOn:
    tryon = await get_or_404(db, tryon_id)
    changes = payload.model_dump(exclude_unset=True)
    for field, value in changes.items():
        setattr(tryon, field, value)

    if "cash_amount" in changes and tryon.cash_amount is not None:
        check_cash_amount(tryon.cash_amount, tryon.fee)
        if "is_cash" not in changes:
            tryon.is_cash = tryon.fee is not None and tryon.cash_amount >= tryon.fee
    if "received_by" in changes and tryon.received_by is not None:
        validate_partner(tryon.received_by)
    if changes.keys() & {"is_cash", "cash_amount", "received_by"}:
        require_received_by(tryon.is_cash, tryon.cash_amount, tryon.received_by)

    await db.commit()
    await db.refresh(tryon)
    return tryon


@router.delete("/{tryon_id}", status_code=204)
async def delete_tryon(tryon_id: int, db: AsyncSession = Depends(get_db)) -> None:
    tryon = await get_or_404(db, tryon_id)
    await db.delete(tryon)
    await db.commit()
