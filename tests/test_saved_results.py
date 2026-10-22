"""결과 저장 (A-21 ~ A-23). 담당: 박채은

- 로그인해야 쓴다. 로그인하지 않았으면 401
- 저장할 때 서버가 다시 계산한다. 화면이 숫자를 보내도 쓰지 않는다
- 남의 것은 404
상품은 conftest.py의 products(첫째 3억 6,000만·70%·연 4.0%·상한 6억)를 쓴다. 기대값은 손으로 계산한 값이다.
"""
from datetime import date

import pytest
from sqlalchemy import select

from backend import models
from backend.services import auth


def _priced(id, name, bands):
    """bands: [(면적대, 평균가, 공급면적), ...]"""
    apt = models.Apartment(id=id, name=name, gu="서구", dong="치평동", jibun=str(id))
    for band, price, supply in bands:
        apt.prices.append(models.ApartmentPrice(
            area_band=band, exclusive_area=f"{band}.9400", supply_area=supply, avg_price=price,
            min_price=price, max_price=price, trade_count=5,
            period_start=date(2025, 10, 1), period_end=date(2026, 9, 30),
        ))
    return apt



@pytest.fixture
def client(anon_client):
    """이 파일의 테스트는 로그인하지 않은 브라우저에서 시작한다 (가입과 로그인을 직접 한다)."""
    return anon_client

@pytest.fixture
def apartments(db, products):
    db.add_all([
        _priced(21, "가아파트", [(84, 300_000_000, "111.00"), (114, 450_000_000, "141.00")]),
        _priced(22, "나아파트", [(59, 150_000_000, None)]),  # 공급면적 없음
    ])
    db.add(models.User(id=2, login_id="otheruser", password_hash="!"))
    db.commit()


EXAMPLE = {
    "current_assets": 50_000_000, "monthly_saving": 1_000_000, "target_years": 5,
    "loan_choice": "product", "loan_product_id": 1, "repayment_years": 30,
}
NO_LOAN = {"loan_choice": "none", "loan_product_id": None, "repayment_years": None}


def _login(client, user_id=1):
    """그 회원으로 로그인한 쿠키를 둔다.

    서버가 응답마다 로그인 쿠키를 새로 내주므로(main.py) 앞 회원의 쿠키가 남아 있다.
    다른 회원으로 바꿀 때 쿠키가 두 개가 되지 않게 먼저 비운다.
    """
    client.cookies.clear()
    client.cookies.set(auth.COOKIE_NAME, auth.make_token(user_id))


def _save(client, apartment_id=21, area_band=84, **changes):
    body = {"conditions": {**EXAMPLE, **changes}, "apartment_id": apartment_id, "area_band": area_band}
    return client.post("/api/saved-results", json=body)


# ---------------------------------------------------------------------------
# 로그인
# ---------------------------------------------------------------------------


def test_login_required(client, apartments):
    assert _save(client).status_code == 401
    assert client.get("/api/saved-results").status_code == 401
    assert client.get("/api/saved-results/1").status_code == 401
    assert _save(client).json() == {"detail": "로그인이 필요합니다."}


# ---------------------------------------------------------------------------
# 저장 (A-21)
# ---------------------------------------------------------------------------


def test_save_matches_scenario(client, apartments):
    """저장한 값은 시나리오(A-07)와 같다. 3억 원 아파트, 보유 5,000만, 월 100만, 5년, 첫째 상품 30년"""
    _login(client)
    response = _save(client)
    assert response.status_code == 201
    body = response.json()
    assert body["id"] > 0
    assert body["created_at"]
    assert body["apartment"] == {
        "id": 21, "name": "가아파트", "gu": "서구", "dong": "치평동",
        "area_band": 84, "exclusive_area": 84.94, "supply_area": 111.0,
    }
    assert body["loan"] == {
        "choice": "product", "product_id": 1, "product_name": "[예시] 첫째 상품", "repayment_years": 30,
        "amount": 210_000_000, "monthly_payment": 1_002_572,
    }
    # 누적 6,000만, 자기자금 1억 1,000만, 부족 3억 − 1억 1,000만 − 2억 1,000만 = −2,000만 (여유)
    assert {k: body[k] for k in (
        "price", "current_assets", "monthly_saving", "target_years", "accumulated_saving", "own_funds",
        "category", "shortage", "required_monthly_saving", "allowed_growth_rate",
    )} == {
        "price": 300_000_000, "current_assets": 50_000_000, "monthly_saving": 1_000_000, "target_years": 5,
        "accumulated_saving": 60_000_000, "own_funds": 110_000_000,
        "category": "within", "shortage": -20_000_000, "required_monthly_saving": None, "allowed_growth_rate": 4.0,
    }

    scenario = client.post("/api/apartments/21/scenario", json={"conditions": EXAMPLE, "area_band": 84}).json()
    for key in ("price", "accumulated_saving", "own_funds", "category", "shortage",
                "required_monthly_saving", "allowed_growth_rate"):
        assert body[key] == scenario[key]


