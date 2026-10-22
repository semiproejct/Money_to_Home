"""대출 계산 (A-03). 담당: 박채은

아파트를 고르기 전의 계산이다. 저장하지 않는다.
상품은 conftest.py의 products(예시 값: 첫째 3억 6,000만·70%·연 4.0%·10/15/20/30년,
둘째 5억·80%·연 4.5%·10/20/30/40년)를 쓴다. 기대값은 손으로 계산한 값이다.
"""
import pytest

BODY = {"current_assets": 50_000_000, "loan_product_id": 1, "repayment_years": 30}


def test_calc_loan_matches_spec_example(client, products):
    # API 명세서 A-03의 예시: 보유 5,000만, 첫째 상품, 30년
    # 대출: min(3억 6,000만, 5,000만 × 0.7 ÷ 0.3 = 116,666,666.67 → 버림), 월 상환: 연 4.0%, 360개월
    response = client.post("/api/calc/loan", json=BODY)
    assert response.status_code == 200
    assert response.json() == {"max_loan_amount": 116_666_666, "monthly_payment": 556_985}


def test_calc_loan_without_years_gives_no_monthly_payment(client, products):
    # 상품만 고르고 상환 기간을 고르기 전 (P-03 ②)
    response = client.post("/api/calc/loan", json={**BODY, "repayment_years": None})
    assert response.json() == {"max_loan_amount": 116_666_666, "monthly_payment": None}


def test_calc_loan_zero_assets_is_not_an_error(client, products):
    # 보유자산이 0원이면 대출금액과 월 상환액이 0원이다. 오류가 아니다 (P-03 ⑩)
    response = client.post("/api/calc/loan", json={**BODY, "current_assets": 0})
    assert response.status_code == 200
    assert response.json() == {"max_loan_amount": 0, "monthly_payment": 0}


def test_calc_loan_second_product(client, products):
    # min(5억, 5,000만 × 0.8 ÷ 0.2 = 2억), 연 4.5%, 480개월 (P-03 ④)
    response = client.post("/api/calc/loan", json={**BODY, "loan_product_id": 2, "repayment_years": 40})
    assert response.json() == {"max_loan_amount": 200_000_000, "monthly_payment": 899_126}


def test_calc_loan_stops_at_max_limit(client, products):
    # 2억 × 0.7 ÷ 0.3 = 4억 6,666만 > 한도 3억 6,000만 → 한도까지만
    response = client.post("/api/calc/loan", json={**BODY, "current_assets": 200_000_000})
    assert response.json() == {"max_loan_amount": 360_000_000, "monthly_payment": 1_718_695}


def test_calc_loan_accepts_the_largest_assets(client, products):
    # 100억이면 둘째 상품의 한도 5억에서 멈춘다. 연 4.5%, 120개월
    body = {"current_assets": 10_000_000_000, "loan_product_id": 2, "repayment_years": 10}
    response = client.post("/api/calc/loan", json=body)
    assert response.json() == {"max_loan_amount": 500_000_000, "monthly_payment": 5_181_920}


def test_calc_loan_other_term(client, products):
    # 같은 대출금액을 10년으로 갚으면 월 상환액이 커진다. 116,666,666원, 연 4.0%, 120개월
    response = client.post("/api/calc/loan", json={**BODY, "repayment_years": 10})
    assert response.json() == {"max_loan_amount": 116_666_666, "monthly_payment": 1_181_193}


@pytest.mark.parametrize(
    "change, detail, field",
    [
        ({"loan_product_id": 99}, "대출 상품과 상환 기간을 골라 주세요.", "loan_product_id"),
        ({"loan_product_id": None}, "대출 상품과 상환 기간을 골라 주세요.", "loan_product_id"),
        ({"repayment_years": 25}, "상환 기간을 다시 골라 주세요.", "repayment_years"),
        ({"repayment_years": 40}, "상환 기간을 다시 골라 주세요.", "repayment_years"),  # 둘째 상품에만 있는 기간
        ({"current_assets": -1}, "0 이상의 숫자만 입력할 수 있습니다.", "current_assets"),
        ({"current_assets": 10_000_000_001}, "100억 원(1,000,000만 원)까지 입력할 수 있습니다.", "current_assets"),
        ({"current_assets": 50000000.5}, "소수는 입력할 수 없습니다. 만 원 단위의 정수로 입력해 주세요.", "current_assets"),
        ({"current_assets": "오천만"}, "숫자만 입력할 수 있습니다.", "current_assets"),
    ],
)
def test_calc_loan_rejects_bad_values(client, products, change, detail, field):
    response = client.post("/api/calc/loan", json={**BODY, **change})
    assert response.status_code == 422
    assert response.json() == {"detail": detail, "field": field}


@pytest.mark.parametrize("name", ["current_assets", "loan_product_id", "repayment_years"])
def test_calc_loan_rejects_missing_value(client, products, name):
    body = {key: value for key, value in BODY.items() if key != name}
    response = client.post("/api/calc/loan", json=body)
    assert response.status_code == 422
    assert response.json() == {"detail": "필요한 값이 빠졌습니다.", "field": name}


def test_calc_loan_does_not_save(client, products):
    client.post("/api/calc/loan", json=BODY)
    assert client.get("/api/profile").json() == {"profile": None}
