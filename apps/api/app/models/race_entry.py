from decimal import Decimal
from sqlalchemy import ForeignKey, Integer, Numeric, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base


class RaceEntry(Base):
    __tablename__ = "race_entries"
    __table_args__ = (UniqueConstraint("race_id", "program_number", name="uq_race_program_number"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    race_id: Mapped[int] = mapped_column(ForeignKey("races.id", ondelete="CASCADE"), index=True)
    horse_id: Mapped[int] = mapped_column(ForeignKey("horses.id"), index=True)
    jockey_id: Mapped[int | None] = mapped_column(ForeignKey("jockeys.id"))
    trainer_id: Mapped[int | None] = mapped_column(ForeignKey("trainers.id"))
    program_number: Mapped[int] = mapped_column(Integer)
    barrier: Mapped[int | None] = mapped_column(Integer)
    weight_kg: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))
    handicap_rating: Mapped[int | None] = mapped_column(Integer)
    agf_percent: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))
    race: Mapped["Race"] = relationship(back_populates="entries")
    horse: Mapped["Horse"] = relationship()
    jockey: Mapped["Jockey | None"] = relationship(back_populates="entries")
    trainer: Mapped["Trainer | None"] = relationship(back_populates="entries")
