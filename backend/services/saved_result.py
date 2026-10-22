"""저장한 결과를 읽고 쓰는 함수. 담당: 박채은

routers/saved_results.py가 부른다. 저장은 요청이 끝날 때 get_db가 한다. 여기서 commit하지 않는다.

- 저장할 때는 화면이 보낸 숫자를 쓰지 않는다. 시나리오(A-07)와 같은 함수로 서버가 다시 계산한다 (NFR-13).
- 저장할 때의 아파트 이름, 구, 동, 평균가, 상품명을 복사해 둔다. 원본이 바뀌거나 지워져도 그대로 보인다.
- 남의 것은 없는 것과 같다 (404). 누구의 것인지는 deps.require_login이 정한 회원 번호로만 본다 (FR-USER-15).
"""
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.errors import ApiError
from backend.models import Apartment, SavedResult
from backend.services import calc, scenario
from backend.services import profile as profile_service

MSG_NOT_FOUND = "저장한 결과를 찾을 수 없습니다."


def save(db: Session, user_id: int, conditions, apartment_id: int, area_band: int, profile_id: int | None = None) -> dict:
    """A-21. 다시 계산해서 저장하고, 저장한 것을 돌려준다.

    없는 아파트나 면적, 맞지 않는 대출 조합은 시나리오와 같은 오류(404, 422)다.
    profile_id는 찜할 때 고른 재무정보다. 남의 것이나 없는 번호면 404 (2026-10-21)
    """
    if profile_id is not None:
        profile_service.find_mine(db, user_id, profile_id)
    result = scenario.scenario(db, apartment_id, area_band, conditions)
    apartment = db.get(Apartment, apartment_id)
    loan = result["loan"]
    with_loan = loan["choice"] == "product"

    row = SavedResult(
        user_id=user_id,
        apartment_id=apartment.id,
        loan_product_id=loan["product_id"] if with_loan else None,
        profile_id=profile_id,
        apartment_name=apartment.name,
        gu=apartment.gu,
        dong=apartment.dong,
        area_band=result["apartment"]["area_band"],
        exclusive_area=Decimal(str(result["apartment"]["exclusive_area"])),
        supply_area=None if result["apartment"]["supply_area"] is None else Decimal(str(result["apartment"]["supply_area"])),
        avg_price=result["price"],
        current_assets=result["current_assets"],
        monthly_saving=result["monthly_saving"],
        target_years=result["target_years"],
        loan_choice=loan["choice"],
        loan_product_name=loan["product_name"] if with_loan else None,
        repayment_years=loan["repayment_years"] if with_loan else None,
        accumulated_saving=result["accumulated_saving"],
        loan_amount=loan["amount"] if with_loan else None,
        monthly_payment=loan["monthly_payment"] if with_loan else None,
        shortage=result["shortage"],
        required_monthly_saving=result["required_monthly_saving"],
        allowed_growth_rate=None if result["allowed_growth_rate"] is None else Decimal(str(result["allowed_growth_rate"])),
        category=result["category"],
    )
    db.add(row)
    db.flush()
    db.refresh(row)  # DB가 정한 번호와 저장한 시각
    return to_out(row)


def find_all(db: Session, user_id: int) -> list[dict]:
    """A-22. 내가 저장한 결과. 최근 것부터"""
    rows = db.scalars(
        select(SavedResult)
        .where(SavedResult.user_id == user_id)
        .order_by(SavedResult.created_at.desc(), SavedResult.id.desc())
    ).all()
    return [to_out(row) for row in rows]


def find_one(db: Session, user_id: int, result_id: int) -> dict:
    """A-23. 없거나 남의 것이면 404"""
    row = db.get(SavedResult, result_id)
    if row is None or row.user_id != user_id:
        raise ApiError(404, MSG_NOT_FOUND)
    return to_out(row)


def delete(db: Session, user_id: int, result_id: int) -> None:
    """A-35. 찜 해제. 없거나 남의 것이면 404 (2026-10-21)"""
    row = db.get(SavedResult, result_id)
    if row is None or row.user_id != user_id:
        raise ApiError(404, MSG_NOT_FOUND)
    db.delete(row)
    db.flush()


def to_out(row: SavedResult) -> dict:
    """표의 한 줄을 응답 모양(시나리오 A-07과 같은 모양)으로 바꾼다. 다시 계산하지 않는다.

    자기자금은 표에 없어서 저장한 보유자산과 누적 저축액으로 calc.own_funds를 불러 채운다 (C-03).
    """
    if row.loan_choice == "product":
        loan = {
            "choice": "product",
            "product_id": row.loan_product_id,
            "product_name": row.loan_product_name,
            "repayment_years": row.repayment_years,
            "amount": row.loan_amount,
            "monthly_payment": row.monthly_payment,
        }
    else:
        loan = {"choice": "none"}

    return {
        "id": row.id,
        "created_at": row.created_at,
        "profile_id": row.profile_id,
        "apartment": {
            "id": row.apartment_id,
            "name": row.apartment_name,
            "gu": row.gu,
            "dong": row.dong,
            "area_band": row.area_band,
            "exclusive_area": float(row.exclusive_area),
            "supply_area": None if row.supply_area is None else float(row.supply_area),
        },
        "price": row.avg_price,
        "current_assets": row.current_assets,
        "monthly_saving": row.monthly_saving,
        "target_years": row.target_years,
        "accumulated_saving": row.accumulated_saving,
        "own_funds": calc.own_funds(row.current_assets, row.accumulated_saving),
        "loan": loan,
        "category": row.category,
        "shortage": row.shortage,
        "required_monthly_saving": row.required_monthly_saving,
        "allowed_growth_rate": None if row.allowed_growth_rate is None else float(row.allowed_growth_rate),
    }
