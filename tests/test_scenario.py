"""시나리오 (A-07). 담당: 박채은

아파트 한 곳과 면적을 골랐을 때의 계산 결과다. 저장하지 않는다.
상품은 conftest.py의 products(첫째 3억 6,000만·70%·연 4.0%·10/15/20/30년·상한 6억,
둘째 5억·80%·연 4.5%·10/20/30/40년·상한 없음)를 쓴다. 기대값은 손으로 계산한 값이다.
"""
from datetime import date

import pytest

from backend import models


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
def apartments(db, products):
    db.add_all([
        _priced(21, "가아파트", [(84, 300_000_000, "111.00"), (114, 450_000_000, "141.00")]),
        _priced(22, "나아파트", [(59, 150_000_000, None)]),  # 공급면적 없음
        _priced(23, "다아파트", [(84, 700_000_000, "111.00")]),  # 첫째 상품의 상한 6억을 넘는다
        _priced(24, "라아파트", []),  # 평균가가 없다
    ])
    db.commit()


EXAMPLE = {
    "current_assets": 50_000_000, "monthly_saving": 1_000_000, "target_years": 5,
    "loan_choice": "product", "loan_product_id": 1, "repayment_years": 30,
}
NO_LOAN = {"loan_choice": "none", "loan_product_id": None, "repayment_years": None}


def _scenario(client, apartment_id=21, area_band=84, **changes):
    body = {"conditions": {**EXAMPLE, **changes}, "area_band": area_band}
    return client.post(f"/api/apartments/{apartment_id}/scenario", json=body)


def test_scenario_matches_spec_example(client, apartments):
    # API 명세서 A-07의 예시: 3억 원 아파트, 보유 5,000만, 월 100만, 5년, 첫째 상품 30년
    # 누적 6,000만, 자기자금 1억 1,000만, 대출 min(3억 6,000만, 3억 × 0.7) = 2억 1,000만
    # 부족자금 3억 − 1억 1,000만 − 2억 1,000만 = −2,000만 (여유), 허용 상승률 (366,666,666 ÷ 3억)^(1/5) − 1 = 4.09% → 4.0
    response = _scenario(client)
    assert response.status_code == 200
    assert response.json() == {
        "apartment": {"id": 21, "name": "가아파트", "area_band": 84, "exclusive_area": 84.94, "supply_area": 111.0},
        "price": 300_000_000,
        "current_assets": 50_000_000,
        "monthly_saving": 1_000_000,
        "target_years": 5,
        "accumulated_saving": 60_000_000,
        "own_funds": 110_000_000,
        "loan": {
            "choice": "product", "product_id": 1, "product_name": "[예시] 첫째 상품", "repayment_years": 30,
            "amount": 210_000_000, "monthly_payment": 1_002_572,
            "max_house_price": 600_000_000, "over_price_cap": False,
        },
        "category": "within",
        "shortage": -20_000_000,
        "required_monthly_saving": None,  # 부족자금이 0 이하
        "allowed_growth_rate": 4.0,
    }


def test_scenario_lack_example(client, apartments):
    # 명세서 A-07의 자금 부족 예: 4억 5,000만 원이면 대출 3억 1,500만, 부족 2,500만,
    # 필요 월 저축액 (4억 5,000만 − 3억 1,500만 − 5,000만) ÷ 60 = 1,416,666.67 → 올림 1,416,667
    body = _scenario(client, area_band=114).json()
    assert body["price"] == 450_000_000
    assert body["loan"]["amount"] == 315_000_000
    assert body["loan"]["monthly_payment"] == 1_503_858
    assert body["category"] == "lack"
    assert body["shortage"] == 25_000_000
    assert body["required_monthly_saving"] == 1_416_667
    assert body["allowed_growth_rate"] is None  # 목표 가능 가격 3억 6,666만 < 평균가라 음수


