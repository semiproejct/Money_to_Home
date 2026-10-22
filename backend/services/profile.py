"""재무정보를 읽고 쓰는 함수. 담당: 김해원 (재무정보 3개: 박채은, 2026-10-21)

회원 한 명에 3개까지다 (재무정보 1 ~ 3). 저장은 요청이 끝날 때 get_db가 한다. 여기서 commit하지 않는다.

- A-08 ~ A-11(입력 단계)은 profile_id로 어느 재무정보인지 고른다. 없으면 칸 번호가 가장 작은 재무정보다 (예전과 같은 동작).
- A-29 ~ A-34(시작 화면의 칸)는 일곱 값을 한 번에 더하고 고치고, 이름을 바꾸고, 지우고, 고른 것을 남긴다.
- 남의 재무정보나 없는 번호는 404다. 누구의 것인지는 deps가 정한 회원 번호로만 본다 (FR-USER-15).
"""
from datetime import datetime

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from backend.errors import ApiError
from backend.models import Profile, SavedResult
from backend.services import loan_product

MSG_FINANCE_FIRST = "재무정보를 먼저 입력해 주세요."
MSG_CHOOSE_LOAN = "대출 상품과 상환 기간을 골라 주세요."
MSG_CHOOSE_YEARS = "상환 기간을 다시 골라 주세요."
MSG_NOT_FOUND = "재무정보를 찾을 수 없습니다."
MSG_TOO_MANY = "재무정보는 3개까지 저장할 수 있습니다."
MAX_PROFILES = 3


def find_all(db: Session, user_id: int) -> list[Profile]:
    """내 재무정보. 칸 번호 순"""
    return list(db.scalars(select(Profile).where(Profile.user_id == user_id).order_by(Profile.slot)).all())


def find_mine(db: Session, user_id: int, profile_id: int) -> Profile:
    """번호로 찾은 내 재무정보. 없거나 남의 것이면 404"""
    profile = db.get(Profile, profile_id)
    if profile is None or profile.user_id != user_id:
        raise ApiError(404, MSG_NOT_FOUND)
    return profile


def find_by_user(db: Session, user_id: int, profile_id: int | None = None) -> Profile | None:
    """A-08. profile_id가 있으면 그 재무정보, 없으면 칸 번호가 가장 작은 재무정보. 하나도 없으면 None"""
    if profile_id is not None:
        return find_mine(db, user_id, profile_id)
    profiles = find_all(db, user_id)
    return profiles[0] if profiles else None


def selected_id(profiles: list[Profile]) -> int | None:
    """A-29의 selected_id. 마지막으로 고른 재무정보, 고른 적이 없으면 칸 번호가 가장 작은 것"""
    if not profiles:
        return None
    chosen = [p for p in profiles if p.selected_at is not None]
    if chosen:
        return max(chosen, key=lambda p: (p.selected_at, p.id)).id
    return profiles[0].id


def _require(db: Session, user_id: int, profile_id: int | None) -> Profile:
    profile = find_by_user(db, user_id, profile_id)
    if profile is None:
        raise ApiError(422, MSG_FINANCE_FIRST)
    return profile


def _saved(db: Session, profile: Profile) -> Profile:
    """DB에 보내고, DB가 정한 값(번호, 수정한 시각, 상품 이름)을 다시 읽는다."""
    db.flush()
    db.refresh(profile)
    return profile


def _new(db: Session, user_id: int) -> Profile:
    """비어 있는 가장 작은 칸 번호로 새 줄을 만든다. 이름은 "재무정보 칸번호". 3개면 422"""
    used = {p.slot for p in find_all(db, user_id)}
    free = [slot for slot in range(1, MAX_PROFILES + 1) if slot not in used]
    if not free:
        raise ApiError(422, MSG_TOO_MANY)
    profile = Profile(user_id=user_id, slot=free[0], name=f"재무정보 {free[0]}")
    db.add(profile)
    return profile


def _check_loan(db: Session, loan_choice: str, loan_product_id: int | None, repayment_years: int | None) -> None:
    """상품을 골랐으면 있는 상품인지, 그 상품에 있는 상환 기간인지 확인한다."""
    if loan_choice != "product":
        return
    product = loan_product.find_by_id(db, loan_product_id)
    if product is None:
        raise ApiError(422, MSG_CHOOSE_LOAN, "loan_product_id")
    if repayment_years not in product.repayment_years_list:
        raise ApiError(422, MSG_CHOOSE_YEARS, "repayment_years")


