import json

from sqlalchemy import Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class LedgerEntry(Base):
    __tablename__ = "ledger_entries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    order_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    step: Mapped[str] = mapped_column(String, nullable=False)
    timestamp: Mapped[str] = mapped_column(String(20), nullable=False)
    details_json: Mapped[str] = mapped_column(Text, nullable=False)

    @property
    def details(self) -> dict:
        return json.loads(self.details_json)
