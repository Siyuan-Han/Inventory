from datetime import date, datetime
from decimal import Decimal
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field

# The order status pipeline, in the sequence an order moves through.
# `arrived_us` was dropped from the active pipeline earlier — shipping
# center goes straight to received now. The dress_order.arrived_us_at
# column and the OrderRead/OrderUpdate fields below stay, so any historical
# value already on an order is preserved; it just isn't part of the
# pipeline going forward.
#
# `shipping_center_received` sits between the factory and shipping-center
# legs: shipped_from_factory's tracking number covers factory -> shipping
# center, this marks the shipping center confirming receipt of it (which
# can lag behind the courier's own tracking), and arrived_shipping_center
# (labelled "Shipped from shipping center") covers the outbound leg from
# there to the US.
ORDER_STATUSES = [
    "ordered",
    "shipped_from_factory",
    "shipping_center_received",
    "arrived_shipping_center",
    "received",
]

# Each status stamps its own timestamp column when an order reaches it.
STATUS_TIMESTAMP_FIELD = {
    "ordered": "ordered_at",
    "shipped_from_factory": "shipped_from_factory_at",
    "shipping_center_received": "shipping_center_received_at",
    "arrived_shipping_center": "arrived_shipping_center_at",
    "received": "received_at",
}

STATUS_LABELS = {
    "ordered": "Ordered",
    "shipped_from_factory": "Shipped from factory",
    "shipping_center_received": "Shipping center received",
    "arrived_shipping_center": "Shipped from shipping center",
    "received": "Received",
}


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# --------------------------------------------------------------------------
# Dress
# --------------------------------------------------------------------------
class DressBase(BaseModel):
    style_name: Optional[str] = Field(default=None, max_length=200)
    photo_url: Optional[str] = None
    supplier: Optional[str] = Field(default=None, max_length=200)
    base_cost: Optional[Decimal] = Field(default=None, ge=0)


class DressCreate(DressBase):
    # Left blank in the normal "Add dress" flow — the server assigns the next
    # code. Still accepted so an import script or a correction can set one.
    dress_code: Optional[str] = Field(default=None, min_length=1, max_length=20)


class DressUpdate(BaseModel):
    dress_code: Optional[str] = Field(default=None, min_length=1, max_length=20)
    style_name: Optional[str] = Field(default=None, max_length=200)
    photo_url: Optional[str] = None
    supplier: Optional[str] = Field(default=None, max_length=200)
    base_cost: Optional[Decimal] = Field(default=None, ge=0)


class SecondhandDressCreate(DressBase):
    """Creates a secondhand dress and its one acquisition order together.

    A secondhand piece is unique — no quantity field, always 1 — and never
    gets a second order, so this combines what's normally two separate steps
    (add dress, then add order) into one atomic action.
    """

    order_date: date
    unit_cost: Optional[Decimal] = Field(default=None, ge=0)
    status: str = "ordered"
    tracking_number: Optional[str] = Field(default=None, max_length=100)
    order_notes: Optional[str] = None


# --------------------------------------------------------------------------
# Order
# --------------------------------------------------------------------------
class OrderBase(BaseModel):
    dress_id: int
    order_date: date
    quantity: int = Field(default=1, ge=1)
    unit_cost: Optional[Decimal] = Field(default=None, ge=0)
    status: str = "ordered"
    notes: Optional[str] = None


class OrderCreate(OrderBase):
    pass


class OrderUpdate(BaseModel):
    order_date: Optional[date] = None
    quantity: Optional[int] = Field(default=None, ge=1)
    unit_cost: Optional[Decimal] = Field(default=None, ge=0)
    status: Optional[str] = None
    # The date the new status was actually reached, when different from
    # today (e.g. marking a shipment received a few days late).
    status_date: Optional[date] = None
    tracking_number: Optional[str] = Field(default=None, max_length=100)
    notes: Optional[str] = None
    ordered_at: Optional[datetime] = None
    shipped_from_factory_at: Optional[datetime] = None
    shipping_center_received_at: Optional[datetime] = None
    arrived_shipping_center_at: Optional[datetime] = None
    arrived_us_at: Optional[datetime] = None
    received_at: Optional[datetime] = None