# ── A-09 ~ A-11 입력 단계 ─────────────────────────────

def save_finance(db: Session, user_id: int, age: int, annual_income: int, current_assets: int, restart: bool,
                 profile_id: int | None = None) -> Profile:
    """재무정보를 저장한다. 하나도 없으면 재무정보 1을 만들고 있으면 고친다.

    restart면 "처음부터 다시 입력"이다. 대출 선택과 저축 계획을 함께 지운다 (DB 설계서 3.2).
    """
    profile = find_by_user(db, user_id, profile_id)
    if profile is None:
        profile = _new(db, user_id)
    profile.age = age
    profile.annual_income = annual_income
    profile.current_assets = current_assets
    if restart:
        profile.loan_choice = None
        profile.loan_product_id = None
        profile.repayment_years = None
        profile.monthly_saving = None
        profile.target_years = None
    return _saved(db, profile)


def save_loan(db: Session, user_id: int, loan_choice: str, loan_product_id: int | None, repayment_years: int | None,
              profile_id: int | None = None) -> Profile:
    """대출 선택을 저장한다. 상품을 골랐으면 그 상품에 있는 상환 기간인지 확인한다."""
    profile = _require(db, user_id, profile_id)
    _check_loan(db, loan_choice, loan_product_id, repayment_years)
    profile.loan_choice = loan_choice
    profile.loan_product_id = loan_product_id
    profile.repayment_years = repayment_years
    return _saved(db, profile)


def save_plan(db: Session, user_id: int, monthly_saving: int, target_years: int, profile_id: int | None = None) -> Profile:
    profile = _require(db, user_id, profile_id)
    profile.monthly_saving = monthly_saving
    profile.target_years = target_years
    return _saved(db, profile)


# ── A-29 ~ A-34 시작 화면의 재무정보 칸 (2026-10-21) ─────

def _fill(profile: Profile, values: dict) -> None:
    for key in ("age", "annual_income", "current_assets", "loan_choice", "loan_product_id", "repayment_years",
                "monthly_saving", "target_years"):
        setattr(profile, key, values[key])


def create(db: Session, user_id: int, values: dict) -> Profile:
    """A-30. 일곱 값으로 새 재무정보를 더한다. 3개면 422"""
    _check_loan(db, values["loan_choice"], values["loan_product_id"], values["repayment_years"])
    profile = _new(db, user_id)
    _fill(profile, values)
    return _saved(db, profile)


def replace(db: Session, user_id: int, profile_id: int, values: dict) -> Profile:
    """A-31. 일곱 값을 한 번에 고친다. 이름과 칸 번호는 그대로"""
    profile = find_mine(db, user_id, profile_id)
    _check_loan(db, values["loan_choice"], values["loan_product_id"], values["repayment_years"])
    _fill(profile, values)
    return _saved(db, profile)


def rename(db: Session, user_id: int, profile_id: int, name: str) -> Profile:
    """A-32. 이름은 schemas가 앞뒤 빈칸을 떼고 1 ~ 10자인지 확인했다."""
    profile = find_mine(db, user_id, profile_id)
    profile.name = name
    return _saved(db, profile)


def delete(db: Session, user_id: int, profile_id: int) -> None:
    """A-33. 재무정보를 지운다. 그 재무정보로 한 찜은 남기고 연결만 비운다 ("삭제된 재무정보").

    MariaDB는 외래키(ON DELETE SET NULL)가 비우지만, 테스트의 SQLite는 외래키를 보지 않으므로 여기서 먼저 비운다.
    """
    profile = find_mine(db, user_id, profile_id)
    db.execute(
        update(SavedResult)
        .where(SavedResult.user_id == user_id, SavedResult.profile_id == profile.id)
        .values(profile_id=None)
    )
    db.delete(profile)
    db.flush()


def select_one(db: Session, user_id: int, profile_id: int) -> None:
    """A-34. 이 재무정보를 골랐다고 남긴다. 다음 로그인 때 A-29의 selected_id가 이것이다."""
    profile = find_mine(db, user_id, profile_id)
    profile.selected_at = datetime.now()
    db.flush()
