from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from models import Dress, DressOrder, Sale
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
    if await db.get(Dress, payload.dress_id) is None:
        raise HTTPException(status_code=404, detail=f"Dress {payload.dress_id} not found")

    if payload.order_id is not None:
        order = await db.get(DressOrder, payload.order_id)
        if order is None:
            raise HTTPException(status_code=404, detail=f"Order {payload.order_id} not found")
        if order.dress_id != payload.dress_id:
            raise HTTPException(
                status_code=422, detail="That order belongs to a different dress"
            )

    sale = Sale(**payload.model_dump())
    db.add(sale)
    await db.commit()
    await db.refresh(sale)
    return sale


@router.put("/{sale_id}", response_model=SaleRead)
async def update_sale(
    sale_id: int, payload: SaleUpdate, db: AsyncSession = Depends(get_db)
) -> Sale:
    sale = await get_or_404(db, sale_id)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(sale, field, value)
    await db.commit()
    await db.refresh(sale)
    return sale


@router.delete("/{sale_id}", status_code=204)
async def delete_sale(sale_id: int, db: AsyncSession = Depends(get_db)) -> None:
    sale = await get_or_404(db, sale_id)
    await db.delete(sale)
    await db.commit()
