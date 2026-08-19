import logging
import re
from collections import Counter
from contextlib import asynccontextmanager
from datetime import date

from typing import Optional

from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from config import settings
from database import get_db, init_db
from models import Dress
from rollups import dress_rollup
from routers import dresses, orders, sales
from schemas import (
    ORDER_STATUSES,
    STATUS_LABELS,
    STATUS_TIMESTAMP_FIELD,
    DashboardStats,
    MonthlyStats,
)


logger = logging.getLogger("uvicorn.error")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # A bad DATABASE_URL should surface as a clear log line and 500s on the
    # data routes, not as a server that refuses to start at all.
    try:
        await init_db()
    except Exception as exc:  # noqa: BLE001
        logger.error("Could not reach the database: %s", exc)
        logger.error("Check DATABASE_URL in backend/.env — the API is up but has no data.")
    yield


app = FastAPI(
    title="Wedding Dress Inventory API",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_origin_regex=r"http://(localhost|127\.0\.0\.1|192\.168\.\d+\.\d+):\d+",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(dresses.router)
app.include_router(orders.router)
app.include_router(sales.router)


@app.get("/health", tags=["meta"])
async def health() -> dict:
    return {"status": "ok"}


@app.get("/statuses", tags=["meta"])
async def statuses() -> list:
    """The order pipeline, in order, for the frontend to render."""
    return [
        {"value": s, "label": STATUS_LABELS[s], "field": STATUS_TIMESTAMP_FIELD[s]}
        for s in ORDER_STATUSES
    ]


@app.get("/stats", response_model=DashboardStats, tags=["meta"])
async def stats(db: AsyncSession = Depends(get_db)) -> DashboardStats:
    stmt = (
        select(Dress)
        .options(selectinload(Dress.orders), selectinload(Dress.sales))
        .where(Dress.archived_at.is_(None))
    )
    all_dresses = (await db.scalars(stmt)).all()

    totals = DashboardStats(total_dresses=len(all_dresses))
    breakdown: Counter = Counter()

    for dress in all_dresses:
        roll = dress_rollup(dress)
        totals.total_ordered += roll["total_ordered"]
        totals.total_received += roll["total_received"]
        totals.total_sold += roll["total_sold"]
        totals.in_stock += roll["in_stock"]
        totals.pending_orders += roll["pending_orders"]
        totals.total_revenue += roll["total_revenue"]
        totals.total_cost += roll["total_cost"]
        totals.cash_sales += sum(1 for s in dress.sales if s.is_cash)
        for order in dress.orders:
            breakdown[order.status or "ordered"] += 1

    totals.profit = totals.total_revenue - totals.total_cost
    totals.status_breakdown = {s: breakdown.get(s, 0) for s in ORDER_STATUSES}
    return totals


MONTH_PATTERN = re.compile(r"^\d{4}-(0[1-9]|1[0-2])$")


@app.get("/stats/monthly", response_model=MonthlyStats, tags=["meta"])
async def monthly_stats(
    db: AsyncSession = Depends(get_db),
    month: Optional[str] = Query(default=None, description="YYYY-MM, defaults to the current month"),
) -> MonthlyStats:
    if month is None:
        today = date.today()
        month = f"{today.year:04d}-{today.month:02d}"
    elif not MONTH_PATTERN.match(month):
        raise HTTPException(status_code=422, detail="month must be formatted as YYYY-MM")

    year, mon = (int(part) for part in month.split("-"))
    start = date(year, mon, 1)
    end = date(year + 1, 1, 1) if mon == 12 else date(year, mon + 1, 1)

    # Historical sales/orders count toward the month they happened in even if
    # the dress has since been archived.
    stmt = select(Dress).options(selectinload(Dress.orders), selectinload(Dress.sales))
    all_dresses = (await db.scalars(stmt)).all()

    result = MonthlyStats(month=month)
    for dress in all_dresses:
        for sale in dress.sales:
            if start <= sale.sale_date < end:
                result.sales_count += 1
                result.revenue += sale.sale_price or 0
                result.cash_sales += 1 if sale.is_cash else 0
        for order in dress.orders:
            if start <= order.order_date < end:
                result.orders_count += 1
                unit_cost = order.unit_cost if order.unit_cost is not None else dress.base_cost
                result.cost += (unit_cost or 0) * (order.quantity or 0)

    result.profit = result.revenue - result.cost
    return result
