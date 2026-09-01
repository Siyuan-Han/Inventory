import logging
import re
from collections import Counter
from contextlib import asynccontextmanager
from datetime import date
from decimal import Decimal

from typing import Optional

from fastapi import APIRouter, Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from config import settings
from database import get_db, init_db
from models import Dress, Sale, Settlement, TryOn
from payments import PARTNER_LABELS, PARTNERS
from rollups import dress_rollup, sale_cost_map, sale_payment_split, tryon_payment_split
from routers import dresses, orders, sales, settlements, tryons
from schemas import (
    ORDER_STATUSES,
    STATUS_LABELS,
    STATUS_TIMESTAMP_FIELD,
    DashboardStats,
    MonthlyStats,
    PartnerCashPosition,
    SettlementSummary,
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

# Routes live under /api so a single Vercel deployment can route "/api/*"
# to this service and everything else to the Vue frontend — the frontend's
# own client-side routes (e.g. /dresses/:id) would otherwise collide with
# these same paths. See vercel.json at the repo root.
API_PREFIX = "/api"

app.include_router(dresses.router, prefix=API_PREFIX)
app.include_router(orders.router, prefix=API_PREFIX)
app.include_router(sales.router, prefix=API_PREFIX)
app.include_router(tryons.router, prefix=API_PREFIX)
app.include_router(settlements.router, prefix=API_PREFIX)

meta_router = APIRouter(prefix=API_PREFIX, tags=["meta"])


@meta_router.get("/health")
async def health() -> dict:
    return {"status": "ok"}


@meta_router.get("/statuses")
async def statuses() -> list:
    """The order pipeline, in order, for the frontend to render."""
    return [
        {"value": s, "label": STATUS_LABELS[s], "field": STATUS_TIMESTAMP_FIELD[s]}
        for s in ORDER_STATUSES
    ]


@meta_router.get("/partners")
async def partners() -> list:
    """The two business partners, for the frontend to render as options."""
    return [{"value": p, "label": PARTNER_LABELS[p]} for p in PARTNERS]


@meta_router.get("/stats", response_model=DashboardStats)
async def stats(db: AsyncSession = Depends(get_db)) -> DashboardStats:
    # Financial totals (revenue/cost/profit/cash vs card) are permanent
    # history and include archived dresses; inventory-workload figures
    # (pending orders, in stock, the stage breakdown) reflect active
    # dresses only, since that's the current work.
    stmt = select(Dress).options(
        selectinload(Dress.orders), selectinload(Dress.sales), selectinload(Dress.try_ons)
    )
    all_dresses = (await db.scalars(stmt)).all()

    totals = DashboardStats()
    breakdown: Counter = Counter()

    for dress in all_dresses:
        roll = dress_rollup(dress)
        totals.total_sold += roll["total_sold"]
        totals.total_revenue += roll["total_revenue"]
        totals.tryon_revenue += roll["tryon_revenue"]
        totals.total_cost += roll["total_cost"]
        totals.cost_of_goods_sold += roll["cost_of_goods_sold"]
        for sale in dress.sales:
            cash, card = sale_payment_split(sale)
            totals.cash_revenue += cash
            totals.card_revenue += card
            totals.cash_sales += 1 if sale.is_cash else 0
        for tryon in dress.try_ons:
            # cash_sales/total_sold stay scoped to actual sales — try-on
            # volume is tracked separately via tryon_count.
            totals.tryon_count += 1
            cash, card = tryon_payment_split(tryon)
            totals.cash_revenue += cash
            totals.card_revenue += card

        if dress.archived_at is None:
            totals.total_dresses += 1
            totals.total_ordered += roll["total_ordered"]
            totals.total_received += roll["total_received"]
            totals.in_stock += roll["in_stock"]
            totals.inventory_value += roll["inventory_value"]
            totals.pending_orders += roll["pending_orders"]
            for order in dress.orders:
                breakdown[order.status or "ordered"] += 1

    totals.profit = totals.total_revenue - totals.cost_of_goods_sold + totals.tryon_revenue
    totals.status_breakdown = {s: breakdown.get(s, 0) for s in ORDER_STATUSES}
    return totals


MONTH_PATTERN = re.compile(r"^\d{4}-(0[1-9]|1[0-2])$")


@meta_router.get("/stats/monthly", response_model=MonthlyStats)
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
    stmt = select(Dress).options(
        selectinload(Dress.orders), selectinload(Dress.sales), selectinload(Dress.try_ons)
    )
    all_dresses = (await db.scalars(stmt)).all()

    result = MonthlyStats(month=month)
    for dress in all_dresses:
        sale_costs = sale_cost_map(dress)
        for sale in dress.sales:
            if start <= sale.sale_date < end:
                result.sales_count += 1
                result.revenue += sale.sale_price or 0
                result.cash_sales += 1 if sale.is_cash else 0
                cash, card = sale_payment_split(sale)
                result.cash_revenue += cash
                result.card_revenue += card
                result.cost += sale_costs.get(sale.id, 0)
        for tryon in dress.try_ons:
            if start <= tryon.tryon_date < end:
                result.tryon_count += 1
                result.tryon_revenue += tryon.fee or 0
                cash, card = tryon_payment_split(tryon)
                result.cash_revenue += cash
                result.card_revenue += card
        for order in dress.orders:
            if start <= order.order_date < end:
                result.orders_count += 1
                unit_cost = order.unit_cost if order.unit_cost is not None else dress.base_cost
                result.inventory_spend += (unit_cost or 0) * (order.quantity or 0)

    result.profit = result.revenue - result.cost + result.tryon_revenue
    return result


@meta_router.get("/settlement/summary", response_model=SettlementSummary)
async def settlement_summary(db: AsyncSession = Depends(get_db)) -> SettlementSummary:
    """Each partner's net cash position and what's owed to equalize —
    replaces the manual spreadsheet's (Camille - Zoe) / 2 reconciliation.
    """
    sales = (await db.scalars(select(Sale))).all()
    tryons = (await db.scalars(select(TryOn))).all()
    all_settlements = (await db.scalars(select(Settlement))).all()

    collected = {p: Decimal("0") for p in PARTNERS}
    unattributed = Decimal("0")
    for sale in sales:
        cash, _ = sale_payment_split(sale)
        if cash <= 0:
            continue
        if sale.received_by in PARTNERS:
            collected[sale.received_by] += cash
        else:
            unattributed += cash
    for tryon in tryons:
        cash, _ = tryon_payment_split(tryon)
        if cash <= 0:
            continue
        if tryon.received_by in PARTNERS:
            collected[tryon.received_by] += cash
        else:
            unattributed += cash

    paid = {p: Decimal("0") for p in PARTNERS}
    received = {p: Decimal("0") for p in PARTNERS}
    for s in all_settlements:
        if s.paid_by in paid:
            paid[s.paid_by] += s.amount
        if s.paid_to in received:
            received[s.paid_to] += s.amount

    positions = [
        PartnerCashPosition(
            partner=p,
            label=PARTNER_LABELS[p],
            cash_collected=collected[p],
            settlements_paid=paid[p],
            settlements_received=received[p],
            net_position=collected[p] - paid[p] + received[p],
        )
        for p in PARTNERS
    ]
    net_by_partner = {pos.partner: pos.net_position for pos in positions}
    to_equalize = (net_by_partner["camille"] - net_by_partner["zoe"]) / 2

    return SettlementSummary(
        positions=positions,
        unattributed_cash=unattributed,
        to_equalize=abs(to_equalize),
        equalize_direction=(
            None
            if to_equalize == 0
            else "camille_to_zoe"
            if to_equalize > 0
            else "zoe_to_camille"
        ),
    )


app.include_router(meta_router)