def test_scenario_now(client, apartments):
    # 1억 5,000만 원: 보유 5,000만 + 대출 1억 500만 ≥ 평균가라 지금 가능. 공급면적이 없으면 null
    body = _scenario(client, apartment_id=22, area_band=59).json()
    assert body["apartment"]["supply_area"] is None
    assert body["category"] == "now"
    assert body["shortage"] == -65_000_000
    assert body["required_monthly_saving"] is None
    assert body["allowed_growth_rate"] == 19.5  # (366,666,666 ÷ 1억 5,000만)^(1/5) − 1 = 19.57% → 버림


def test_scenario_target_years_now(client, apartments):
    # 목표 기간 "지금": 누적 0, 자기자금은 보유자산. 부족자금 3억 − 5,000만 − 2억 1,000만 = 4,000만
    # 필요 월 저축액과 허용 상승률은 표시하지 않는다 (FR-PLAN-09, C-12). "기간 내 가능"은 나오지 않는다
    body = _scenario(client, target_years=0).json()
    assert (body["accumulated_saving"], body["own_funds"]) == (0, 50_000_000)
    assert body["category"] == "lack"
    assert body["shortage"] == 40_000_000
    assert body["required_monthly_saving"] is None
    assert body["allowed_growth_rate"] is None


def test_scenario_without_loan(client, apartments):
    # 대출 없이 계산: loan은 choice만 온다 (FR-RESULT-05). 대출 0원으로 계산한다 (C-13)
    # 부족자금 3억 − 1억 1,000만 = 1억 9,000만, 필요 월 저축액 (3억 − 5,000만) ÷ 60 = 4,166,666.67 → 4,166,667
    body = _scenario(client, **NO_LOAN).json()
    assert body["loan"] == {"choice": "none"}
    assert body["category"] == "lack"
    assert body["shortage"] == 190_000_000
    assert body["required_monthly_saving"] == 4_166_667
    assert body["allowed_growth_rate"] is None  # 목표 가능 가격이 자기자금 1억 1,000만이라 평균가보다 작다


def test_scenario_over_price_cap_is_shown_not_excluded(client, apartments):
    # 7억 > 첫째 상품 상한 6억: 표시만 하고 계산은 그대로 한다 (FR-LOAN-14). 대출은 한도 3억 6,000만에서 멈춘다
    # 필요 월 저축액 (7억 − 3억 6,000만 − 5,000만) ÷ 60 = 4,833,333.33 → 4,833,334
    body = _scenario(client, apartment_id=23).json()
    assert body["loan"]["amount"] == 360_000_000
    assert body["loan"]["monthly_payment"] == 1_718_695
    assert body["loan"]["over_price_cap"] is True
    assert body["shortage"] == 230_000_000
    assert body["required_monthly_saving"] == 4_833_334


def test_scenario_second_product_has_no_cap(client, apartments):
    # 둘째 상품: min(5억, 7억 × 0.8) = 5억, 연 4.5%, 360개월. 상한이 없으면 null이고 넘지 않는다
    body = _scenario(client, apartment_id=23, loan_product_id=2, repayment_years=30).json()
    assert body["loan"]["product_name"] == "[예시] 둘째 상품"
    assert body["loan"]["amount"] == 500_000_000
    assert body["loan"]["monthly_payment"] == 2_533_427
    assert body["loan"]["max_house_price"] is None
    assert body["loan"]["over_price_cap"] is False


def test_scenario_zero_assets_and_saving(client, apartments):
    # 보유 0원, 월 0원: 자기자금 0. 부족자금 3억 − 2억 1,000만 = 9,000만, 필요 월 저축액 9,000만 ÷ 60 = 1,500,000
    body = _scenario(client, current_assets=0, monthly_saving=0).json()
    assert body["own_funds"] == 0
    assert body["category"] == "lack"
    assert body["shortage"] == 90_000_000
    assert body["required_monthly_saving"] == 1_500_000
    assert body["allowed_growth_rate"] is None  # 목표 가능 가격 0원


