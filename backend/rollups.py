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


def sale_cost_map(dress: Dress) -> Dict[int, Decimal]:
    """Buying cost allocated to each of this dress's sales (sale.id -> cost).

    We don't track which specific physical unit a sale came from, so cost is
    spread using the dress's weighted-average unit cost across its orders —
    standard practice when individual units aren't tracked. Sales beyond
    what was ever ordered (no matching order at all) get no cost, since
    there's nothing to allocate from. Summing these values gives cost of
    goods sold; each order's total minus what's allocated here is unsold
    inventory value.
    """
    orders = list(dress.orders or [])
    sales = list(dress.sales or [])

    total_ordered = sum(o.quantity or 0 for o in orders)
    total_cost = sum(
        (
            _d(o.unit_cost if o.unit_cost is not None else dress.base_cost) * (o.quantity or 0)
            for o in orders
        ),
        Decimal("0"),
    )
    avg_unit_cost = total_cost / total_ordered if total_ordered else Decimal("0")

    remaining_units = total_ordered
    costs = {}
    for sale in sales:
        if remaining_units > 0:
            costs[sale.id] = avg_unit_cost
            remaining_units -= 1
        else:
            costs[sale.id] = Decimal("0")
    return costs


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

    # Split what was spent ordering this style into cost of goods sold
    # (charged against revenue) and inventory value (unsold stock, not yet
    # an expense).
    cost_of_goods_sold = sum(sale_cost_map(dress).values(), Decimal("0"))
    inventory_value = total_cost - cost_of_goods_sold

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
        "cost_of_goods_sold": cost_of_goods_sold,
        "inventory_value": inventory_value,
        "latest_status": latest_order.status if latest_order else None,
        "latest_order_id": latest_order.id if latest_order else None,
    }
