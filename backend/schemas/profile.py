"""재무정보 저장 API(A-08 ~ A-11, A-29 ~ A-34)의 요청과 응답 모양.

재무정보는 회원 한 명에 3개까지다 (2026-10-21). A-29 ~ A-34는 시작 화면의 재무정보 칸이 쓴다.

주민등록번호는 받지 않는다. 화면이 계산한 만 나이만 받는다 (NFR-25).
"""
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, StrictBool, StrictInt, field_validator, model_validator

from backend.schemas.common import check_age, check_asset, check_monthly_saving, check_target_years


class FinanceIn(BaseModel):
    """A-09 요청"""

    age: StrictInt
    annual_income: StrictInt
    current_assets: StrictInt
    restart: StrictBool = False  # true면 대출 선택과 저축 계획을 함께 지운다

    _age = field_validator("age")(check_age)
    _money = field_validator("annual_income", "current_assets")(check_asset)


def check_loan_combination(body):
    """대출 선택 세 값의 조합 (API 명세서 2.2). A-10과 A-30, A-31이 함께 쓴다."""
    has_product = body.loan_product_id is not None and body.repayment_years is not None
    has_nothing = body.loan_product_id is None and body.repayment_years is None
    if body.loan_choice == "product" and not has_product:
        raise ValueError("대출 상품과 상환 기간을 골라 주세요.")
    if body.loan_choice == "none" and not has_nothing:
        raise ValueError("대출 상품과 상환 기간을 골라 주세요.")
    return body


class LoanChoiceIn(BaseModel):
    """A-10 요청"""

    loan_choice: Literal["product", "none"]
    loan_product_id: StrictInt | None = None
    repayment_years: StrictInt | None = None

    @model_validator(mode="after")
    def check_combination(self):
        return check_loan_combination(self)


class PlanIn(BaseModel):
    """A-11 요청"""

    monthly_saving: StrictInt
    target_years: StrictInt

    _saving = field_validator("monthly_saving")(check_monthly_saving)
    _years = field_validator("target_years")(check_target_years)


class ProfileIn(BaseModel):
    """A-30, A-31 요청. 일곱 값을 한 번에 받는다 (A-09 ~ A-11과 같은 규칙)."""

    age: StrictInt
    annual_income: StrictInt
    current_assets: StrictInt
    loan_choice: Literal["product", "none"]
    loan_product_id: StrictInt | None = None
    repayment_years: StrictInt | None = None
    monthly_saving: StrictInt
    target_years: StrictInt

    _age = field_validator("age")(check_age)
    _money = field_validator("annual_income", "current_assets")(check_asset)
    _saving = field_validator("monthly_saving")(check_monthly_saving)
    _years = field_validator("target_years")(check_target_years)

    @model_validator(mode="after")
    def check_combination(self):
        return check_loan_combination(self)


MSG_NAME = "이름은 1자 이상 10자 이하로 입력해 주세요."
NAME_MAX = 10


class NameIn(BaseModel):
    """A-32 요청. 앞뒤 빈칸을 뗀 뒤 1 ~ 10자"""

    name: str

    @field_validator("name")
    @classmethod
    def check_name(cls, value: str) -> str:
        value = value.strip()
        if not 1 <= len(value) <= NAME_MAX:
            raise ValueError(MSG_NAME)
        return value


class Profile(BaseModel):
    # models의 Profile을 그대로 넘기면 이 모양으로 바뀐다.
    model_config = ConfigDict(from_attributes=True)

    id: int  # 재무정보 번호 (2026-10-21)
    slot: int  # 칸 번호 1 ~ 3
    name: str  # 칸 이름
    age: int
    annual_income: int
    current_assets: int
    loan_choice: Literal["product", "none"] | None
    loan_product_id: int | None
    loan_product_name: str | None
    repayment_years: int | None
    monthly_saving: int | None
    target_years: int | None
    updated_at: datetime


class ProfileOut(BaseModel):
    """A-08 ~ A-11, A-30 ~ A-32 응답. 저장한 것이 없으면 profile이 null이다."""

    profile: Profile | None


class ProfilesOut(BaseModel):
    """A-29 응답. 칸 번호 순. selected_id는 마지막으로 고른 재무정보 (없으면 칸 번호가 가장 작은 것, 하나도 없으면 null)"""

    profiles: list[Profile]
    selected_id: int | None
