"""머니 to 홈 서버.

실행 (프로젝트 폴더에서):
    uvicorn backend.main:app --reload --port 8000

- 화면:     http://localhost:8000
- API 문서: http://localhost:8000/docs
- 상태 확인: http://localhost:8000/api/health
"""
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles

from backend.config import FRONTEND_DIR
from backend.errors import register_error_handlers
from backend.routers import apartment_detail, apartments, auth, loans, plans, profile, saved_results, scenario, system
from backend.services import auth as auth_service

app = FastAPI(title="머니 to 홈", version="0.1.0")

register_error_handlers(app)


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
app.include_router(apartments.router)
app.include_router(apartment_detail.router)
app.include_router(scenario.router)
app.include_router(auth.router)
app.include_router(saved_results.router)

class FrontendFiles(StaticFiles):
    """화면 파일. 브라우저가 쓸 때마다 바뀌었는지 서버에 묻게 한다. 안 바뀌었으면 304라 다시 받지 않는다."""
    def file_response(self, *args, **kwargs):
        response = super().file_response(*args, **kwargs)
        response.headers["Cache-Control"] = "no-cache"
        return response

app.mount("/", FrontendFiles(directory=FRONTEND_DIR, html=True), name="frontend")
