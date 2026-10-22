"""오류 응답을 한 모양으로 바꾼다 (NFR-19, API 명세서 2.5).

    { "detail": "사용자에게 보여 줄 문장", "field": "문제가 된 값의 이름" }

- field는 입력 검증 오류일 때만 넣는다.
- 서버 오류의 문장은 고정한다. 내부 정보는 서버 기록에만 남긴다 (NFR-11).
"""
import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

logger = logging.getLogger("money_to_home")

MSG_SERVER_ERROR = "잠시 후 다시 시도해 주세요."
MSG_NOT_FOUND = "찾는 것이 없습니다."
MSG_INVALID = "입력한 값을 다시 확인해 주세요."
MSG_MISSING = "필요한 값이 빠졌습니다."
MSG_NOT_NUMBER = "숫자만 입력할 수 있습니다."
MSG_NOT_INTEGER = "소수는 입력할 수 없습니다. 만 원 단위의 정수로 입력해 주세요."


class ApiError(Exception):
    """router와 models에서 일부러 내는 오류. 문장을 그대로 사용자에게 보여 준다."""

    def __init__(self, status_code: int, detail: str, field: str | None = None):
        self.status_code = status_code
        self.detail = detail
        self.field = field


def _body(detail: str, field: str | None = None) -> dict:
    body = {"detail": detail}
    if field:
        body["field"] = field
    return body


def _validation_message(error: dict) -> str:
    kind = error.get("type", "")
    if kind == "missing":
        return MSG_MISSING
    if kind == "value_error":
        # schemas의 검사 함수가 ValueError("문장")으로 낸 것
        return str(error.get("ctx", {}).get("error", MSG_INVALID))
    if kind.startswith("int") or kind.startswith("float"):
        if isinstance(error.get("input"), float):
            return MSG_NOT_INTEGER
        return MSG_NOT_NUMBER
    return MSG_INVALID


def _validation_field(error: dict) -> str | None:
    names = [part for part in error.get("loc", ()) if isinstance(part, str)]
    names = [name for name in names if name not in ("body", "query", "path")]
    return names[-1] if names else None


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(ApiError)
    async def handle_api_error(request: Request, exc: ApiError):
        return JSONResponse(status_code=exc.status_code, content=_body(exc.detail, exc.field))

    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(request: Request, exc: RequestValidationError):
        error = exc.errors()[0]
        return JSONResponse(
            status_code=422,
            content=_body(_validation_message(error), _validation_field(error)),
        )

    @app.exception_handler(StarletteHTTPException)
    async def handle_http_error(request: Request, exc: StarletteHTTPException):
        if exc.status_code == 404:
            detail = MSG_NOT_FOUND
        elif exc.status_code >= 500:
            detail = MSG_SERVER_ERROR
        else:
            detail = str(exc.detail)
        return JSONResponse(status_code=exc.status_code, content=_body(detail))

    @app.exception_handler(Exception)
    async def handle_unexpected_error(request: Request, exc: Exception):
        logger.exception("처리하지 못한 오류: %s %s", request.method, request.url.path)
        return JSONResponse(status_code=500, content=_body(MSG_SERVER_ERROR))
