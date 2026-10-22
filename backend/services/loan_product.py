"""대출 상품을 읽는 함수. 담당: 박채은

routers는 DB를 직접 다루지 않고 이 파일의 함수를 부른다.
"""
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.models import LoanProduct


def find_all(db: Session) -> list[LoanProduct]:
    """상품 전부. 번호 순서다. 카드를 이 순서로 보여 준다."""
    return list(db.scalars(select(LoanProduct).order_by(LoanProduct.id)).all())


def find_by_id(db: Session, product_id: int) -> LoanProduct | None:
    return db.get(LoanProduct, product_id)


def for_calc(product: LoanProduct | None) -> dict | None:
    """계산 모듈(services/calc.py)에 넘길 모양으로 바꾼다. 대출 없이 계산이면 None을 그대로 넘긴다.

        product = loan_product.for_calc(loan_product.find_by_id(db, 1))
        loan = calc.loan_amount(avg_price, product)
    """
    if product is None:
        return None
    return {
        "max_limit": product.max_limit,
        "ltv_ratio": product.ltv_ratio,
        "annual_rate_pct": product.annual_rate_pct,
        "max_house_price": product.max_house_price,
    }
