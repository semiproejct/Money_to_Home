"""설정. .env의 값을 읽는다.

키와 비밀번호는 이 파일에 적지 않는다. 프로젝트 폴더의 .env에만 둔다.
다른 파일에서는 `from backend.config import settings`로 꺼내 쓴다.
"""
import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

# 프로젝트 폴더 (backend의 위)
BASE_DIR = Path(__file__).resolve().parent.parent
FRONTEND_DIR = BASE_DIR / "frontend"

load_dotenv(BASE_DIR / ".env")


@dataclass(frozen=True)
class Settings:
    db_host: str
    db_port: int
    db_name: str
    db_user: str
    db_password: str
    kakao_js_key: str
    session_secret_key: str
    # 클라우드 DB(Aiven 등)는 암호화 접속(SSL)을 요구한다. 로컬 MariaDB는 쓰지 않는다 (2026-10-22 배포)
    db_ssl: bool
    db_ssl_ca: str  # DB 회사가 주는 CA 인증서 파일 경로. 비우면 인증서를 확인하지 않고 암호화만 한다


settings = Settings(
    db_host=os.getenv("DB_HOST", "localhost"),
    db_port=int(os.getenv("DB_PORT", "3306")),
    db_name=os.getenv("DB_NAME", "money_to_home"),
    db_user=os.getenv("DB_USER", ""),
    db_password=os.getenv("DB_PASSWORD", ""),
    kakao_js_key=os.getenv("KAKAO_JS_KEY", ""),
    session_secret_key=os.getenv("SESSION_SECRET_KEY", ""),
    db_ssl=os.getenv("DB_SSL", "").strip().lower() in ("1", "true", "yes"),
    db_ssl_ca=os.getenv("DB_SSL_CA", "").strip(),
)