class BulkOrderStatusUpdate(BaseModel):
    """Advance several orders to the same next status at once.

    All `order_ids` must currently share one status — the point is moving a
    batch that's sitting together at one stage (e.g. 20+ secondhand pieces
    all "at shipping center") to the next stage together, not advancing
    unrelated orders to different places in one call.
    """

    order_ids: List[int] = Field(min_length=1)
    status: str
    status_date: Optional[date] = None


class OrderRead(ORMModel):
    id: int
    dress_id: Optional[int] = None
    order_date: date
    quantity: Optional[int] = None
    unit_cost: Optional[Decimal] = None
    status: Optional[str] = None
    tracking_number: Optional[str] = None
    notes: Optional[str] = None
    ordered_at: Optional[datetime] = None
    shipped_from_factory_at: Optional[datetime] = None
    shipping_center_received_at: Optional[datetime] = None
    arrived_shipping_center_at: Optional[datetime] = None
    arrived_us_at: Optional[datetime] = None
    received_at: Optional[datetime] = None
    created_at: Optional[datetime] = None


# --------------------------------------------------------------------------
# Sale
# --------------------------------------------------------------------------
class SaleBase(BaseModel):
    dress_id: int
    order_id: Optional[int] = None
    sale_date: date
    sale_price: Optional[Decimal] = Field(default=None, ge=0)
    is_cash: bool = False
    # How much of sale_price was cash; the remainder is card. Omit for a
    # sale that's simply all-cash (is_cash=true) or all-card (is_cash=false).
    cash_amount: Optional[Decimal] = Field(default=None, ge=0)
    # Which partner (see PARTNERS in payments.py) physically received the
    # cash. Required by the API whenever any part of the sale is cash.
    received_by: Optional[str] = None
    notes: Optional[str] = None


class SaleCreate(SaleBase):
    pass


class SaleUpdate(BaseModel):
    order_id: Optional[int] = None
    sale_date: Optional[date] = None
    sale_price: Optional[Decimal] = Field(default=None, ge=0)
    is_cash: Optional[bool] = None
    cash_amount: Optional[Decimal] = Field(default=None, ge=0)
    received_by: Optional[str] = None
    notes: Optional[str] = None


class SaleRead(ORMModel):
    id: int
    dress_id: Optional[int] = None
    order_id: Optional[int] = None
    sale_date: date
    sale_price: Optional[Decimal] = None
    is_cash: Optional[bool] = None
    cash_amount: Optional[Decimal] = None
    received_by: Optional[str] = None
    notes: Optional[str] = None
    created_at: Optional[datetime] = None


# --------------------------------------------------------------------------
# TryOn
# --------------------------------------------------------------------------
class TryOnBase(BaseModel):
    dress_id: int
    tryon_date: date
    fee: Optional[Decimal] = Field(default=None, ge=0)
    is_cash: bool = False
    cash_amount: Optional[Decimal] = Field(default=None, ge=0)
    received_by: Optional[str] = None
    notes: Optional[str] = None


class TryOnCreate(TryOnBase):
    pass


class TryOnUpdate(BaseModel):
    tryon_date: Optional[date] = None
    fee: Optional[Decimal] = Field(default=None, ge=0)
    is_cash: Optional[bool] = None
    cash_amount: Optional[Decimal] = Field(default=None, ge=0)
    received_by: Optional[str] = None
    notes: Optional[str] = None


class TryOnRead(ORMModel):
    id: int
    dress_id: Optional[int] = None
    tryon_date: date
    fee: Optional[Decimal] = None
    is_cash: Optional[bool] = None
    cash_amount: Optional[Decimal] = None
    received_by: Optional[str] = None
    notes: Optional[str] = None
    created_at: Optional[datetime] = None


