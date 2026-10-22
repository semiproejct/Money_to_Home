"""apartment_facilities 표. 아파트와 시설 종류마다 한 줄. 주변 시설 (FR-MAP-23).

data/load_facilities.py가 카카오 장소 검색으로 미리 받아 넣는다. 서버는 읽기만 한다 (NFR-08).
"""
from decimal import Decimal

from sqlalchemy import ForeignKey, Integer, Numeric, SmallInteger, String
from sqlalchemy.orm import Mapped, mapped_column

from backend.database import Base


class ApartmentFacility(Base):
    __tablename__ = "apartment_facilities"

    apartment_id: Mapped[int] = mapped_column(Integer, ForeignKey("apartments.id", ondelete="CASCADE"), primary_key=True)
    kind: Mapped[str] = mapped_column(String(20), primary_key=True)  # subway, school, mart, convenience, hospital, elementary, middle, high, university
    place_name: Mapped[str | None] = mapped_column(String(100))  # 가장 가까운 곳. 반경 안에 없으면 비운다
    distance: Mapped[int | None] = mapped_column(Integer)  # m. 지하철역은 가장 가까운 출구까지
    exit_no: Mapped[int | None] = mapped_column(SmallInteger)  # 지하철역의 출구 번호
    place_count: Mapped[int] = mapped_column(Integer, default=0)  # 반경 안의 수
    radius: Mapped[int] = mapped_column(Integer)  # m
    latitude: Mapped[Decimal | None] = mapped_column(Numeric(10, 7))  # 그 곳의 위도. 지하철역은 가장 가까운 출구
    longitude: Mapped[Decimal | None] = mapped_column(Numeric(10, 7))
