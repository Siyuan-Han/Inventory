"""Cash/card payment logic shared by Sale and TryOn, plus the two-partner
cash-attribution constants used for settlement tracking. Kept separate from
rollups.py (pure derived numbers, no HTTP concerns) since this module raises
HTTPException for request validation.
"""

from decimal import Decimal
from typing import Any, Optional, Tuple

from fastapi import HTTPException

PARTNERS = ["camille", "zoe"]
PARTNER_LABELS = {"camille": "Camille", "zoe": "Zoe"}


def _d(value: Any) -> Decimal:
    return Decimal(str(value)) if value is not None else Decimal("0")


def payment_split(
    amount: Any, is_cash: Optional[bool], cash_amount: Optional[Decimal]
) -> Tuple[Decimal, Decimal]:
    """(cash, card) portions of a payment, generalized over Sale.sale_price
    and TryOn.fee.

    `cash_amount` is authoritative when set (supports part-cash, part-card
    payments); otherwise the payment is treated as fully cash or fully card
    based on the older `is_cash` flag.
    """
    total = _d(amount)
    if cash_amount is not None:
        cash = min(_d(cash_amount), total)
        return cash, total - cash
    return (total, Decimal("0")) if is_cash else (Decimal("0"), total)


def check_cash_amount(cash_amount: Optional[Decimal], total: Optional[Decimal]) -> None:
    if cash_amount is not None and total is not None and cash_amount > total:
        raise HTTPException(status_code=422, detail="cash_amount cannot exceed the total amount")


def validate_partner(partner: str) -> str:
    if partner not in PARTNERS:
        raise HTTPException(
            status_code=422, detail=f"received_by must be one of: {', '.join(PARTNERS)}"
        )
    return partner


def require_received_by(
    is_cash: Optional[bool], cash_amount: Optional[Decimal], received_by: Optional[str]
) -> None:
    cash_involved = bool(is_cash) or (cash_amount is not None and cash_amount > 0)
    if cash_involved and not received_by:
        raise HTTPException(
            status_code=422, detail="received_by is required when payment includes cash"
        )