def test_scenario_largest_values(client, apartments):
    # 보유 100억, 월 10억, 10년: 누적 1,200억, 자기자금 1,300억. 여유 1,299억 1,000만
    # 허용 상승률 (1,303억 6,000만 ÷ 3억)^(1/10) − 1 = 83.57% → 83.5
    body = _scenario(client, current_assets=10_000_000_000, monthly_saving=1_000_000_000, target_years=10).json()
    assert body["own_funds"] == 130_000_000_000
    assert body["category"] == "now"
    assert body["shortage"] == -129_910_000_000
    assert body["required_monthly_saving"] is None
    assert body["allowed_growth_rate"] == 83.5


@pytest.mark.parametrize("apartment_id, area_band", [
    (999, 84),  # 없는 아파트
    (21, 59),   # 그 아파트에 없는 면적
    (24, 84),   # 평균가가 없는 아파트
])
def test_scenario_not_found(client, apartments, apartment_id, area_band):
    response = _scenario(client, apartment_id=apartment_id, area_band=area_band)
    assert response.status_code == 404
    assert response.json() == {"detail": "아파트를 찾을 수 없습니다."}


@pytest.mark.parametrize("changes, field, detail", [
    ({"loan_product_id": 999}, "loan_product_id", "대출 상품과 상환 기간을 골라 주세요."),
    ({"repayment_years": 25}, "repayment_years", "상환 기간을 다시 골라 주세요."),
    ({"loan_choice": "none"}, "loan_product_id", "대출 상품과 상환 기간을 골라 주세요."),
    ({"repayment_years": None}, "loan_product_id", "대출 상품과 상환 기간을 골라 주세요."),
    ({"loan_choice": "maybe"}, "loan_choice", "대출 상품과 상환 기간을 골라 주세요."),
    ({"target_years": 7}, "target_years", "목표 기간을 다시 골라 주세요."),
    ({"current_assets": -1}, "current_assets", "0 이상의 숫자만 입력할 수 있습니다."),
    ({"current_assets": 10_000_000_001}, "current_assets", "100억 원(1,000,000만 원)까지 입력할 수 있습니다."),
    ({"monthly_saving": 1_000_000_001}, "monthly_saving", "10억 원(100,000만 원)까지 입력할 수 있습니다."),
    ({"monthly_saving": 1.5}, "monthly_saving", "소수는 입력할 수 없습니다. 만 원 단위의 정수로 입력해 주세요."),
    ({"current_assets": "많이"}, "current_assets", "숫자만 입력할 수 있습니다."),
])
def test_scenario_invalid_conditions(client, apartments, changes, field, detail):
    response = _scenario(client, **changes)
    assert response.status_code == 422
    assert response.json() == {"detail": detail, "field": field}


def test_scenario_missing_values(client, apartments):
    # 계산에 필요한 값이 빠지면 계산하지 않는다 (FR-RESULT-10)
    no_assets = {k: v for k, v in EXAMPLE.items() if k != "current_assets"}
    response = client.post("/api/apartments/21/scenario", json={"conditions": no_assets, "area_band": 84})
    assert response.json() == {"detail": "필요한 값이 빠졌습니다.", "field": "current_assets"}
    response = client.post("/api/apartments/21/scenario", json={"conditions": EXAMPLE})
    assert response.json() == {"detail": "필요한 값이 빠졌습니다.", "field": "area_band"}
    response = client.post("/api/apartments/21/scenario", json={"area_band": 84})
    assert response.json() == {"detail": "필요한 값이 빠졌습니다.", "field": "conditions"}


def test_scenario_does_not_change_db(client, apartments, db):
    # 계산만 한다. 아파트와 평균가, 상품을 바꾸지 않는다
    before = [(p.apartment_id, p.area_band, p.avg_price) for p in db.query(models.ApartmentPrice).all()]
    _scenario(client)
    after = [(p.apartment_id, p.area_band, p.avg_price) for p in db.query(models.ApartmentPrice).all()]
    assert before == after
    assert db.query(models.SavedResult).count() == 0
