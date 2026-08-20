import re
from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import delete, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from database import get_db
from models import Dress, DressOrder, Sale
from rollups import dress_rollup
from schemas import ORDER_STATUSES, DressCreate, DressDetail, DressRead, DressUpdate, NextDressCode

router = APIRouter(prefix="/dresses", tags=["dresses"])

CODE_PREFIX = "WD"
CODE_PATTERN = re.compile(rf"^{CODE_PREFIX}(\d+)$")


def utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


async def next_code(db: AsyncSession) -> str:
    """The next sequential WDxxx code, based on the highest one in use."""
    codes = (await db.scalars(select(Dress.dress_code))).all()
    highest = 0
    for code in codes:
        match = CODE_PATTERN.match(code or "")
        if match:
            highest = max(highest, int(match.group(1)))
    return f"{CODE_PREFIX}{highest + 1:03d}"


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


@router.get("/next-code", response_model=NextDressCode)
async def preview_next_code(db: AsyncSession = Depends(get_db)) -> NextDressCode:
    """A preview of the code the next dress will get. Not reserved."""
    return NextDressCode(dress_code=await next_code(db))


@router.get("/suppliers", response_model=List[str])
async def list_suppliers(db: AsyncSession = Depends(get_db)) -> List[str]:
    """Distinct supplier names in use, for populating a filter dropdown."""
    stmt = (
        select(Dress.supplier)
        .where(Dress.supplier.isnot(None), Dress.supplier != "")
        .distinct()
        .order_by(Dress.supplier)
    )
    return list((await db.scalars(stmt)).all())


@router.get("", response_model=List[DressRead])
async def list_dresses(
    db: AsyncSession = Depends(get_db),
    search: Optional[str] = Query(default=None, description="Match code, style or supplier"),
    archived: bool = Query(default=False, description="List archived dresses instead of active ones"),
    supplier: Optional[str] = Query(default=None, description="Exact supplier match"),
    status: Optional[str] = Query(
        default=None, description="Only dresses whose most recent order is at this status"
    ),
) -> List[DressRead]:
    if status is not None and status not in ORDER_STATUSES:
        raise HTTPException(
            status_code=422, detail=f"status must be one of: {', '.join(ORDER_STATUSES)}"
        )
    stmt = (
        select(Dress)
        .options(selectinload(Dress.orders), selectinload(Dress.sales))
        .order_by(Dress.dress_code)
    )
    stmt = stmt.where(Dress.archived_at.isnot(None) if archived else Dress.archived_at.is_(None))
    if supplier:
        stmt = stmt.where(Dress.supplier == supplier)
    if search and search.strip():
        pattern = f"%{search.strip()}%"
        stmt = stmt.where(
            or_(
                Dress.dress_code.ilike(pattern),
                Dress.style_name.ilike(pattern),
                Dress.supplier.ilike(pattern),
            )
        )
    results = [to_read(d) for d in (await db.scalars(stmt)).all()]
    if status is not None:
        results = [d for d in results if d.latest_status == status]
    return results


@router.post("", response_model=DressDetail, status_code=201)
async def create_dress(payload: DressCreate, db: AsyncSession = Depends(get_db)) -> DressDetail:
    data = payload.model_dump()

    # Retry a handful of times in case two people add a dress at once and
    # both compute the same "next" code before either commits.
    for attempt in range(5):
        data["dress_code"] = payload.dress_code or await next_code(db)
        dress = Dress(**data)
        db.add(dress)
        try:
            await db.commit()
            break
        except IntegrityError:
            await db.rollback()
            if payload.dress_code:
                raise HTTPException(
                    status_code=409, detail=f"Dress code '{payload.dress_code}' already exists"
                )
    else:
        raise HTTPException(status_code=500, detail="Could not assign a dress code, try again")

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


@router.post("/{dress_id}/archive", response_model=DressDetail)
async def archive_dress(dress_id: int, db: AsyncSession = Depends(get_db)) -> DressDetail:
    dress = await load_dress(db, dress_id)
    if dress.archived_at is None:
        dress.archived_at = utcnow()
        await db.commit()
    return to_detail(await load_dress(db, dress_id))


@router.post("/{dress_id}/restore", response_model=DressDetail)
async def restore_dress(dress_id: int, db: AsyncSession = Depends(get_db)) -> DressDetail:
    dress = await load_dress(db, dress_id)
    dress.archived_at = None
    await db.commit()
    return to_detail(await load_dress(db, dress_id))


@router.delete("/{dress_id}", status_code=204)
async def delete_dress(dress_id: int, db: AsyncSession = Depends(get_db)) -> None:
    exists = await db.scalar(select(Dress.id).where(Dress.id == dress_id))
    if exists is None:
        raise HTTPException(status_code=404, detail=f"Dress {dress_id} not found")

    # sale.order_id has no ON DELETE action, so children must go in dependency
    # order: sales, then orders, then the dress itself.
    await db.execute(delete(Sale).where(Sale.dress_id == dress_id))
    await db.execute(delete(DressOrder).where(DressOrder.dress_id == dress_id))
    await db.execute(delete(Dress).where(Dress.id == dress_id))
    await db.commit()
