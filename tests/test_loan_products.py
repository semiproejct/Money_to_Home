"""대출 상품 목록 (A-01)."""


def test_products_come_in_id_order(client, products):
    body = client.get("/api/loan-products").json()
    assert [p["id"] for p in body["products"]] == [1, 2]


def test_product_shape(client, products):
    first = client.get("/api/loan-products").json()["products"][0]
    assert first["max_limit"] == 360_000_000
    assert first["ltv_ratio"] == 0.7
    assert first["annual_rate_pct"] == 4.0
    assert first["repayment_years_options"] == [10, 15, 20, 30]  # DB의 "10,15,20,30"을 숫자의 목록으로
    assert first["max_house_price"] == 600_000_000
    assert first["base_date"] == "2026-10-01"


def test_product_without_price_cap(client, products):
    second = client.get("/api/loan-products").json()["products"][1]
    assert second["max_house_price"] is None


def test_for_calc_gives_what_calc_needs(db, products):
    from backend.services import calc, loan_product

    product = loan_product.for_calc(loan_product.find_by_id(db, 1))
    assert calc.loan_amount(300_000_000, product) == 210_000_000
    assert calc.max_loan_amount(50_000_000, product) == 116_666_666
    assert loan_product.for_calc(None) is None
