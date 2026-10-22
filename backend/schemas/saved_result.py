"""결과 저장 API의 요청과 응답 모양. 담당: 박채은

- A-21 POST /api/saved-results      : SavedResultIn → SavedResultOut (201)
- A-22 GET  /api/saved-results      : SavedResultsOut
- A-23 GET  /api/saved-results/{id} : SavedResultOut
- A-35 DELETE /api/saved-results/{id} : 204. 찜 해제 (2026-10-21)

요청에는 계산 결과를 받지 않는다. 조건과 아파트만 받고 서버가 다시 계산해 저장한다 (API 명세서 3.5, NFR-13).
응답의 모양은 시나리오(A-07)와 같게 맞췄다. 화면이 시나리오 탭과 같은 함수로 그릴 수 있게 한다.
금액은 모두 원 단위 정수다.
"""
from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, Field, StrictInt

from backend.schemas.apartment import Category, Conditions


class SavedResultIn(BaseModel):
    """A-21 요청"""

    conditions: Conditions
    apartment_id: StrictInt
    area_band: StrictInt  # 고른 면적대. ㎡
    profile_id: StrictInt | None = None  # 찜할 때 고른 재무정보 (2026-10-21). 없어도 된다


class SavedApartment(BaseModel):
    """저장 당시의 아파트. 원본이 지워졌으면 id가 null이다."""

    id: int | None
    name: str
    gu: str
    dong: str
    area_band: int
    exclusive_area: float
    supply_area: float | None


class SavedLoanWithProduct(BaseModel):
    choice: Literal["product"]
    product_id: int | None  # 원본 상품이 지워졌으면 null
    product_name: str
    repayment_years: int
    amount: int  # 예상 대출금액
    monthly_payment: int  # 예상 월 상환액


class SavedLoanNone(BaseModel):
    choice: Literal["none"]


class SavedResultOut(BaseModel):
    """저장한 결과 하나. 저장할 때의 값 그대로다 (다시 계산하지 않는다)."""

    id: int
    created_at: datetime  # 저장한 시각
    profile_id: int | None  # 찜한 재무정보. 지웠거나 모르면 null ("삭제된 재무정보", 2026-10-21)
    apartment: SavedApartment
    price: int  # 저장 당시 평균가 (목표 부동산 가격)
    current_assets: int
    monthly_saving: int
    target_years: int
    accumulated_saving: int
    own_funds: int  # 목표 시점 자기자금
    loan: Annotated[SavedLoanWithProduct | SavedLoanNone, Field(discriminator="choice")]
    category: Category
    shortage: int  # 음수면 그 절댓값이 여유자금
    required_monthly_saving: int | None
    allowed_growth_rate: float | None


class SavedResultsOut(BaseModel):
    """A-22 응답. 최근 것부터"""

    results: list[SavedResultOut]
