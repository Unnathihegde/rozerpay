from sqlalchemy import Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class WebhookEvent(Base):
    __tablename__ = "webhook_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    event_key: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    event_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    order_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    payment_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    processed_at: Mapped[str] = mapped_column(String(20), nullable=False)
    payload_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    raw_payload: Mapped[str] = mapped_column(Text, nullable=False)
