from datetime import date, time
from sqlalchemy import Date, ForeignKey, Integer, String, Time, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base


class Race(Base):
    __tablename__ = "races"
    __table_args__ = (UniqueConstraint("track_id", "race_date", "race_number", name="uq_race_program"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    track_id: Mapped[int] = mapped_column(ForeignKey("tracks.id"), index=True)
    race_date: Mapped[date] = mapped_column(Date, index=True)
    race_number: Mapped[int] = mapped_column(Integer)
    scheduled_time: Mapped[time | None] = mapped_column(Time)
    distance_meters: Mapped[int] = mapped_column(Integer)
    surface: Mapped[str] = mapped_column(String(32))
    race_class: Mapped[str | None] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(24), default="scheduled")
    track: Mapped["Track"] = relationship(back_populates="races")
    entries: Mapped[list["RaceEntry"]] = relationship(back_populates="race", cascade="all, delete-orphan")
