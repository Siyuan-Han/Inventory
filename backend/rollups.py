"""Derived inventory numbers computed from a dress's orders and sales."""

from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, Tuple

from models import Dress, Sale


def _d(value: Any) -> Decimal:
    return Decimal(str(value)) if value is not None else Decimal("0")


def sale_payment_split(sale: Sale) -> Tuple[Decimal, Decimal]:
    """(cash, card) portions of a sale's price.

    `cash_amount` is the source of truth when set (supports part-cash,
    part-card sales); otherwise the sale is treated as fully cash or fully
    card based on the older `is_cash` flag.
    """
    price = _d(sale.sale_price)
    if sale.cash_amount is not None:
        cash = min(_d(sale.cash_amount), price)
        return cash, price - cash
    return (price, Decimal("0")) if sale.is_cash else (Decimal("0"), price)


def dress_rollup(dress: Dress) -> Dict[str, Any]:
    orders = list(dress.orders or [])
    sales = list(dress.sales or [])

    total_ordered = sum(o.quantity or 0 for o in orders)
    total_received = sum(o.quantity or 0 for o in orders if o.status == "received")
    total_sold = len(sales)
    pending_orders = sum(1 for o in orders if o.status != "received")

    total_revenue = sum((_d(s.sale_price) for s in sales), Decimal("0"))
    total_cost = sum(
        (
            _d(o.unit_cost if o.unit_cost is not None else dress.base_cost) * (o.quantity or 0)
            for o in orders
        ),
        Decimal("0"),
    )

    # The order most recently *created* — not the one with the latest
    # order_date, which can tie (or be backdated) and no longer reflects
    # which order actually changed status last.
    latest_order = max(orders, key=lambda o: (o.created_at or datetime.min, o.id), default=None)

    return {
        "total_ordered": total_ordered,
        "total_received": total_received,
        "total_sold": total_sold,
        "in_stock": total_received - total_sold,
        "pending_orders": pending_orders,
        "total_revenue": total_revenue,
        "total_cost": total_cost,
        "latest_status": latest_order.status if latest_order else None,
    }
