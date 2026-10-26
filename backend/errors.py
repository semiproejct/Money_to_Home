"""오류 응답을 한 모양으로 바꾼다 (NFR-19, API 명세서 2.5).

    { "detail": "사용자에게 보여 줄 문장", "field": "문제가 된 값의 이름" }

- field는 입력 검증 오류일 때만 넣는다.
- 서버 오류의 문장은 고정한다. 내부 정보는 서버 기록에만 남긴다 (NFR-11).
- 주소창으로 연 화면(/api가 아닌 GET)에서 난 오류는 JSON 대신 오류 화면(templates/error.html)으로 보여 준다 (2026-10-26).
"""
import html
import logging
import os
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import HTMLResponse, JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

logger = logging.getLogger("money_to_home")

MSG_SERVER_ERROR = "잠시 후 다시 시도해 주세요."
MSG_NOT_FOUND = "찾는 것이 없습니다."
MSG_INVALID = "입력한 값을 다시 확인해 주세요."
MSG_MISSING = "필요한 값이 빠졌습니다."
MSG_NOT_NUMBER = "숫자만 입력할 수 있습니다."
MSG_NOT_INTEGER = "소수는 입력할 수 없습니다. 만 원 단위의 정수로 입력해 주세요."


ERROR_PAGE = (Path(__file__).parent / "templates" / "error.html").read_text(encoding="utf-8")

# 상태 코드별 오류 화면의 제목 · 설명 · 버튼. 없는 코드는 400번대면 400, 500번대면 500 것을 쓴다
PAGE_TEXT = {
    400: ("잘못된 요청입니다", "요청을 이해하지 못했습니다. 주소를 다시 확인해 주세요.", "/", "처음으로"),
    401: ("로그인이 필요합니다", "로그인한 뒤 다시 시도해 주세요.", "/login.html", "로그인"),
    403: ("볼 수 없는 화면입니다", "이 화면을 볼 권한이 없습니다.", "/", "처음으로"),
    404: ("화면을 찾을 수 없습니다", "주소가 바뀌었거나 없는 화면입니다. 주소를 다시 확인해 주세요.", "/", "처음으로"),
    405: ("허용되지 않는 요청입니다", "이 주소로는 할 수 없는 요청입니다.", "/", "처음으로"),
    408: ("요청 시간이 지났습니다", "응답을 기다리다 시간이 지났습니다. 다시 시도해 주세요.", "/", "처음으로"),
    429: ("요청이 너무 많습니다", "잠시 기다린 뒤 다시 시도해 주세요.", "/", "처음으로"),
    500: ("서버에 문제가 생겼습니다", "잠시 후 다시 시도해 주세요. 문제가 계속되면 팀에 알려 주세요.", "/", "처음으로"),
    502: ("서버가 응답하지 않습니다", "서버를 다시 켜는 중일 수 있습니다. 잠시 후 다시 시도해 주세요.", "/", "처음으로"),
    503: ("잠시 쓸 수 없습니다", "서버를 점검하고 있습니다. 잠시 후 다시 시도해 주세요.", "/", "처음으로"),
    504: ("응답이 늦어지고 있습니다", "서버의 응답이 늦습니다. 잠시 후 다시 시도해 주세요.", "/", "처음으로"),
}

# 오류 화면 미리보기 /error-preview/404 (로컬에서만). Render는 RENDER 환경 변수를 넣으므로 배포 서버에서는 꺼진다
PREVIEW_ON = not os.environ.get("RENDER")


def _wants_page(request: Request) -> bool:
    """브라우저 주소창으로 연 화면이면 True. API와 fetch 요청은 지금처럼 JSON으로 답한다."""
    return (
        request.method in ("GET", "HEAD")
        and not request.url.path.startswith("/api")
        and "text/html" in request.headers.get("accept", "")
    )


def _error_page(status_code: int) -> HTMLResponse:
    fallback = 500 if status_code >= 500 else 400
    title, message, href, label = PAGE_TEXT.get(status_code, PAGE_TEXT[fallback])
    page = ERROR_PAGE
    for key, value in {"code": str(status_code), "title": title, "message": message, "action_href": href, "action_label": label}.items():
        page = page.replace("{{" + key + "}}", html.escape(value))
    return HTMLResponse(page, status_code=status_code, headers={"Cache-Control": "no-cache"})


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
    if PREVIEW_ON:
        @app.get("/error-preview/{code}", include_in_schema=False)
        async def preview_error_page(code: int):
            return _error_page(code if code in PAGE_TEXT else 404)

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
        if _wants_page(request):
            return _error_page(exc.status_code)
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
        if _wants_page(request):
            return _error_page(500)
        return JSONResponse(status_code=500, content=_body(MSG_SERVER_ERROR))
