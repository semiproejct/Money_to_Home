"""회원 API(A-14 ~ A-18)의 요청과 응답 모양. 담당: 김해원

규칙과 문장은 API 명세서 5장을 그대로 따른다.
"""
import re

from pydantic import BaseModel, ValidationInfo, field_validator

MSG_LOGIN_ID = "아이디는 영문 소문자로 시작하는 5자 이상 20자 이하의 영문 소문자와 숫자여야 합니다."  # FR-USER-19
MSG_PASSWORD = "비밀번호는 8자 이상이며 영문과 숫자를 포함해야 합니다."  # FR-USER-03
MSG_PASSWORD_CONFIRM = "비밀번호가 서로 다릅니다."  # FR-USER-04

LOGIN_ID_RULE = re.compile(r"[a-z][a-z0-9]{4,19}")


def check_login_id(value: str) -> str:
    if not LOGIN_ID_RULE.fullmatch(value):
        raise ValueError(MSG_LOGIN_ID)
    return value


def check_password(value: str) -> str:
    if len(value) < 8 or not re.search(r"[A-Za-z]", value) or not re.search(r"[0-9]", value):
        raise ValueError(MSG_PASSWORD)
    return value


class LoginIdIn(BaseModel):
    """A-14 요청"""

    login_id: str

    _check_login_id = field_validator("login_id")(check_login_id)


class AvailableOut(BaseModel):
    """A-14 응답"""

    available: bool


class SignupIn(BaseModel):
    """A-15 요청"""

    login_id: str
    password: str
    password_confirm: str
    agreed: bool | None = None  # 가입 동의 (3차, FR-USER-05). true면 동의한 시각을 남긴다

    _check_login_id = field_validator("login_id")(check_login_id)
    _check_password = field_validator("password")(check_password)

    @field_validator("password_confirm")
    @classmethod
    def same_as_password(cls, value: str, info: ValidationInfo) -> str:
        # password가 규칙에 걸렸으면 info.data에 없다. 그때는 password의 오류가 먼저 나간다
        if "password" in info.data and value != info.data["password"]:
            raise ValueError(MSG_PASSWORD_CONFIRM)
        return value


class LoginIn(BaseModel):
    """A-16 요청. 규칙은 보지 않는다. 틀리면 모두 같은 401이다 (FR-USER-07)"""

    login_id: str
    password: str


class PasswordIn(BaseModel):
    """A-19 요청 (3차, FR-USER-13). 새 비밀번호의 규칙은 회원가입과 같다"""

    current_password: str
    new_password: str
    new_password_confirm: str

    _check_password = field_validator("new_password")(check_password)

    @field_validator("new_password_confirm")
    @classmethod
    def same_as_new_password(cls, value: str, info: ValidationInfo) -> str:
        if "new_password" in info.data and value != info.data["new_password"]:
            raise ValueError(MSG_PASSWORD_CONFIRM)
        return value


class WithdrawIn(BaseModel):
    """A-20 요청 (3차, FR-USER-11). 비밀번호를 한 번 더 받는다 (와이어프레임 C5)"""

    password: str


class LoginOut(BaseModel):
    """A-15, A-16, A-18 응답"""

    login_id: str
