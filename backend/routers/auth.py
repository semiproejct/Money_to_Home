"""회원 (2차). 담당: 김해원

- A-14 POST /api/auth/login-id/check : 아이디를 쓸 수 있는가
- A-15 POST /api/auth/signup         : 회원가입. 가입과 함께 로그인된다
- A-16 POST /api/auth/login          : 로그인
- A-17 POST /api/auth/logout         : 로그아웃
- A-18 GET  /api/auth/me             : 로그인 상태 확인
- A-19 PUT  /api/auth/password       : 비밀번호 변경 (3차)
- A-20 DELETE /api/auth/me           : 회원 탈퇴 (3차). 재무정보와 저장한 결과도 함께 지운다

로그인 상태는 서명한 쿠키로 확인한다. 쿠키와 비밀번호를 다루는 일은 backend/services/auth.py에 있다.
로그인하지 않아도 계산과 탐색은 그대로 된다. 이 API들은 저장 기능을 쓰는 회원을 위한 것이다.
"""
from fastapi import APIRouter, Depends, Response
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.deps import require_login
from backend.errors import ApiError
from backend.models import User
from backend.schemas.auth import AvailableOut, LoginIdIn, LoginIn, LoginOut, PasswordIn, SignupIn, WithdrawIn
from backend.services import auth

router = APIRouter(prefix="/api/auth", tags=["회원"])


@router.post("/login-id/check", response_model=AvailableOut)
def check_login_id(body: LoginIdIn, db: Session = Depends(get_db)):
    auth.check_available(db, body.login_id)
    return {"available": True}


@router.post("/signup", response_model=LoginOut, status_code=201)
def signup(body: SignupIn, response: Response, db: Session = Depends(get_db)):
    user = auth.signup(db, body.login_id, body.password, body.agreed)
    auth.set_cookie(response, user.id)  # 가입과 함께 로그인된다 (FR-USER-01)
    return {"login_id": user.login_id}


@router.post("/login", response_model=LoginOut)
def login(body: LoginIn, response: Response, db: Session = Depends(get_db)):
    user = auth.login(db, body.login_id, body.password)
    auth.set_cookie(response, user.id)
    return {"login_id": user.login_id}


@router.post("/logout", status_code=204)
def logout(response: Response, user_id: int = Depends(require_login)):
    auth.clear_cookie(response)


@router.get("/me", response_model=LoginOut)
def me(db: Session = Depends(get_db), user_id: int = Depends(require_login)):
    user = db.get(User, user_id)
    if user is None:  # 쿠키는 맞지만 회원이 없다 (탈퇴 등)
        raise ApiError(401, auth.MSG_LOGIN_REQUIRED)
    return {"login_id": user.login_id}


@router.put("/password", status_code=204)
def change_password(body: PasswordIn, db: Session = Depends(get_db), user_id: int = Depends(require_login)):
    auth.change_password(db, user_id, body.current_password, body.new_password)


@router.delete("/me", status_code=204)
def withdraw(body: WithdrawIn, response: Response, db: Session = Depends(get_db), user_id: int = Depends(require_login)):
    auth.withdraw(db, user_id, body.password)
    auth.clear_cookie(response)  # 탈퇴하면 로그아웃된다
