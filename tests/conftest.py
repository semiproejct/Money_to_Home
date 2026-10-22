"""테스트 공통 준비.

여기의 테스트는 MariaDB 없이 돈다. 메모리 안에 임시 DB(SQLite)를 만들어 models의 표를 넣고,
서버가 그 DB를 쓰게 바꿔 끼운다. 테스트 하나가 끝나면 통째로 사라진다.
실행 (프로젝트 폴더에서): pytest
"""
from datetime import date

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend import models
from backend.database import Base, get_db
from backend.main import app
from backend.services import response_cache


@pytest.fixture(autouse=True)
def no_response_cache():
    """테스트마다 DB가 새로 만들어지므로 응답 기억(response_cache)은 끈다. 켠 채로 보는 테스트는 따로 켠다"""
    response_cache.enabled = False
    response_cache.clear()
    yield
    response_cache.enabled = False
    response_cache.clear()


@pytest.fixture
def db():
    """빈 임시 DB. 테스트 사용자(번호 1)만 들어 있다."""
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)()
    session.add(models.User(id=1, login_id="testuser", password_hash="!"))
    session.commit()
    yield session
    session.close()
    engine.dispose()


@pytest.fixture
def products(db):
    """대출 상품 두 줄. db/seed_loan_products.sql의 예시와 같은 값이다."""
    rows = [
        models.LoanProduct(
            id=1, name="[예시] 첫째 상품", institution="한국주택금융공사", max_limit=360_000_000,
            ltv_ratio="0.700", annual_rate_pct="4.000", repayment_years_options="10,15,20,30",
            max_house_price=600_000_000, eligibility_summary="요약", eligibility_text="문구",
            base_date=date(2026, 10, 1), source_url="https://www.hf.go.kr",
        ),
        models.LoanProduct(
            id=2, name="[예시] 둘째 상품", institution="카카오뱅크", max_limit=500_000_000,
            ltv_ratio="0.800", annual_rate_pct="4.500", repayment_years_options="10,20,30,40",
            max_house_price=None, eligibility_summary="요약", eligibility_text="문구",
            base_date=date(2026, 10, 1), source_url="https://www.kakaobank.com",
        ),
    ]
    db.add_all(rows)
    db.commit()
    return rows


@pytest.fixture
def anon_client(db):
    """로그인하지 않은 브라우저"""
    def use_test_db():
        try:
            yield db
            db.commit()
        except Exception:
            db.rollback()
            raise

    app.dependency_overrides[get_db] = use_test_db
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture
def client(anon_client):
    """테스트 사용자(번호 1)로 로그인한 브라우저. 재무정보 API(A-08 ~ A-11)는 로그인해야 쓴다."""
    from backend.services import auth

    anon_client.cookies.set(auth.COOKIE_NAME, auth.make_token(1))
    return anon_client
