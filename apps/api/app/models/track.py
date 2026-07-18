from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base


class Track(Base):
    __tablename__ = "tracks"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False, unique=True, index=True)
    city: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    country: Mapped[str] = mapped_column(String(2), nullable=False, default="TR")
    races: Mapped[list["Race"]] = relationship(back_populates="track")
