from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from database import get_db
from models import Dress
from rollups import dress_rollup
from schemas import DressCreate, DressDetail, DressRead, DressUpdate

router = APIRouter(prefix="/dresses", tags=["dresses"])


def to_read(dress: Dress) -> DressRead:
    base = DressRead.model_validate(dress).model_dump()
    base.update(dress_rollup(dress))
    return DressRead(**base)


def to_detail(dress: Dress) -> DressDetail:
    base = DressDetail.model_validate(dress).model_dump()
    base.update(dress_rollup(dress))
    return DressDetail(**base)


async def load_dress(db: AsyncSession, dress_id: int) -> Dress:
    """Fetch one dress with its orders and sales freshly loaded."""
    stmt = (
        select(Dress)
        .options(selectinload(Dress.orders), selectinload(Dress.sales))
        .where(Dress.id == dress_id)
        .execution_options(populate_existing=True)
    )
    dress = (await db.scalars(stmt)).first()
    if dress is None:
        raise HTTPException(status_code=404, detail=f"Dress {dress_id} not found")
    return dress


@router.get("", response_model=List[DressRead])
async def list_dresses(
    db: AsyncSession = Depends(get_db),
    search: Optional[str] = Query(default=None, description="Match code, style or supplier"),
) -> List[DressRead]:
    stmt = (
        select(Dress)
        .options(selectinload(Dress.orders), selectinload(Dress.sales))
        .order_by(Dress.dress_code)
    )
    if search and search.strip():
        pattern = f"%{search.strip()}%"
        stmt = stmt.where(
            or_(
                Dress.dress_code.ilike(pattern),
                Dress.style_name.ilike(pattern),
                Dress.supplier.ilike(pattern),
            )
        )
    return [to_read(d) for d in (await db.scalars(stmt)).all()]


@router.post("", response_model=DressDetail, status_code=201)
async def create_dress(payload: DressCreate, db: AsyncSession = Depends(get_db)) -> DressDetail:
    dress = Dress(**payload.model_dump())
    db.add(dress)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=409, detail=f"Dress code '{payload.dress_code}' already exists"
        )
    return to_detail(await load_dress(db, dress.id))


@router.get("/{dress_id}", response_model=DressDetail)
async def get_dress(dress_id: int, db: AsyncSession = Depends(get_db)) -> DressDetail:
    return to_detail(await load_dress(db, dress_id))


@router.put("/{dress_id}", response_model=DressDetail)
async def update_dress(
    dress_id: int, payload: DressUpdate, db: AsyncSession = Depends(get_db)
) -> DressDetail:
    dress = await load_dress(db, dress_id)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(dress, field, value)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=409, detail="That dress code is already taken")
    return to_detail(await load_dress(db, dress_id))


@router.delete("/{dress_id}", status_code=204)
async def delete_dress(dress_id: int, db: AsyncSession = Depends(get_db)) -> None:
    dress = await db.get(Dress, dress_id)
    if dress is None:
        raise HTTPException(status_code=404, detail=f"Dress {dress_id} not found")
    await db.delete(dress)
    await db.commit()