# --------------------------------------------------------------------------
# Settlement
# --------------------------------------------------------------------------
class SettlementBase(BaseModel):
    settlement_date: date
    amount: Decimal = Field(ge=0)
    paid_by: str
    paid_to: str
    notes: Optional[str] = None


class SettlementCreate(SettlementBase):
    pass


class SettlementRead(ORMModel):
    id: int
    settlement_date: date
    amount: Decimal
    paid_by: str
    paid_to: str
    notes: Optional[str] = None
    created_at: Optional[datetime] = None


class PartnerCashPosition(BaseModel):
    partner: str
    label: str
    cash_collected: Decimal = Decimal("0")
    settlements_paid: Decimal = Decimal("0")
    settlements_received: Decimal = Decimal("0")
    net_position: Decimal = Decimal("0")


class SettlementSummary(BaseModel):
    positions: List[PartnerCashPosition] = []
    unattributed_cash: Decimal = Decimal("0")
    to_equalize: Decimal = Decimal("0")
    equalize_direction: Optional[str] = None  # "camille_to_zoe" | "zoe_to_camille" | None


# --------------------------------------------------------------------------
# Dress read models (with rollups)
# --------------------------------------------------------------------------
class DressRead(ORMModel):
    id: int
    dress_code: str
    category: str = "new"  # "new" (reorderable) or "secondhand" (one-off)
    style_name: Optional[str] = None
    photo_url: Optional[str] = None
    supplier: Optional[str] = None
    base_cost: Optional[Decimal] = None
    created_at: Optional[datetime] = None
    archived_at: Optional[datetime] = None

    # Rollups computed by the router.
    total_ordered: int = 0
    total_received: int = 0
    total_sold: int = 0
    in_stock: int = 0
    pending_orders: int = 0
    total_revenue: Decimal = Decimal("0")
    tryon_revenue: Decimal = Decimal("0")
    total_cost: Decimal = Decimal("0")
    latest_status: Optional[str] = None
    latest_order_id: Optional[int] = None
    latest_tracking_number: Optional[str] = None


class DressDetail(DressRead):
    orders: List[OrderRead] = []
    sales: List[SaleRead] = []
    try_ons: List[TryOnRead] = []


class DashboardStats(BaseModel):
    total_dresses: int = 0
    total_ordered: int = 0
    total_received: int = 0
    total_sold: int = 0
    in_stock: int = 0
    pending_orders: int = 0
    total_revenue: Decimal = Decimal("0")  # sale revenue only
    tryon_revenue: Decimal = Decimal("0")
    tryon_count: int = 0
    total_cost: Decimal = Decimal("0")  # cost of everything ordered, sold or not
    cost_of_goods_sold: Decimal = Decimal("0")  # buying cost of sold dresses only
    inventory_value: Decimal = Decimal("0")  # buying cost still sitting unsold
    profit: Decimal = Decimal("0")  # total_revenue - cost_of_goods_sold + tryon_revenue
    cash_sales: int = 0
    cash_revenue: Decimal = Decimal("0")  # sales + try-ons
    card_revenue: Decimal = Decimal("0")  # sales + try-ons
    status_breakdown: dict = {}


class MonthlyStats(BaseModel):
    month: str  # "YYYY-MM"
    orders_count: int = 0
    sales_count: int = 0
    revenue: Decimal = Decimal("0")  # sale revenue only
    tryon_revenue: Decimal = Decimal("0")
    tryon_count: int = 0
    cost: Decimal = Decimal("0")  # cost of goods sold that were sold this month
    inventory_spend: Decimal = Decimal("0")  # cost of orders placed this month, sold or not
    profit: Decimal = Decimal("0")  # revenue - cost + tryon_revenue
    cash_sales: int = 0
    cash_revenue: Decimal = Decimal("0")  # sales + try-ons
    card_revenue: Decimal = Decimal("0")  # sales + try-ons


class NextDressCode(BaseModel):
    dress_code: str
