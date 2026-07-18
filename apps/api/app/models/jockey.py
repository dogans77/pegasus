from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base


class Jockey(Base):
    __tablename__ = "jockeys"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False, unique=True, index=True)
    country: Mapped[str] = mapped_column(String(2), nullable=False, default="TR")
    entries: Mapped[list["RaceEntry"]] = relationship(back_populates="jockey")
