"""DB 연결. MariaDB에 SQLAlchemy로 접속한다 (드라이버는 PyMySQL).

router에서는 아래처럼 세션을 받아 services의 함수에 넘긴다.

    from sqlalchemy.orm import Session
    from backend.database import get_db

    @router.get("/api/...")
    def 함수(db: Session = Depends(get_db)):
        return some_service.find_all(db)

규칙
- 표는 db/schema.sql로 만든다. Base.metadata.create_all()로 만들지 않는다.
  models의 클래스는 이미 있는 표에 이름을 맞춰 적은 것이다.
- SQL 문장에 값을 직접 붙이지 않는다. select(...).where(...)처럼 쓰면 값이 매개변수로 넘어간다 (NFR-09).
- 요청이 오류 없이 끝나면 저장(commit)하고, 오류가 나면 되돌린다(rollback). services에서 commit하지 않는다.
"""
import ssl

import pymysql
from pymysql.cursors import DictCursor
from sqlalchemy import URL, create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from backend.config import settings

DATABASE_URL = URL.create(
    "mysql+pymysql",
    username=settings.db_user,
    password=settings.db_password,
    host=settings.db_host,
    port=settings.db_port,
    database=settings.db_name,
    query={"charset": "utf8mb4"},
)



def ssl_options() -> dict | None:
    """DB_SSL=true면 PyMySQL에 넘길 SSL 설정. 아니면 None (로컬 MariaDB).

    DB_SSL_CA에 CA 인증서 파일이 있으면 서버 인증서를 확인한다. 없으면 암호화만 하고 확인은 하지 않는다.
    """
    if not settings.db_ssl:
        return None
    if settings.db_ssl_ca:
        return {"ca": settings.db_ssl_ca}
    return {"check_hostname": False, "verify_mode": ssl.CERT_NONE}


# 접속은 처음 쓸 때 한다. 이 파일을 불러오는 것만으로는 DB에 붙지 않는다.
_ssl = ssl_options()
engine = create_engine(DATABASE_URL, pool_pre_ping=True, connect_args={"ssl": _ssl} if _ssl else {})
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


class Base(DeclarativeBase):
    """모든 models 클래스의 부모."""


def get_db():
    """요청 하나에 세션 하나를 내주고, 끝나면 닫는다."""
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def connect():
    """PyMySQL 연결 하나를 연다. data/ 폴더의 수집·적재 스크립트가 쓴다.

    서버 코드(routers, services)는 이것을 쓰지 않고 get_db의 세션을 쓴다.
    조회 결과는 칸 이름을 키로 하는 dict로 온다.
    """
    return pymysql.connect(
        host=settings.db_host,
        port=settings.db_port,
        user=settings.db_user,
        password=settings.db_password,
        database=settings.db_name,
        charset="utf8mb4",
        cursorclass=DictCursor,
        ssl=ssl_options(),
        autocommit=False,
    )
