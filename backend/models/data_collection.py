"""data_collections 표. 자료를 언제 받았는지의 기록 (수집 기준일)."""
from datetime import date, datetime

from sqlalchemy import Date, DateTime, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from backend.database import Base


class DataCollection(Base):
    __tablename__ = "data_collections"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    dataset: Mapped[str] = mapped_column(String(20))  # trades, coordinates, supply_area, households, facilities
    source: Mapped[str] = mapped_column(String(100))  # 받은 곳
    base_date: Mapped[date] = mapped_column(Date)
    row_count: Mapped[int | None] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
