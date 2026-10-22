"""재무정보 저장. 담당: 김해원 (재무정보 3개 A-29 ~ A-34: 박채은, 2026-10-21)

- A-08 GET /api/profile         : 저장한 재무정보
- A-09 PUT /api/profile/finance : 재무정보 저장
- A-10 PUT /api/profile/loan    : 대출 선택 저장
- A-11 PUT /api/profile/plan    : 저축 계획 저장
  네 API 모두 주소 끝에 ?profile_id=번호를 붙여 어느 재무정보인지 고른다. 없으면 칸 번호가 가장 작은 재무정보다.

- A-29 GET    /api/profiles             : 내 재무정보 목록 (3개까지)과 고른 재무정보
- A-30 POST   /api/profiles             : 재무정보 더하기 (일곱 값)
- A-31 PUT    /api/profiles/{id}        : 재무정보 고치기 (일곱 값)
- A-32 PUT    /api/profiles/{id}/name   : 이름 바꾸기
- A-33 DELETE /api/profiles/{id}        : 지우기. 그 재무정보로 한 찜은 남는다
- A-34 PUT    /api/profiles/{id}/select : 고른 재무정보를 남긴다

로그인한 회원의 값을 읽고 쓴다. 로그인하지 않았으면 401이다. 누구의 값인지는 deps.py가 정한다.
router는 요청을 받아 services의 함수를 부르고 응답을 만든다. DB를 다루는 일은 backend/services/profile.py에 있다.
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.deps import get_current_user_id
from backend.schemas.profile import FinanceIn, LoanChoiceIn, NameIn, PlanIn, ProfileIn, ProfileOut, ProfilesOut
from backend.services import profile

router = APIRouter(prefix="/api/profile", tags=["재무정보"])
profiles_router = APIRouter(prefix="/api/profiles", tags=["재무정보"])


@router.get("", response_model=ProfileOut)
def get_profile(profile_id: int | None = None, db: Session = Depends(get_db), user_id: int = Depends(get_current_user_id)):
    return {"profile": profile.find_by_user(db, user_id, profile_id)}


@router.put("/finance", response_model=ProfileOut)
def put_finance(body: FinanceIn, profile_id: int | None = None, db: Session = Depends(get_db),
                user_id: int = Depends(get_current_user_id)):
    saved = profile.save_finance(db, user_id, body.age, body.annual_income, body.current_assets, body.restart, profile_id)
    return {"profile": saved}


@router.put("/loan", response_model=ProfileOut)
def put_loan(body: LoanChoiceIn, profile_id: int | None = None, db: Session = Depends(get_db),
             user_id: int = Depends(get_current_user_id)):
    saved = profile.save_loan(db, user_id, body.loan_choice, body.loan_product_id, body.repayment_years, profile_id)
    return {"profile": saved}


@router.put("/plan", response_model=ProfileOut)
def put_plan(body: PlanIn, profile_id: int | None = None, db: Session = Depends(get_db),
             user_id: int = Depends(get_current_user_id)):
    saved = profile.save_plan(db, user_id, body.monthly_saving, body.target_years, profile_id)
    return {"profile": saved}


# ── 재무정보 3개 (2026-10-21) ─────────────────────────

@profiles_router.get("", response_model=ProfilesOut)
def list_profiles(db: Session = Depends(get_db), user_id: int = Depends(get_current_user_id)):
    profiles = profile.find_all(db, user_id)
    return {"profiles": profiles, "selected_id": profile.selected_id(profiles)}


@profiles_router.post("", response_model=ProfileOut, status_code=201)
def create_profile(body: ProfileIn, db: Session = Depends(get_db), user_id: int = Depends(get_current_user_id)):
    return {"profile": profile.create(db, user_id, body.model_dump())}


@profiles_router.put("/{id}", response_model=ProfileOut)
def replace_profile(id: int, body: ProfileIn, db: Session = Depends(get_db), user_id: int = Depends(get_current_user_id)):
    return {"profile": profile.replace(db, user_id, id, body.model_dump())}


@profiles_router.put("/{id}/name", response_model=ProfileOut)
def rename_profile(id: int, body: NameIn, db: Session = Depends(get_db), user_id: int = Depends(get_current_user_id)):
    return {"profile": profile.rename(db, user_id, id, body.name)}


@profiles_router.delete("/{id}", status_code=204)
def delete_profile(id: int, db: Session = Depends(get_db), user_id: int = Depends(get_current_user_id)):
    profile.delete(db, user_id, id)


@profiles_router.put("/{id}/select", status_code=204)
def select_profile(id: int, db: Session = Depends(get_db), user_id: int = Depends(get_current_user_id)):
    profile.select_one(db, user_id, id)
