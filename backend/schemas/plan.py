"""저축 계획 계산 API(A-04)의 요청과 응답 모양. 담당: 김해원

저장(A-11)의 요청은 schemas/profile.py의 PlanIn이다. 여기는 저장하지 않는 계산만 다룬다.
"""
from pydantic import BaseModel, StrictInt, field_validator

from backend.schemas.common import check_asset, check_monthly_saving, check_target_years


class PlanCalcIn(BaseModel):
    """A-04 요청. 금액은 원 단위 정수다."""

    current_assets: StrictInt
    monthly_saving: StrictInt
    target_years: StrictInt  # 0, 3, 5, 10 중 하나. 0은 "지금"

    _assets = field_validator("current_assets")(check_asset)
    _saving = field_validator("monthly_saving")(check_monthly_saving)
    _years = field_validator("target_years")(check_target_years)


class PlanCalcOut(BaseModel):
    """A-04 응답"""

    accumulated_saving: int  # 누적 저축액 (C-02)
    own_funds: int  # 목표 시점 자기자금 (C-03)
