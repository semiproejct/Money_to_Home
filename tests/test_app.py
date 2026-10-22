"""서버의 틀을 확인한다. 화면 제공, 오류 응답의 모양, 입력 검증."""


def test_start_page_is_served(client):
    response = client.get("/")
    assert response.status_code == 200
    assert "머니 to 홈" in response.text


def test_config_returns_only_the_javascript_key(client):
    response = client.get("/api/config")
    assert response.status_code == 200
    assert list(response.json().keys()) == ["kakao_js_key"]


def test_unknown_api_returns_common_error_shape(client):
    response = client.get("/api/nothing-here")
    assert response.status_code == 404
    assert response.json() == {"detail": "찾는 것이 없습니다."}


def test_loan_products_is_empty_list_when_table_is_empty(client):
    response = client.get("/api/loan-products")
    assert response.status_code == 200
    assert response.json() == {"products": []}


def test_profile_is_null_when_nothing_is_saved(client):
    response = client.get("/api/profile")
    assert response.status_code == 200
    assert response.json() == {"profile": None}


def test_age_out_of_range_is_rejected(client):
    body = {"age": 14, "annual_income": 36000000, "current_assets": 50000000}
    response = client.put("/api/profile/finance", json=body)
    assert response.status_code == 422
    assert response.json() == {"detail": "만 15세부터 100세까지 입력할 수 있습니다.", "field": "age"}


def test_amount_over_limit_is_rejected(client):
    body = {"age": 29, "annual_income": 36000000, "current_assets": 10000000001}
    response = client.put("/api/profile/finance", json=body)
    assert response.status_code == 422
    assert response.json() == {
        "detail": "100억 원(1,000,000만 원)까지 입력할 수 있습니다.",
        "field": "current_assets",
    }


def test_decimal_amount_is_rejected(client):
    body = {"age": 29, "annual_income": 3600.5, "current_assets": 50000000}
    response = client.put("/api/profile/finance", json=body)
    assert response.status_code == 422
    assert response.json() == {
        "detail": "소수는 입력할 수 없습니다. 만 원 단위의 정수로 입력해 주세요.",
        "field": "annual_income",
    }


def test_text_amount_is_rejected(client):
    body = {"age": 29, "annual_income": "많음", "current_assets": 50000000}
    response = client.put("/api/profile/finance", json=body)
    assert response.status_code == 422
    assert response.json() == {"detail": "숫자만 입력할 수 있습니다.", "field": "annual_income"}


def test_missing_value_is_rejected(client):
    response = client.put("/api/profile/finance", json={"age": 29})
    assert response.status_code == 422
    assert response.json()["field"] == "annual_income"


def test_target_years_must_be_one_of_the_choices(client):
    response = client.put("/api/profile/plan", json={"monthly_saving": 1000000, "target_years": 7})
    assert response.status_code == 422
    assert response.json() == {"detail": "목표 기간을 다시 골라 주세요.", "field": "target_years"}


def test_product_choice_needs_product_and_years(client):
    body = {"loan_choice": "product", "loan_product_id": 1, "repayment_years": None}
    response = client.put("/api/profile/loan", json=body)
    assert response.status_code == 422
    assert response.json()["detail"] == "대출 상품과 상환 기간을 골라 주세요."


def test_loan_choice_needs_finance_first(client):
    body = {"loan_choice": "none", "loan_product_id": None, "repayment_years": None}
    response = client.put("/api/profile/loan", json=body)
    assert response.status_code == 422
    assert response.json() == {"detail": "재무정보를 먼저 입력해 주세요."}
