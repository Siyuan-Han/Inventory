from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from models import Dress, DressOrder, Sale
from schemas import ORDER_STATUSES, STATUS_TIMESTAMP_FIELD, OrderCreate, OrderRead, OrderUpdate

router = APIRouter(prefix="/orders", tags=["orders"])


def utcnow() -> datetime:
    """Naive UTC, matching the `timestamp without time zone` columns."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


def validate_status(status: str) -> str:
    if status not in ORDER_STATUSES:
        raise HTTPException(
            status_code=422,
            detail=f"status must be one of: {', '.join(ORDER_STATUSES)}",
        )
    return status


def stamp_status(order: DressOrder, status: str, when: Optional[datetime] = None) -> None:
    """Record the moment an order reached `status`, if not already recorded.

    Statuses earlier in the pipeline are backfilled too, so a jump straight to
    'received' still leaves a usable timeline. `when` lets a status be
    recorded for a date other than today, e.g. marking a shipment received a
    few days after the fact.
    """
    when = when or utcnow()
    for step in ORDER_STATUSES[: ORDER_STATUSES.index(status) + 1]:
        field = STATUS_TIMESTAMP_FIELD[step]
        if getattr(order, field) is None:
            setattr(order, field, when)


async def get_or_404(db: AsyncSession, order_id: int) -> DressOrder:
    order = await db.get(DressOrder, order_id)
    if order is None:
        raise HTTPException(status_code=404, detail=f"Order {order_id} not found")
    return order


@router.get("", response_model=List[OrderRead])
async def list_orders(
    db: AsyncSession = Depends(get_db),
    dress_id: Optional[int] = Query(default=None),
    status: Optional[str] = Query(default=None),
) -> List[DressOrder]:
    stmt = select(DressOrder).order_by(DressOrder.order_date.desc(), DressOrder.id.desc())
    if dress_id is not None:
        stmt = stmt.where(DressOrder.dress_id == dress_id)
    if status:
        stmt = stmt.where(DressOrder.status == validate_status(status))
    return list((await db.scalars(stmt)).all())


@router.post("", response_model=OrderRead, status_code=201)
async def create_order(payload: OrderCreate, db: AsyncSession = Depends(get_db)) -> DressOrder:
    if await db.get(Dress, payload.dress_id) is None:
        raise HTTPException(status_code=404, detail=f"Dress {payload.dress_id} not found")

    order = DressOrder(**payload.model_dump())
    stamp_status(order, validate_status(order.status))
    db.add(order)
    await db.commit()
    await db.refresh(order)
    return order


@router.get("/{order_id}", response_model=OrderRead)
async def get_order(order_id: int, db: AsyncSession = Depends(get_db)) -> DressOrder:
    return await get_or_404(db, order_id)


@router.put("/{order_id}", response_model=OrderRead)
async def update_order(
    order_id: int, payload: OrderUpdate, db: AsyncSession = Depends(get_db)
) -> DressOrder:
    order = await get_or_404(db, order_id)
    changes = payload.model_dump(exclude_unset=True)

    new_status = changes.pop("status", None)
    status_date = changes.pop("status_date", None)
    for field, value in changes.items():
        setattr(order, field, value)
    if new_status is not None:
        order.status = validate_status(new_status)
        when = datetime.combine(status_date, datetime.min.time()) if status_date else None
        stamp_status(order, order.status, when=when)

    await db.commit()
    await db.refresh(order)
    return order


@router.delete("/{order_id}", status_code=204)
async def delete_order(order_id: int, db: AsyncSession = Depends(get_db)) -> None:
    order = await get_or_404(db, order_id)
    # sale.order_id has no ON DELETE action; unlink any sales instead of
    # blowing up, since a recorded sale shouldn't disappear with the order.
    await db.execute(update(Sale).where(Sale.order_id == order_id).values(order_id=None))
    await db.delete(order)
    await db.commit()
