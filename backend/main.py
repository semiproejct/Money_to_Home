"""머니 to 홈 서버.

실행 (프로젝트 폴더에서):
    uvicorn backend.main:app --reload --port 8000

- 화면:     http://localhost:8000
- API 문서: http://localhost:8000/docs
- 상태 확인: http://localhost:8000/api/health
"""
from fastapi import FastAPI, Request
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.staticfiles import StaticFiles

from backend.config import FRONTEND_DIR
from backend.errors import register_error_handlers
from backend.routers import apartment_detail, apartments, auth, bus_stops, loans, plans, profile, saved_results, scenario, system
from backend.services import auth as auth_service

app = FastAPI(title="머니 to 홈", version="0.1.0")

register_error_handlers(app)

# 1KB가 넘는 응답은 압축해서 보낸다 (2026-10-20). 광주 전체 아파트(A-05, 약 520KB)와 법정동 경계(약 550KB)가 크게 줄어든다.
# 브라우저가 Accept-Encoding: gzip을 보낼 때만 압축하므로 다른 동작은 그대로다
app.add_middleware(GZipMiddleware, minimum_size=1024, compresslevel=5)  # 9(기본)보다 조금 덜 줄지만 압축이 몇 배 빠르다


@app.middleware("http")
async def keep_login(request: Request, call_next):
    """로그인한 사용자의 요청이면 로그인 쿠키를 새로 내준다. 그래서 "마지막 요청 뒤 30분"이 된다 (FR-USER-08).

    로그인이나 로그아웃처럼 응답이 이미 쿠키를 정했으면 건드리지 않는다.
    """
    response = await call_next(request)
    user_id = auth_service.read_token(request.cookies.get(auth_service.COOKIE_NAME))
    decided = any(
        value.startswith(f"{auth_service.COOKIE_NAME}=") for value in response.headers.getlist("set-cookie")
    )
    if user_id is not None and not decided:
        auth_service.set_cookie(response, user_id)
    return response


# API. 새 router 파일을 만들면 여기에 한 줄을 더한다.
app.include_router(system.router)
app.include_router(loans.router)
app.include_router(plans.router)
app.include_router(profile.router)
app.include_router(profile.profiles_router)  # 재무정보 3개 A-29 ~ A-34 (2026-10-21)
app.include_router(apartments.router)
app.include_router(apartment_detail.router)
app.include_router(bus_stops.router)
app.include_router(scenario.router)
app.include_router(auth.router)
app.include_router(saved_results.router)

class FrontendFiles(StaticFiles):
    """화면 파일. 브라우저가 쓸 때마다 바뀌었는지 서버에 묻게 한다. 안 바뀌었으면 304라 다시 받지 않는다.

    ?v= 버전이 붙은 CSS · JS는 (2026-10-20) 하루 동안 묻지 않고 브라우저에 둔 것을 쓴다. 파일을 고치면 ?v= 숫자를 올리는 것이
    팀 규칙이라(CLAUDE.md) 숫자가 바뀌면 새 주소가 되어 바로 새로 받는다. 화면(HTML)과 버전이 없는 파일은 지금처럼 매번 묻는다.
    """

    async def get_response(self, path, scope):
        response = await super().get_response(path, scope)
        versioned = b"v=" in scope.get("query_string", b"") and path.endswith((".css", ".js"))
        if response.status_code in (200, 304):
            response.headers["Cache-Control"] = "public, max-age=86400" if versioned else "no-cache"
        return response

app.mount("/", FrontendFiles(directory=FRONTEND_DIR, html=True), name="frontend")
