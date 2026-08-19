from datetime import date, datetime
from decimal import Decimal
from typing import List, Optional

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base


class Dress(Base):
    __tablename__ = "dress"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    dress_code: Mapped[str] = mapped_column(String(20), unique=True, nullable=False, index=True)
    style_name: Mapped[Optional[str]] = mapped_column(String(200))
    photo_url: Mapped[Optional[str]] = mapped_column(Text)
    supplier: Mapped[Optional[str]] = mapped_column(String(200))
    base_cost: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 2))
    created_at: Mapped[Optional[datetime]] = mapped_column(DateTime, server_default=func.now())
    archived_at: Mapped[Optional[datetime]] = mapped_column(DateTime)

    # `.id.desc()` breaks ties when two rows share the same date — without it,
    # two orders placed the same day sort in an arbitrary, storage-dependent
    # order, which made the "latest status" badge look stuck.
    orders: Mapped[List["DressOrder"]] = relationship(
        back_populates="dress",
        cascade="all, delete-orphan",
        order_by="DressOrder.order_date.desc(), DressOrder.id.desc()",
        lazy="selectin",
    )
    sales: Mapped[List["Sale"]] = relationship(
        back_populates="dress",
        cascade="all, delete-orphan",
        order_by="Sale.sale_date.desc(), Sale.id.desc()",
        lazy="selectin",
    )


class DressOrder(Base):
    __tablename__ = "dress_order"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    dress_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("dress.id", ondelete="CASCADE"), index=True
    )
    order_date: Mapped[date] = mapped_column(Date, nullable=False)
    quantity: Mapped[Optional[int]] = mapped_column(Integer, default=1, server_default="1")
    unit_cost: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 2))
    status: Mapped[Optional[str]] = mapped_column(
        String(50), default="ordered", server_default="ordered"
    )
    notes: Mapped[Optional[str]] = mapped_column(Text)

    ordered_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    shipped_from_factory_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    arrived_shipping_center_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    arrived_us_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    received_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    created_at: Mapped[Optional[datetime]] = mapped_column(DateTime, server_default=func.now())

    dress: Mapped[Optional["Dress"]] = relationship(back_populates="orders")


class Sale(Base):
    __tablename__ = "sale"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    dress_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("dress.id", ondelete="CASCADE"), index=True
    )
    order_id: Mapped[Optional[int]] = mapped_column(ForeignKey("dress_order.id"))
    sale_date: Mapped[date] = mapped_column(Date, nullable=False)
    sale_price: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 2))
    is_cash: Mapped[Optional[bool]] = mapped_column(
        Boolean, default=False, server_default="false"
    )
    # How much of sale_price was paid in cash; the rest is card. Null means
    # "not split" — go by is_cash instead (kept for older rows/simple sales).
    cash_amount: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 2))
    notes: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[Optional[datetime]] = mapped_column(DateTime, server_default=func.now())

    dress: Mapped[Optional["Dress"]] = relationship(back_populates="sales")
