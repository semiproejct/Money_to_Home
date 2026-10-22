"""시나리오에 쓰는 DB 함수. 담당: 박채은

routers/scenario.py가 부른다. 저장은 하지 않는다 (읽기만 한다).
요청에 든 값만 쓴다. 로그인 정보와 profiles 표를 읽지 않는다 (NFR-18).
계산은 services/calc.py의 함수만 부른다 (NFR-13).
"""
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.errors import ApiError
from backend.models import Apartment, ApartmentPrice
from backend.services import calc, loan_product
from backend.services.apartment import _product_for

# API 명세서 A-06의 문장. 없는 면적도 같은 문장을 쓴다 (명세서 A-07에 따로 정한 문장이 없다).
MSG_NO_APARTMENT = "아파트를 찾을 수 없습니다."


def find_price(db: Session, apartment_id: int, area_band: int) -> ApartmentPrice | None:
    """아파트 한 곳의 한 면적대. 없는 아파트이거나 그 면적대의 평균가가 없으면 None."""
    return db.scalars(
        select(ApartmentPrice).where(
            ApartmentPrice.apartment_id == apartment_id,
            ApartmentPrice.area_band == area_band,
        )
    ).first()


def scenario(db: Session, apartment_id: int, area_band: int, conditions) -> dict:
    """A-07 시나리오. 고른 아파트와 면적의 계산 결과.

    - 조건의 대출 조합은 A-05와 같은 규칙으로 검사한다 (services/apartment.py의 _product_for). 걸리면 422.
    - 없는 아파트나 없는 면적이면 404 "아파트를 찾을 수 없습니다."
    - 대출 없이 계산이면 loan은 {"choice": "none"}만 준다 (FR-RESULT-05).
    - 필요 월 저축액은 부족자금이 0보다 클 때만 준다 (C-11). 허용 상승률은 calc가 null을 정한다 (C-12).
    """
    product = _product_for(db, conditions)

    row = find_price(db, apartment_id, area_band)
    if row is None:
        raise ApiError(404, MSG_NO_APARTMENT)
    apartment = db.get(Apartment, apartment_id)

    price = row.avg_price
    current = conditions.current_assets
    years = conditions.target_years
    accumulated = calc.accumulated_saving(conditions.monthly_saving, years)
    own = calc.own_funds(current, accumulated)
    loan = calc.loan_amount(price, product)
    shortage = calc.shortage(price, own, loan)

    if product is None:
        loan_part = {"choice": "none"}
    else:
        chosen = loan_product.find_by_id(db, conditions.loan_product_id)
        cap = product["max_house_price"]
        loan_part = {
            "choice": "product",
            "product_id": chosen.id,
            "product_name": chosen.name,
            "repayment_years": conditions.repayment_years,
            "amount": loan,
            "monthly_payment": calc.monthly_payment(loan, product["annual_rate_pct"], conditions.repayment_years),
            "max_house_price": cap,
            "over_price_cap": cap is not None and price > cap,
        }

    return {
        "apartment": {
            "id": apartment.id,
            "name": apartment.name,
            "area_band": row.area_band,
            "exclusive_area": float(row.exclusive_area),
            "supply_area": None if row.supply_area is None else float(row.supply_area),
        },
        "price": price,
        "current_assets": current,
        "monthly_saving": conditions.monthly_saving,
        "target_years": years,
        "accumulated_saving": accumulated,
        "own_funds": own,
        "loan": loan_part,
        "category": calc.category(current, own, loan, price, years),
        "shortage": shortage,
        "required_monthly_saving": (
            calc.required_monthly_saving(price, loan, current, years) if shortage > 0 else None
        ),
        "allowed_growth_rate": calc.allowed_growth_rate(calc.target_price(own, product), price, years),
    }