def test_save_lack(client, apartments):
    """4억 5,000만 원: 대출 3억 1,500만, 부족 2,500만, 필요 월 저축액 (4억 5,000만 − 3억 1,500만 − 5,000만) ÷ 60 → 1,416,667"""
    _login(client)
    body = _save(client, area_band=114).json()
    assert body["category"] == "lack"
    assert body["shortage"] == 25_000_000
    assert body["required_monthly_saving"] == 1_416_667
    assert body["allowed_growth_rate"] is None


def test_save_without_loan(client, apartments):
    """대출 없이: 1억 5,000만 원 아파트, 자기자금 1억 1,000만 → 부족 4,000만, (1억 5,000만 − 5,000만) ÷ 60 → 1,666,667"""
    _login(client)
    body = _save(client, apartment_id=22, area_band=59, **NO_LOAN).json()
    assert body["loan"] == {"choice": "none"}
    assert body["apartment"]["supply_area"] is None
    assert body["shortage"] == 40_000_000
    assert body["required_monthly_saving"] == 1_666_667


def test_save_now(client, apartments):
    """목표 기간 "지금": 누적 0원, 자기자금 = 보유자산, 필요 월 저축액·허용 상승률 없음"""
    _login(client)
    body = _save(client, target_years=0).json()
    assert body["accumulated_saving"] == 0
    assert body["own_funds"] == 50_000_000
    assert body["category"] == "lack"  # 5,000만 + 2억 1,000만 < 3억
    assert body["required_monthly_saving"] is None
    assert body["allowed_growth_rate"] is None


def test_save_ignores_numbers_from_screen(client, apartments):
    """화면이 계산 결과를 함께 보내도 쓰지 않고 서버가 다시 계산한다 (NFR-13)"""
    _login(client)
    body = {"conditions": EXAMPLE, "apartment_id": 21, "area_band": 84, "shortage": -999_999_999, "category": "now"}
    saved = client.post("/api/saved-results", json=body).json()
    assert saved["shortage"] == -20_000_000
    assert saved["category"] == "within"


def test_save_unknown_apartment_or_area(client, apartments):
    _login(client)
    assert _save(client, apartment_id=999).status_code == 404
    assert _save(client, area_band=200).status_code == 404


def test_save_bad_conditions(client, apartments):
    """조건 검사는 시나리오와 같다"""
    _login(client)
    assert _save(client, monthly_saving=-1).status_code == 422
    assert _save(client, target_years=4).status_code == 422
    assert _save(client, loan_product_id=None).status_code == 422


# ---------------------------------------------------------------------------
# 목록과 하나 (A-22, A-23)
# ---------------------------------------------------------------------------


def test_list_newest_first_and_only_mine(client, apartments):
    _login(client)
    first = _save(client).json()
    second = _save(client, apartment_id=22, area_band=59, **NO_LOAN).json()
    _login(client, user_id=2)
    _save(client, area_band=114)  # 다른 회원의 것

    _login(client)
    results = client.get("/api/saved-results").json()["results"]
    assert [item["id"] for item in results] == [second["id"], first["id"]]


def test_list_empty(client, apartments):
    _login(client)
    assert client.get("/api/saved-results").json() == {"results": []}


def test_get_one(client, apartments):
    _login(client)
    saved = _save(client).json()
    response = client.get(f"/api/saved-results/{saved['id']}")
    assert response.status_code == 200
    assert response.json() == saved


def test_get_others_is_404(client, apartments):
    _login(client, user_id=2)
    others = _save(client).json()
    _login(client)
    response = client.get(f"/api/saved-results/{others['id']}")
    assert response.status_code == 404
    assert response.json() == {"detail": "저장한 결과를 찾을 수 없습니다."}
    assert client.get("/api/saved-results/999").status_code == 404


def test_saved_values_stay_when_price_changes(client, db, apartments):
    """저장한 뒤 평균가가 바뀌어도 저장한 값은 그대로다 (다시 계산하지 않는다)"""
    _login(client)
    saved = _save(client).json()
    for row in db.scalars(select(models.ApartmentPrice).where(
        models.ApartmentPrice.apartment_id == 21, models.ApartmentPrice.area_band == 84,
    )):
        row.avg_price = 999_000_000
    db.commit()
    again = client.get(f"/api/saved-results/{saved['id']}").json()
    assert again["price"] == 300_000_000
    assert again["shortage"] == -20_000_000
