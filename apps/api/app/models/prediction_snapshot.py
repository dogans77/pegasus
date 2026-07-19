from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, JSON, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class PredictionSnapshot(Base):
    __tablename__ = "prediction_snapshots"

    id: Mapped[int] = mapped_column(primary_key=True)
    race_id: Mapped[int] = mapped_column(ForeignKey("races.id", ondelete="CASCADE"), index=True)
    model_version: Mapped[str] = mapped_column(String(64), index=True)
    chaos_index: Mapped[float] = mapped_column(Numeric(6, 2))
    payload: Mapped[dict] = mapped_column(JSON)
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)