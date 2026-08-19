"""Derived inventory numbers computed from a dress's orders and sales."""

from decimal import Decimal
from typing import Any, Dict

from models import Dress


def _d(value: Any) -> Decimal:
    return Decimal(str(value)) if value is not None else Decimal("0")


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

    # `orders` is ordered newest-first by the relationship.
    latest_status = orders[0].status if orders else None

    return {
        "total_ordered": total_ordered,
        "total_received": total_received,
        "total_sold": total_sold,
        "in_stock": total_received - total_sold,
        "pending_orders": pending_orders,
        "total_revenue": total_revenue,
        "total_cost": total_cost,
        "latest_status": latest_status,
    }
