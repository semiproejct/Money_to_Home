"""버스정류장을 읽는 함수. 담당: 안세환

- bus_stops 표에서 지도 영역 안의 정류장을 읽는다 ((위도, 경도) 인덱스).
- 표는 data/load_facilities.py가 data/bus_stops_gwangju.csv로 미리 채운다. 서버는 읽기만 한다 (NFR-08).
여기서 commit하지 않는다.
"""
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.errors import ApiError
from backend.models import BusStop

MSG_BOUNDS = "지도 영역을 다시 확인해 주세요."  # API 명세서 5장의 bounds 문장
# 한 번에 찾는 영역의 가로 · 세로 상한 (위도 · 경도의 도). 약 10km. 지도는 축척 100m 이하에서만 부른다 (PC 화면도 4km 안쪽)
MAX_SPAN = 0.1


def in_area(db: Session, south: float, west: float, north: float, east: float) -> list[BusStop]:
    """영역 안의 정류장. 정류장 번호 순. 영역이 뒤집혔거나 너무 넓으면 422"""
    if not (south < north and west < east) or north - south > MAX_SPAN or east - west > MAX_SPAN:
        raise ApiError(422, MSG_BOUNDS, "bounds")
    query = (
        select(BusStop)
        .where(BusStop.latitude.between(south, north), BusStop.longitude.between(west, east))
        .order_by(BusStop.stop_id)
    )
    return list(db.scalars(query))
