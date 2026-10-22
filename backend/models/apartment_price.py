"""apartment_prices 표. 아파트와 면적대마다 한 줄. 화면이 보는 평균가가 여기 있다."""
from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, Date, DateTime, ForeignKey, Integer, Numeric, SmallInteger, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.database import Base

if TYPE_CHECKING:
    from backend.models.apartment import Apartment


class ApartmentPrice(Base):
    __tablename__ = "apartment_prices"
    __table_args__ = (UniqueConstraint("apartment_id", "area_band", name="uq_prices_apartment_band"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    apartment_id: Mapped[int] = mapped_column(Integer, ForeignKey("apartments.id", ondelete="CASCADE"))
    area_band: Mapped[int] = mapped_column(SmallInteger)  # 면적대. 전용면적의 소수점 아래를 버린 값
    exclusive_area: Mapped[Decimal] = mapped_column(Numeric(8, 4))  # 대표 전용면적. 거래에 가장 많이 나온 값
    supply_area: Mapped[Decimal | None] = mapped_column(Numeric(7, 2))  # 공급면적. 구하지 못하면 비운다
    supply_area_method: Mapped[str | None] = mapped_column(String(30))  # ledger_sum, ledger_partial, ledger_inferred, borrowed, legacy
    avg_price: Mapped[int] = mapped_column(BigInteger)  # 평균가. 원. 해제된 거래를 뺀 평균
    min_price: Mapped[int] = mapped_column(BigInteger)
    max_price: Mapped[int] = mapped_column(BigInteger)
    trade_count: Mapped[int] = mapped_column(Integer)  # 해제된 거래를 뺀 수
    period_start: Mapped[date] = mapped_column(Date)
    period_end: Mapped[date] = mapped_column(Date)
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    apartment: Mapped[Apartment] = relationship(back_populates="prices")
