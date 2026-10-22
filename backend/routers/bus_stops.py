"""버스정류장. 담당: 안세환

- A-28 GET /api/bus-stops?south=&west=&north=&east= : 지도 영역 안의 버스정류장 (API 명세서 3.1)

지도(축척 100m 이하)가 화면 근처의 정류장을 모두 띄울 때 부른다 (FR-MAP-23, 2026-10-20).
data/load_facilities.py가 미리 넣어 둔 것만 준다. 외부 API를 부르지 않는다 (NFR-08).
영역이 뒤집혔거나 가로 · 세로가 0.1도(약 10km)를 넘으면 422, "지도 영역을 다시 확인해 주세요." (field bounds)
DB를 읽는 일은 backend/services/bus_stop.py에 있다.
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.schemas.bus_stop import BusStopOut, BusStopsOut
from backend.services import bus_stop

router = APIRouter(prefix="/api", tags=["버스정류장"])


@router.get("/bus-stops", response_model=BusStopsOut)
def list_bus_stops(
    south: float = Query(...),
    west: float = Query(...),
    north: float = Query(...),
    east: float = Query(...),
    db: Session = Depends(get_db),
):
    stops = bus_stop.in_area(db, south, west, north, east)
    return BusStopsOut(stops=[BusStopOut.model_validate(stop) for stop in stops])
