"""bus_stops 표. 광주 5개 구의 시내버스 정류장마다 한 줄 (FR-MAP-23, 2026-10-20).

data/load_facilities.py가 data/bus_stops_gwangju.csv(국토교통부 전국 버스정류장 위치정보)에서 미리 넣는다.
서버는 읽기만 한다 (NFR-08). 지도가 화면 안 정류장을 A-28로 읽는다.
"""
from decimal import Decimal

from sqlalchemy import Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from backend.database import Base


class BusStop(Base):
    __tablename__ = "bus_stops"

    stop_id: Mapped[str] = mapped_column(String(20), primary_key=True)  # 원본의 정류장번호 (예: KJB3908)
    name: Mapped[str] = mapped_column(String(100))  # 길 건너편 정류장은 이름이 같고 번호가 다르다
    latitude: Mapped[Decimal] = mapped_column(Numeric(10, 7))
    longitude: Mapped[Decimal] = mapped_column(Numeric(10, 7))
