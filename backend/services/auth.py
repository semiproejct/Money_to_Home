"""회원: 비밀번호 해시, 로그인 쿠키, 회원 찾기와 만들기. 담당: 김해원

routers/auth.py와 deps.py가 부른다.

비밀번호 (FR-USER-14)
  - bcrypt로 해시해 저장한다. 원래 값은 어디에도 남기지 않는다. 기록(log)에도 찍지 않는다.
  - bcrypt는 72바이트까지만 읽는다. 긴 비밀번호도 끝까지 쓰이도록 SHA-256으로 한 번 줄인 뒤 해시한다.

로그인 쿠키 (아키텍처 문서 8.2, FR-USER-08)
  - 서버는 로그인 상태를 저장하지 않는다. 쿠키에 "회원 번호.받은 때.서명"을 담는다.
  - 서명은 .env의 SESSION_SECRET_KEY로 만든다 (HMAC-SHA256). 값을 고치면 서명이 맞지 않아 버린다.
  - 받은 때에서 30분이 지나면 버린다. 요청마다 새로 내주므로 "마지막 요청 뒤 30분"이 된다 (main.py).
"""
import base64
import hashlib
import hmac
import logging
import secrets
import time
from datetime import datetime

import bcrypt
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.config import settings
from backend.errors import ApiError
from backend.models import Profile, SavedResult, User

logger = logging.getLogger("money_to_home")

COOKIE_NAME = "mth_session"
SESSION_SECONDS = 30 * 60  # 마지막 요청 뒤 30분 (FR-USER-08)

MSG_ID_TAKEN = "이미 사용 중인 아이디입니다. 다른 아이디를 입력해 주세요."  # P-08 ③
MSG_LOGIN_FAILED = "아이디 또는 비밀번호가 맞지 않습니다."  # P-07 ②. 어느 쪽이 틀렸는지 구분하지 않는다 (FR-USER-07)
MSG_LOGIN_REQUIRED = "로그인이 필요합니다."
MSG_CURRENT_WRONG = "지금 비밀번호가 맞지 않습니다."  # 와이어프레임 C4 (P-10)
MSG_PASSWORD_WRONG = "비밀번호가 맞지 않습니다."  # 탈퇴할 때. C4의 문장에서 "지금"만 뺐다

# 서명 키. .env에 없으면 서버를 켤 때마다 새로 만든다 (서버를 다시 켜면 모두 로그아웃된다).
_secret = settings.session_secret_key.encode("utf-8")
if not _secret:
    logger.warning("SESSION_SECRET_KEY가 없어 임시 키를 씁니다. 서버를 다시 켜면 로그인이 풀립니다.")
    _secret = secrets.token_bytes(32)


def now() -> int:
    """지금 (초). 테스트에서 시간을 바꿔 끼우려고 함수로 둔다."""
    return int(time.time())


# ------------------------------------------------------------------
# 비밀번호
# ------------------------------------------------------------------
def _digest(password: str) -> bytes:
    return base64.b64encode(hashlib.sha256(password.encode("utf-8")).digest())


def hash_password(password: str) -> str:
    return bcrypt.hashpw(_digest(password), bcrypt.gensalt()).decode("ascii")


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(_digest(password), password_hash.encode("ascii"))
    except ValueError:
        return False  # 해시의 모양이 아니다 (테스트 사용자의 "!" 등)


# 없는 아이디로 로그인할 때도 해시를 한 번 맞춰 본다. 걸리는 시간으로 아이디가 있는지 알 수 없게 한다.
_DUMMY_HASH = hash_password(secrets.token_hex(16))


# ------------------------------------------------------------------
# 로그인 쿠키
# ------------------------------------------------------------------
def _sign(payload: str) -> str:
    return hmac.new(_secret, payload.encode("ascii"), hashlib.sha256).hexdigest()


def make_token(user_id: int) -> str:
    payload = f"{user_id}.{now()}"
    return f"{payload}.{_sign(payload)}"


