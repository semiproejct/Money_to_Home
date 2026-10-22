"""trades 표. 거래 한 건에 한 줄이다. 해제된 거래도 넣고, 평균을 낼 때만 뺀다."""
from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, Boolean, Date, ForeignKey, Integer, Numeric, SmallInteger
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.database import Base

if TYPE_CHECKING:
    from backend.models.apartment import Apartment


class Trade(Base):
    __tablename__ = "trades"

    # MariaDB에서는 BIGINT다. 테스트용 SQLite에서는 INTEGER여야 번호가 자동으로 붙는다.
    id: Mapped[int] = mapped_column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True, autoincrement=True)
    apartment_id: Mapped[int] = mapped_column(Integer, ForeignKey("apartments.id", ondelete="CASCADE"))
    contract_date: Mapped[date] = mapped_column(Date)
    exclusive_area: Mapped[Decimal] = mapped_column(Numeric(8, 4))  # 전용면적. ㎡
    price: Mapped[int] = mapped_column(BigInteger)  # 거래 금액. 원
    floor: Mapped[int | None] = mapped_column(SmallInteger)
    is_canceled: Mapped[bool] = mapped_column(Boolean, default=False)  # True면 평균에서 뺀다

    apartment: Mapped[Apartment] = relationship(back_populates="trades")
