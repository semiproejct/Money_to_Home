"""버스정류장 API(A-28)의 응답 모양. 담당: 안세환

API 명세서 3.1 A-28을 그대로 따른다. models의 BusStop을 넘기면 이 모양으로 바뀐다.
"""
from pydantic import BaseModel, ConfigDict


class BusStopOut(BaseModel):
    """정류장 하나. bus_stops 표의 한 줄"""

    model_config = ConfigDict(from_attributes=True)

    stop_id: str  # 정류장 번호 (예: KJB3908). 길 건너편 정류장은 이름이 같아 이것으로 구분한다
    name: str
    latitude: float
    longitude: float


class BusStopsOut(BaseModel):
    """A-28 응답"""

    stops: list[BusStopOut]
