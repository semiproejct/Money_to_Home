"""아파트 한 곳. 담당: 안세환

- A-06 GET /api/apartments/{id} : 아파트 한 곳의 정보 (API 명세서 3.1)

아래 창의 아파트 정보 탭(P-06 ⑦)이 부른다. 재무 조건이 필요 없어 GET이다.
구분과 여유·부족 금액은 주지 않는다. 그것은 A-05와 A-07이 준다.
주변 시설(facilities)은 data/load_facilities.py가 미리 넣어 둔 것을 준다. 카카오를 부르지 않는다 (NFR-08).
없는 번호면 404, "아파트를 찾을 수 없습니다."
DB를 읽는 일은 backend/services/apartment_detail.py에 있다.
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.schemas.apartment_detail import ApartmentDetailOut, AreaDetail, FacilityDetail
from backend.services import apartment_detail

router = APIRouter(prefix="/api", tags=["아파트 한 곳"])


@router.get("/apartments/{id}", response_model=ApartmentDetailOut)
def get_apartment(id: int, db: Session = Depends(get_db)):
    found = apartment_detail.find(db, id)
    out = ApartmentDetailOut.model_validate(found)
    out.areas = [AreaDetail.model_validate(price) for price in apartment_detail.areas(db, id)]
    # 세대수를 알 때만 기준일을 붙인다. 세대수를 모르면 둘 다 null이다 (FR-APT-15)
    if found.households is not None:
        out.households_base_date = apartment_detail.households_base_date(db)
    # 주변 시설 (FR-MAP-23). 미리 받아 둔 것만 준다. 없으면 빈 목록과 null
    out.facilities = [FacilityDetail.model_validate(row) for row in apartment_detail.facilities(db, id)]
    if out.facilities:
        out.facilities_base_date = apartment_detail.facilities_base_date(db)
    return out
