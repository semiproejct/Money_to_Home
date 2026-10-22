"""apartments 표. 아파트. 같은 아파트는 구, 동, 지번, 아파트명이 모두 같은 것이다."""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Enum, Integer, Numeric, SmallInteger, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.database import Base

if TYPE_CHECKING:
    from backend.models.apartment_price import ApartmentPrice
    from backend.models.trade import Trade


class Apartment(Base):
    __tablename__ = "apartments"
    __table_args__ = (UniqueConstraint("gu", "dong", "jibun", "name", name="uq_apartments_address"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    complex_code: Mapped[str | None] = mapped_column(String(30), unique=True)  # 단지 일련번호. 받은 그대로 둔다
    name: Mapped[str] = mapped_column(String(100))
    gu: Mapped[str] = mapped_column(String(10))
    dong: Mapped[str] = mapped_column(String(20))
    jibun: Mapped[str] = mapped_column(String(20))  # 506-8, 산1-9 같은 글자
    road_address: Mapped[str | None] = mapped_column(String(100))
    built_year: Mapped[int | None] = mapped_column(SmallInteger)
    latitude: Mapped[Decimal | None] = mapped_column(Numeric(10, 7))  # 변환에 실패하면 비운다
    longitude: Mapped[Decimal | None] = mapped_column(Numeric(10, 7))
    geocode_status: Mapped[str | None] = mapped_column(Enum("ok", "failed", name="geocode_status"))  # 비어 있으면 아직 변환 안 함
    households: Mapped[int | None] = mapped_column(Integer)  # 세대수. 연결되지 않으면 비운다
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    # 면적대별 평균가. 평균가가 낮은 순으로 읽는다.
    prices: Mapped[list[ApartmentPrice]] = relationship(
        back_populates="apartment", order_by="ApartmentPrice.avg_price", cascade="all, delete-orphan"
    )
    trades: Mapped[list[Trade]] = relationship(back_populates="apartment", cascade="all, delete-orphan")
