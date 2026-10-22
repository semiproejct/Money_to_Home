"""저축 계획. 담당: 김해원

- A-04 POST /api/calc/plan : 저축 계획 계산 (API 명세서 3.2)

계산식은 여기에 쓰지 않는다. backend/services/calc.py의 함수를 부른다 (NFR-13).
DB를 읽지 않는다. 받은 값으로 계산만 해서 돌려준다. 저장은 A-11(routers/profile.py)이 한다.
"""
from fastapi import APIRouter

from backend.schemas.plan import PlanCalcIn, PlanCalcOut
from backend.services import calc

router = APIRouter(prefix="/api", tags=["저축 계획"])


@router.post("/calc/plan", response_model=PlanCalcOut)
def calc_plan(body: PlanCalcIn):
    accumulated = calc.accumulated_saving(body.monthly_saving, body.target_years)
    return {
        "accumulated_saving": accumulated,
        "own_funds": calc.own_funds(body.current_assets, accumulated),
    }
