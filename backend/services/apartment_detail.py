"""아파트 한 곳을 읽는 함수. 담당: 안세환

- 아파트는 db.get(Apartment, 번호)로 읽는다.
- 면적대별 평균가는 apartment_prices 표에서 평균가가 낮은 순으로 읽는다 (같으면 면적대가 작은 순).
- 세대수의 기준일은 data_collections 표에서 세대수 자료(households)의 가장 최근 기준일이다.
- 주변 시설은 apartment_facilities 표에서 읽는다 (data/load_facilities.py가 카카오에서 미리 받아 넣는다. 서버는 카카오를 부르지 않는다).
여기서 commit하지 않는다. 읽기만 한다.
"""
from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.errors import ApiError
from backend.models import Apartment, ApartmentFacility, ApartmentPrice, DataCollection

MSG_NOT_FOUND = "아파트를 찾을 수 없습니다."  # API 명세서 3.1 A-06
# 주변 시설을 주는 순서. 화면의 다섯 줄(지하철역 · 학교 · 대형마트 · 편의점 · 병원) 뒤에 학교 종류별 네 줄,
# 맨 뒤에 버스정류장 (2026-10-20 더함. 정보 탭 줄은 아니고 지도에서 역세권이 아닌 아파트의 대중교통으로 쓴다)
FACILITY_ORDER = ["subway", "school", "mart", "convenience", "hospital", "elementary", "middle", "high", "university", "bus"]


def find(db: Session, apartment_id: int) -> Apartment:
    """아파트 한 곳. 없는 번호면 404"""
    apartment = db.get(Apartment, apartment_id)
    if apartment is None:
        raise ApiError(404, MSG_NOT_FOUND)
    return apartment


def areas(db: Session, apartment_id: int) -> list[ApartmentPrice]:
    """면적대별 평균가. 평균가가 낮은 순"""
    query = (
        select(ApartmentPrice)
        .where(ApartmentPrice.apartment_id == apartment_id)
        .order_by(ApartmentPrice.avg_price, ApartmentPrice.area_band)
    )
    return list(db.scalars(query))


def households_base_date(db: Session) -> date | None:
    """세대수 자료의 가장 최근 기준일. 기록이 없으면 None"""
    return _base_date(db, "households")


def facilities(db: Session, apartment_id: int) -> list[ApartmentFacility]:
    """주변 시설. FACILITY_ORDER 순. 모르는 종류는 뒤로"""
    rows = list(db.scalars(select(ApartmentFacility).where(ApartmentFacility.apartment_id == apartment_id)))
    rank = {kind: index for index, kind in enumerate(FACILITY_ORDER)}
    return sorted(rows, key=lambda row: rank.get(row.kind, len(rank)))


def facilities_base_date(db: Session) -> date | None:
    """주변 시설 자료의 가장 최근 기준일. 기록이 없으면 None"""
    return _base_date(db, "facilities")


def _base_date(db: Session, dataset: str) -> date | None:
    query = (
        select(DataCollection.base_date)
        .where(DataCollection.dataset == dataset)
        .order_by(DataCollection.base_date.desc())
        .limit(1)
    )
    return db.scalars(query).first()
