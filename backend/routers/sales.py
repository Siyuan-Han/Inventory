from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from models import Dress, DressOrder, Sale
from payments import check_cash_amount, require_received_by, validate_partner
from routers.dresses import utcnow
from schemas import SaleCreate, SaleRead, SaleUpdate

router = APIRouter(prefix="/sales", tags=["sales"])


async def get_or_404(db: AsyncSession, sale_id: int) -> Sale:
    sale = await db.get(Sale, sale_id)
    if sale is None:
        raise HTTPException(status_code=404, detail=f"Sale {sale_id} not found")
    return sale


@router.get("", response_model=List[SaleRead])
async def list_sales(
    db: AsyncSession = Depends(get_db),
    dress_id: Optional[int] = Query(default=None),
) -> List[Sale]:
    stmt = select(Sale).order_by(Sale.sale_date.desc(), Sale.id.desc())
    if dress_id is not None:
        stmt = stmt.where(Sale.dress_id == dress_id)
    return list((await db.scalars(stmt)).all())


@router.post("", response_model=SaleRead, status_code=201)
async def create_sale(payload: SaleCreate, db: AsyncSession = Depends(get_db)) -> Sale:
    dress = await db.get(Dress, payload.dress_id)
    if dress is None:
        raise HTTPException(status_code=404, detail=f"Dress {payload.dress_id} not found")

    if payload.order_id is not None:
        order = await db.get(DressOrder, payload.order_id)
        if order is None:
            raise HTTPException(status_code=404, detail=f"Order {payload.order_id} not found")
        if order.dress_id != payload.dress_id:
            raise HTTPException(
                status_code=422, detail="That order belongs to a different dress"
            )

    check_cash_amount(payload.cash_amount, payload.sale_price)
    data = payload.model_dump()
    if payload.cash_amount is not None:
        # cash_amount is authoritative once set — derive is_cash from it
        # instead of trusting a client-sent value that could disagree.
        data["is_cash"] = payload.sale_price is not None and payload.cash_amount >= payload.sale_price

    if data.get("received_by") is not None:
        data["received_by"] = validate_partner(data["received_by"])
    require_received_by(data["is_cash"], data.get("cash_amount"), data.get("received_by"))

    sale = Sale(**data)
    db.add(sale)

    # A secondhand piece is one of a kind — once it's sold there's nothing
    # left to track actively, so it moves straight to the archive. Still
    # restorable by hand for the rare return.
    if dress.category == "secondhand" and dress.archived_at is None:
        dress.archived_at = utcnow()

    await db.commit()
    await db.refresh(sale)
    return sale


@router.put("/{sale_id}", response_model=SaleRead)
async def update_sale(
    sale_id: int, payload: SaleUpdate, db: AsyncSession = Depends(get_db)
) -> Sale:
    sale = await get_or_404(db, sale_id)
    changes = payload.model_dump(exclude_unset=True)
    for field, value in changes.items():
        setattr(sale, field, value)

    if "cash_amount" in changes and sale.cash_amount is not None:
        check_cash_amount(sale.cash_amount, sale.sale_price)
        if "is_cash" not in changes:
            sale.is_cash = sale.sale_price is not None and sale.cash_amount >= sale.sale_price
    if "received_by" in changes and sale.received_by is not None:
        validate_partner(sale.received_by)
    # Only enforce on rows whose payment fields this request actually
    # touched — an unrelated edit (e.g. notes) on a sale that predates this
    # field, or was left card-only, shouldn't suddenly start 422ing.
    if changes.keys() & {"is_cash", "cash_amount", "received_by"}:
        require_received_by(sale.is_cash, sale.cash_amount, sale.received_by)

    await db.commit()
    await db.refresh(sale)
    return sale


@router.delete("/{sale_id}", status_code=204)
async def delete_sale(sale_id: int, db: AsyncSession = Depends(get_db)) -> None:
    sale = await get_or_404(db, sale_id)
    await db.delete(sale)
    await db.commit()
