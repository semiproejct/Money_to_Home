"""대출 상품 API의 요청과 응답 모양.

A-01(상품 목록)의 응답과 A-03(대출 계산)의 요청과 응답이 들어 있다.
"""
from datetime import date

from pydantic import BaseModel, ConfigDict, Field, StrictInt, field_validator

from backend.schemas.common import check_asset


class LoanProduct(BaseModel):
    # models의 LoanProduct를 그대로 넘기면 이 모양으로 바뀐다.
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    institution: str
    max_limit: int  # 최대 한도. 원
    ltv_ratio: float  # 대출 비율. 70%면 0.7
    annual_rate_pct: float  # 대표 금리. 연 4.0%면 4.0
    # DB에는 "10,15,20,30"으로 들어 있다. models가 숫자의 목록으로 바꿔 준 값을 쓴다.
    repayment_years_options: list[int] = Field(validation_alias="repayment_years_list")
    max_house_price: int | None  # 대상 주택 가격 상한. 없으면 null
    eligibility_summary: str
    eligibility_text: str
    base_date: date
    source_url: str


class LoanProductsOut(BaseModel):
    """A-01 응답"""

    products: list[LoanProduct]


class LoanCalcIn(BaseModel):
    """A-03 요청. 금액은 원 단위 정수다.

    상환 기간을 아직 고르지 않았으면 repayment_years를 null로 보낸다 (P-03 ②).
    상품이 있는지, 기간이 그 상품의 선택지인지는 DB를 봐야 알 수 있어 router에서 확인한다.
    """

    current_assets: StrictInt
    loan_product_id: StrictInt
    repayment_years: StrictInt | None  # null이면 월 상환액을 계산하지 않는다

    _assets = field_validator("current_assets")(check_asset)

    @field_validator("loan_product_id", mode="before")
    @classmethod
    def check_product_chosen(cls, value):
        # 상품을 고르지 않고 부르면 API 명세서 5장의 문장으로 알린다.
        if value is None:
            raise ValueError("대출 상품과 상환 기간을 골라 주세요.")
        return value


class LoanCalcOut(BaseModel):
    """A-03 응답"""

    max_loan_amount: int  # 최대 예상 대출금액 (C-06)
    monthly_payment: int | None  # 예상 월 상환액 (C-07). 상환 기간을 고르지 않았으면 null
