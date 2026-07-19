from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, JSON, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class RaceResult(Base):
    __tablename__ = "race_results"
    __table_args__ = (UniqueConstraint("race_id", name="uq_race_results_race_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    race_id: Mapped[int] = mapped_column(ForeignKey("races.id", ondelete="CASCADE"), index=True)
    winner_entry_id: Mapped[int] = mapped_column(ForeignKey("race_entries.id"))
    official_order: Mapped[list] = mapped_column(JSON)
    official_time: Mapped[str | None] = mapped_column(String(32))
    source: Mapped[str] = mapped_column(String(32), default="manual")
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())