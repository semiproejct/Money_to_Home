"""아파트 한 곳 API(A-06)의 응답 모양. 담당: 안세환

API 명세서 3.1 A-06을 그대로 따른다. models의 Apartment와 ApartmentPrice를 넘기면 이 모양으로 바뀐다.
"""
from datetime import date

from pydantic import BaseModel, ConfigDict


class AreaDetail(BaseModel):
    """면적대 하나. apartment_prices 표의 한 줄"""

    model_config = ConfigDict(from_attributes=True)

    area_band: int  # 면적대. ㎡
    exclusive_area: float  # 대표 전용면적. ㎡
    supply_area: float | None  # 공급면적. 모르면 null
    avg_price: int  # 평균가. 원
    min_price: int
    max_price: int
    trade_count: int
    period_start: date  # 집계 기간 (최근 1년)
    period_end: date


class FacilityDetail(BaseModel):
    """주변 시설 한 줄. apartment_facilities 표의 한 줄 (FR-MAP-23)"""

    model_config = ConfigDict(from_attributes=True)

    kind: str  # subway, school, mart, convenience, hospital, elementary, middle, high, university, bus(버스정류장)
    place_name: str | None  # 가장 가까운 곳. 반경 안에 없으면 null ("근처에 없음")
    distance: int | None  # 직선거리. m. 지하철역은 가장 가까운 출구까지
    exit_no: int | None  # 지하철역의 출구 번호. 못 찾았으면 null (distance는 역까지)
    place_count: int  # 반경 안의 수
    radius: int  # 찾은 반경. m
    latitude: float | None = None  # 그 곳의 좌표 (지도에서 아파트와 점선으로 잇는다). 지하철역은 가장 가까운 출구
    longitude: float | None = None


class ApartmentDetailOut(BaseModel):
    """A-06 응답"""

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    gu: str
    dong: str
    jibun: str
    road_address: str | None
    built_year: int | None
    latitude: float | None  # 좌표가 없으면 null
    longitude: float | None
    households: int | None  # 세대수. 아직 없어서 null
    households_base_date: date | None = None  # 세대수의 기준일. 세대수를 모르면 null
    areas: list[AreaDetail] = []  # 평균가가 낮은 순. router가 services.apartment_detail.areas()로 채운다
    facilities: list[FacilityDetail] = []  # 주변 시설. 아직 받지 않았으면 빈 목록. 순서는 services.apartment_detail.FACILITY_ORDER
    facilities_base_date: date | None = None  # 주변 시설을 받은 날. 시설이 없으면 null
