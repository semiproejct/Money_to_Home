"""재무정보를 저장하고 읽는 흐름 (A-08 ~ A-11). 임시 DB에 실제로 넣어 본다."""
FINANCE = {"age": 29, "annual_income": 36_000_000, "current_assets": 50_000_000}


def test_save_finance_then_read(client):
    saved = client.put("/api/profile/finance", json=FINANCE)
    assert saved.status_code == 200
    profile = saved.json()["profile"]
    assert (profile["age"], profile["annual_income"], profile["current_assets"]) == (29, 36_000_000, 50_000_000)
    assert profile["loan_choice"] is None and profile["monthly_saving"] is None
    assert profile["updated_at"]

    read = client.get("/api/profile").json()["profile"]
    assert read["current_assets"] == 50_000_000


def test_save_finance_twice_updates_one_row(client, db):
    from backend.models import Profile

    client.put("/api/profile/finance", json=FINANCE)
    client.put("/api/profile/finance", json={**FINANCE, "age": 30})
    assert db.query(Profile).count() == 1
    assert client.get("/api/profile").json()["profile"]["age"] == 30


def test_save_loan_with_product(client, products):
    client.put("/api/profile/finance", json=FINANCE)
    response = client.put("/api/profile/loan", json={"loan_choice": "product", "loan_product_id": 1, "repayment_years": 30})
    assert response.status_code == 200
    profile = response.json()["profile"]
    assert profile["loan_choice"] == "product"
    assert profile["loan_product_id"] == 1
    assert profile["loan_product_name"] == "[예시] 첫째 상품"
    assert profile["repayment_years"] == 30


def test_save_loan_rejects_years_not_in_product(client, products):
    client.put("/api/profile/finance", json=FINANCE)
    response = client.put("/api/profile/loan", json={"loan_choice": "product", "loan_product_id": 1, "repayment_years": 40})
    assert response.status_code == 422
    assert response.json() == {"detail": "상환 기간을 다시 골라 주세요.", "field": "repayment_years"}


def test_save_loan_rejects_unknown_product(client, products):
    client.put("/api/profile/finance", json=FINANCE)
    response = client.put("/api/profile/loan", json={"loan_choice": "product", "loan_product_id": 99, "repayment_years": 30})
    assert response.status_code == 422
    assert response.json()["field"] == "loan_product_id"


def test_save_loan_without_loan(client):
    client.put("/api/profile/finance", json=FINANCE)
    response = client.put("/api/profile/loan", json={"loan_choice": "none", "loan_product_id": None, "repayment_years": None})
    profile = response.json()["profile"]
    assert profile["loan_choice"] == "none"
    assert profile["loan_product_id"] is None and profile["loan_product_name"] is None


def test_save_plan(client):
    client.put("/api/profile/finance", json=FINANCE)
    response = client.put("/api/profile/plan", json={"monthly_saving": 1_000_000, "target_years": 5})
    profile = response.json()["profile"]
    assert (profile["monthly_saving"], profile["target_years"]) == (1_000_000, 5)


def test_plan_needs_finance_first(client):
    response = client.put("/api/profile/plan", json={"monthly_saving": 1_000_000, "target_years": 5})
    assert response.status_code == 422
    assert response.json() == {"detail": "재무정보를 먼저 입력해 주세요."}


def test_finance_without_restart_keeps_loan_and_plan(client, products):
    client.put("/api/profile/finance", json=FINANCE)
    client.put("/api/profile/loan", json={"loan_choice": "product", "loan_product_id": 1, "repayment_years": 30})
    client.put("/api/profile/plan", json={"monthly_saving": 1_000_000, "target_years": 5})

    profile = client.put("/api/profile/finance", json={**FINANCE, "current_assets": 60_000_000, "restart": False}).json()["profile"]
    assert profile["current_assets"] == 60_000_000
    assert profile["loan_choice"] == "product" and profile["target_years"] == 5


def test_finance_with_restart_clears_loan_and_plan(client, products):
    """ "처음부터 다시 입력"이면 대출 선택과 저축 계획을 함께 지운다."""
    client.put("/api/profile/finance", json=FINANCE)
    client.put("/api/profile/loan", json={"loan_choice": "product", "loan_product_id": 1, "repayment_years": 30})
    client.put("/api/profile/plan", json={"monthly_saving": 1_000_000, "target_years": 5})

    profile = client.put("/api/profile/finance", json={**FINANCE, "restart": True}).json()["profile"]
    assert profile["loan_choice"] is None and profile["loan_product_id"] is None and profile["repayment_years"] is None
    assert profile["monthly_saving"] is None and profile["target_years"] is None
