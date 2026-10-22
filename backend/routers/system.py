"""서버 상태 확인과 화면 설정.

- GET /api/health : 서버와 DB가 살아 있는지 본다. 개발 환경을 확인할 때 쓴다.
- GET /api/config : A-26. 지도를 그릴 카카오 JavaScript 키를 화면에 준다.
"""
import logging

from fastapi import APIRouter
from sqlalchemy import text

from backend.config import settings
from backend.database import engine

router = APIRouter(prefix="/api", tags=["공통"])
logger = logging.getLogger("money_to_home")


@router.get("/health")
def health():
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        db = "ok"
    except Exception:
        # 접속 정보가 응답에 섞이지 않게 자세한 내용은 서버 기록에만 남긴다.
        logger.exception("DB에 연결하지 못했습니다.")
        db = "error"
    return {"status": "ok", "db": db}


@router.get("/config")
def config():
    # JavaScript 키만 준다. REST API 키와 공공데이터 인증키는 화면에 주지 않는다 (NFR-04).
    return {"kakao_js_key": settings.kakao_js_key}
