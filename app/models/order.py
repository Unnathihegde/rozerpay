from sqlalchemy import Boolean, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class Order(Base):
    __tablename__ = "orders"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    quote_id: Mapped[str] = mapped_column(String(36), nullable=False)
    razorpay_order_id: Mapped[str | None] = mapped_column(String, nullable=True)
    razorpay_payment_link_id: Mapped[str | None] = mapped_column(String, nullable=True)
    razorpay_payment_link_url: Mapped[str | None] = mapped_column(String, nullable=True)
    amount_paise: Mapped[int] = mapped_column(Integer, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    status: Mapped[str] = mapped_column(String, nullable=False)
    is_autonomous: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    payment_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    payment_status: Mapped[str | None] = mapped_column(String(32), nullable=True)
    payment_method: Mapped[str | None] = mapped_column(String(32), nullable=True)
    payment_amount_paise: Mapped[int | None] = mapped_column(Integer, nullable=True)
    payment_currency: Mapped[str | None] = mapped_column(String(3), nullable=True)
    payment_timestamp: Mapped[str | None] = mapped_column(String(20), nullable=True)
    webhook_event_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    webhook_event_type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    webhook_received_at: Mapped[str | None] = mapped_column(String(20), nullable=True)
    webhook_verified: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    webhook_processing_status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending")
    created_at: Mapped[str] = mapped_column(String(20), nullable=False)
    updated_at: Mapped[str] = mapped_column(String(20), nullable=False)