def read_token(token: str | None) -> int | None:
    """쿠키의 값에서 회원 번호를 꺼낸다. 서명이 틀렸거나 30분이 지났으면 None"""
    if not token or not token.isascii():
        return None
    payload, _, signature = token.rpartition(".")
    if not payload or not hmac.compare_digest(signature, _sign(payload)):
        return None
    user_id, _, issued = payload.partition(".")
    if not (user_id.isdigit() and issued.isdigit()):
        return None
    if not 0 <= now() - int(issued) <= SESSION_SECONDS:
        return None
    return int(user_id)


def set_cookie(response, user_id: int) -> None:
    """로그인 쿠키를 내준다. 스크립트가 읽지 못하고(HttpOnly), 다른 사이트에서 보낸 요청에는 실리지 않는다(SameSite)."""
    response.set_cookie(
        COOKIE_NAME, make_token(user_id), max_age=SESSION_SECONDS, httponly=True, samesite="lax", path="/",
    )


def clear_cookie(response) -> None:
    response.delete_cookie(COOKIE_NAME, path="/", httponly=True, samesite="lax")


# ------------------------------------------------------------------
# 회원
# ------------------------------------------------------------------
def find_by_login_id(db: Session, login_id: str) -> User | None:
    return db.scalars(select(User).where(User.login_id == login_id)).first()


def check_available(db: Session, login_id: str) -> None:
    """이미 있는 아이디면 409 (FR-USER-02)"""
    if find_by_login_id(db, login_id) is not None:
        raise ApiError(409, MSG_ID_TAKEN, "login_id")


def signup(db: Session, login_id: str, password: str, agreed: bool | None = None) -> User:
    """회원을 만든다. 아이디 확인을 통과한 뒤 그사이에 다른 사람이 가입했으면 409.

    가입 동의(agreed)가 true면 동의한 시각을 남긴다 (FR-USER-05).
    """
    check_available(db, login_id)
    user = User(login_id=login_id, password_hash=hash_password(password))
    if agreed:
        user.terms_agreed_at = datetime.now()
    db.add(user)
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        raise ApiError(409, MSG_ID_TAKEN, "login_id") from None
    return user


def login(db: Session, login_id: str, password: str) -> User:
    """아이디와 비밀번호가 맞으면 회원을, 아니면 401"""
    user = find_by_login_id(db, login_id)
    matched = verify_password(password, user.password_hash if user else _DUMMY_HASH)
    if user is None or not matched:
        raise ApiError(401, MSG_LOGIN_FAILED)
    return user


def change_password(db: Session, user_id: int, current: str, new: str) -> None:
    """A-19 비밀번호 변경 (FR-USER-13). 지금 비밀번호가 틀리면 422 (그 입력란에 알린다)"""
    user = db.get(User, user_id)
    if user is None:
        raise ApiError(401, MSG_LOGIN_REQUIRED)
    if not verify_password(current, user.password_hash):
        raise ApiError(422, MSG_CURRENT_WRONG, "current_password")
    user.password_hash = hash_password(new)


def withdraw(db: Session, user_id: int, password: str) -> None:
    """A-20 회원 탈퇴 (FR-USER-11, 12). 재무정보와 저장한 결과를 함께 지운다. 비밀번호가 틀리면 422

    DB의 외래 키도 함께 지우게(ON DELETE CASCADE) 되어 있지만, 여기서도 직접 지워 어느 DB에서든 같게 한다.
    """
    user = db.get(User, user_id)
    if user is None:
        raise ApiError(401, MSG_LOGIN_REQUIRED)
    if not verify_password(password, user.password_hash):
        raise ApiError(422, MSG_PASSWORD_WRONG, "password")
    db.query(SavedResult).filter(SavedResult.user_id == user_id).delete()
    db.query(Profile).filter(Profile.user_id == user_id).delete()
    db.delete(user)
