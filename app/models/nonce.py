from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base
from app.gateway.quote import now_utc


class UsedNonce(Base):
    __tablename__ = "used_nonces"

    nonce: Mapped[str] = mapped_column(String(36), primary_key=True)
    used_at: Mapped[str] = mapped_column(String(20), nullable=False, default=now_utc)
