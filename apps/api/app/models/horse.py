from sqlalchemy import Column, Integer, String

from app.core.database import Base


class Horse(Base):
    __tablename__ = "horses"

    id = Column(Integer, primary_key=True, index=True)

    name = Column(String(150), nullable=False)

    father = Column(String(150))

    mother = Column(String(150))

    country = Column(String(20))

    gender = Column(String(10))