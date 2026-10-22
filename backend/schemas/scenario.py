"""시나리오 API의 요청과 응답 모양. 담당: 박채은

- A-07 POST /api/apartments/{id}/scenario : ScenarioIn, ScenarioOut (API 명세서 3.2)

조건 묶음(Conditions)은 A-05와 같은 것을 쓴다 (API 명세서 2.2). 금액은 모두 원 단위 정수다.
"""
from typing import Annotated, Literal

from pydantic import BaseModel, Field, StrictInt

from backend.schemas.apartment import Category, Conditions


class ScenarioIn(BaseModel):
    """A-07 요청"""

    conditions: Conditions
    area_band: StrictInt  # 고른 면적대. ㎡


class ScenarioApartment(BaseModel):
    id: int
    name: str
    area_band: int  # 면적대. ㎡
    exclusive_area: float  # 대표 전용면적. ㎡
    supply_area: float | None  # 공급면적. 없으면 null


class LoanWithProduct(BaseModel):
    """상품을 골랐을 때의 대출 (FR-RESULT-05)"""

    choice: Literal["product"]
    product_id: int
    product_name: str
    repayment_years: int
    amount: int  # 예상 대출금액 (C-05)
    monthly_payment: int  # 예상 월 상환액 (C-07)
    max_house_price: int | None  # 대상 주택 가격 상한. 없으면 null
    over_price_cap: bool  # 평균가가 상한을 넘으면 true (FR-LOAN-14). 계산에서 빼지는 않는다


class LoanNone(BaseModel):
    """대출 없이 계산이면 choice만 준다 (FR-RESULT-05, C-13)"""

    choice: Literal["none"]


class ScenarioOut(BaseModel):
    """A-07 응답"""

    apartment: ScenarioApartment
    price: int  # 목표 부동산 가격. 그 면적의 평균가 (C-04)
    current_assets: int
    monthly_saving: int
    target_years: int
    accumulated_saving: int  # 누적 저축액 (C-02)
    own_funds: int  # 목표 시점 자기자금 (C-03)
    loan: Annotated[LoanWithProduct | LoanNone, Field(discriminator="choice")]
    category: Category  # 3단계 구분 (C-09)
    shortage: int  # 부족자금 (C-10). 음수면 그 절댓값이 여유자금
    required_monthly_saving: int | None  # 필요 월 저축액 (C-11). 부족자금이 0 이하이거나 "지금"이면 null
    allowed_growth_rate: float | None  # 허용 상승률, 연 % (C-12). 음수이거나 "지금"이면 null
