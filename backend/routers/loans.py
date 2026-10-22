"""대출 상품. 담당: 박채은

- A-01 GET  /api/loan-products : 상품 목록 (만들어 둠)
- A-03 POST /api/calc/loan     : 대출 계산 (API 명세서 3.2)

router는 요청을 받아 services의 함수를 부르고 응답을 만든다. DB를 다루는 코드와 계산식을 여기에 쓰지 않는다.
DB는 backend/services/loan_product.py, 계산은 backend/services/calc.py에 있다 (NFR-13).
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.errors import ApiError
from backend.schemas.loan import LoanCalcIn, LoanCalcOut, LoanProductsOut
from backend.services import calc, loan_product

router = APIRouter(prefix="/api", tags=["대출 상품"])

# API 명세서 5장의 문장. A-10(대출 선택 저장)과 같은 문장이다.
MSG_CHOOSE_LOAN = "대출 상품과 상환 기간을 골라 주세요."
MSG_CHOOSE_YEARS = "상환 기간을 다시 골라 주세요."


@router.get("/loan-products", response_model=LoanProductsOut)
def list_loan_products(db: Session = Depends(get_db)):
    return {"products": loan_product.find_all(db)}


@router.post("/calc/loan", response_model=LoanCalcOut)
def calc_loan(body: LoanCalcIn, db: Session = Depends(get_db)):
    """아파트를 고르기 전의 대출 계산. 저장하지 않는다.

    현재 보유자산으로 살 수 있는 가장 비싼 집을 기준으로 한 대출금액이다 (C-06).
    "대출 없이 계산"을 골랐을 때는 화면이 이 API를 부르지 않는다.
    """
    product = loan_product.find_by_id(db, body.loan_product_id)
    if product is None:
        raise ApiError(422, MSG_CHOOSE_LOAN, "loan_product_id")
    if body.repayment_years is not None and body.repayment_years not in product.repayment_years_list:
        raise ApiError(422, MSG_CHOOSE_YEARS, "repayment_years")

    conditions = loan_product.for_calc(product)
    max_loan = calc.max_loan_amount(body.current_assets, conditions)
    monthly = None
    if body.repayment_years is not None:
        monthly = calc.monthly_payment(max_loan, conditions["annual_rate_pct"], body.repayment_years)
    return {"max_loan_amount": max_loan, "monthly_payment": monthly}
