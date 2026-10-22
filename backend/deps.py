"""지금 사용자가 누구인지 알아내는 함수.

누구인지는 로그인 쿠키의 회원 번호로만 정한다. 요청에 든 번호를 믿지 않는다 (FR-USER-15).

- login_user_id      : 로그인했으면 회원 번호, 아니면 None
- require_login      : 로그인했으면 회원 번호, 아니면 401. 로그인이 꼭 필요한 API가 쓴다 (NFR-10)
- get_current_user_id: 재무정보 API(A-08 ~ A-11)가 쓴다. require_login과 같다.
    로그인하지 않은 사용자의 값은 브라우저에만 두고 서버에 저장하지 않는다 (FR-PROFILE-04, API 명세서 2.3).
    입력 화면은 로그인했을 때만 저장 API를 부른다 (frontend/js/account.js의 account.save).
"""
from fastapi import Request

from backend.errors import ApiError
from backend.services import auth


def login_user_id(request: Request) -> int | None:
    return auth.read_token(request.cookies.get(auth.COOKIE_NAME))


def require_login(request: Request) -> int:
    user_id = login_user_id(request)
    if user_id is None:
        raise ApiError(401, auth.MSG_LOGIN_REQUIRED)
    return user_id


def get_current_user_id(request: Request) -> int:
    return require_login(request)
