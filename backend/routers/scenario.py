"""시나리오(필요자금 결과). 담당: 박채은

- A-07 POST /api/apartments/{id}/scenario : 아파트 한 곳의 시나리오 (API 명세서 3.2)

요청의 conditions만 쓴다. 로그인 정보와 profiles 표를 읽지 않는다 (NFR-18).
계산식은 여기에 쓰지 않는다. backend/services/calc.py의 함수를 부른다 (NFR-13).
DB는 backend/services/scenario.py가 읽는다.
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.schemas.scenario import ScenarioIn, ScenarioOut
from backend.services import scenario

router = APIRouter(prefix="/api", tags=["시나리오"])


@router.post("/apartments/{id}/scenario", response_model=ScenarioOut)
def apartment_scenario(id: int, body: ScenarioIn, db: Session = Depends(get_db)):
    return scenario.scenario(db, id, body.area_band, body.conditions)
