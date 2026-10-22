"""재무정보 3개 (A-29 ~ A-34)와 찜의 재무정보 (A-21 profile_id, A-35 찜 해제). 담당: 박채은 (2026-10-21)

- 회원 한 명에 3개까지. 칸 번호는 비어 있는 가장 작은 번호, 이름은 "재무정보 칸번호"
- A-08 ~ A-11은 ?profile_id=로 어느 재무정보인지 고른다. 없으면 칸 번호가 가장 작은 재무정보 (예전과 같음)
- 재무정보를 지우면 그 재무정보로 한 찜은 남고 profile_id만 비워진다. 같은 칸 번호로 새로 만들어도 이어지지 않는다
- 남의 재무정보, 남의 찜은 404
"""
from datetime import date

import pytest

from backend import models
from backend.services import auth

VALUES = {
    "age": 29, "annual_income": 36_000_000, "current_assets": 50_000_000,
    "loan_choice": "product", "loan_product_id": 1, "repayment_years": 30,
    "monthly_saving": 1_000_000, "target_years": 5,
}
NO_LOAN = {**VALUES, "loan_choice": "none", "loan_product_id": None, "repayment_years": None,
           "current_assets": 80_000_000, "monthly_saving": 2_000_000, "target_years": 3}


@pytest.fixture
def apartment(db, products):
    apt = models.Apartment(id=21, name="가아파트", gu="서구", dong="치평동", jibun="21")
    apt.prices.append(models.ApartmentPrice(
        area_band=84, exclusive_area="84.9400", supply_area="111.00", avg_price=300_000_000,
        min_price=300_000_000, max_price=300_000_000, trade_count=5,
        period_start=date(2025, 10, 1), period_end=date(2026, 9, 30),
    ))
    db.add(apt)
    db.add(models.User(id=2, login_id="otheruser", password_hash="!"))
    db.commit()


def _as(client, user_id):
    client.cookies.clear()
    client.cookies.set(auth.COOKIE_NAME, auth.make_token(user_id))


def _conditions(values):
    keys = ("current_assets", "monthly_saving", "target_years", "loan_choice", "loan_product_id", "repayment_years")
    return {key: values[key] for key in keys}


def _save_result(client, profile_id=None, values=VALUES):
    body = {"conditions": _conditions(values), "apartment_id": 21, "area_band": 84}
    if profile_id is not None:
        body["profile_id"] = profile_id
    return client.post("/api/saved-results", json=body)


# ── A-29, A-30 목록과 더하기 ────────────────────────────

def test_list_is_empty_at_first(client):
    assert client.get("/api/profiles").json() == {"profiles": [], "selected_id": None}


def test_create_fills_smallest_free_slot_and_name(client, products):
    first = client.post("/api/profiles", json=VALUES)
    assert first.status_code == 201
    one = first.json()["profile"]
    assert (one["slot"], one["name"], one["current_assets"], one["loan_product_name"]) == (1, "재무정보 1", 50_000_000, "[예시] 첫째 상품")

    two = client.post("/api/profiles", json=NO_LOAN).json()["profile"]
    assert (two["slot"], two["name"], two["loan_choice"], two["repayment_years"]) == (2, "재무정보 2", "none", None)

    listed = client.get("/api/profiles").json()
    assert [p["slot"] for p in listed["profiles"]] == [1, 2]
    assert listed["selected_id"] == one["id"]  # 고른 적이 없으면 칸 번호가 가장 작은 것


def test_create_up_to_three(client, products):
    for _ in range(3):
        assert client.post("/api/profiles", json=VALUES).status_code == 201
    response = client.post("/api/profiles", json=VALUES)
    assert response.status_code == 422
    assert response.json() == {"detail": "재무정보는 3개까지 저장할 수 있습니다."}


def test_create_after_delete_reuses_slot_but_not_id(client, products):
    ids = [client.post("/api/profiles", json=VALUES).json()["profile"]["id"] for _ in range(3)]
    assert client.delete(f"/api/profiles/{ids[0]}").status_code == 204
    again = client.post("/api/profiles", json=VALUES).json()["profile"]
    assert again["slot"] == 1 and again["name"] == "재무정보 1"
    assert again["id"] not in ids


@pytest.mark.parametrize("change, detail, field", [
    ({"current_assets": 10_000_000_001}, "100억 원(1,000,000만 원)까지 입력할 수 있습니다.", "current_assets"),
    ({"annual_income": -1}, "0 이상의 숫자만 입력할 수 있습니다.", "annual_income"),
    ({"monthly_saving": 1_000_000_001}, "10억 원(100,000만 원)까지 입력할 수 있습니다.", "monthly_saving"),
    ({"monthly_saving": 1.5}, "소수는 입력할 수 없습니다. 만 원 단위의 정수로 입력해 주세요.", "monthly_saving"),
    ({"age": 14}, "만 15세부터 100세까지 입력할 수 있습니다.", "age"),
    ({"target_years": 7}, "목표 기간을 다시 골라 주세요.", "target_years"),
    ({"repayment_years": None}, "대출 상품과 상환 기간을 골라 주세요.", None),
    ({"repayment_years": 40}, "상환 기간을 다시 골라 주세요.", "repayment_years"),
    ({"loan_product_id": 99}, "대출 상품과 상환 기간을 골라 주세요.", "loan_product_id"),
])
def test_create_checks_values_like_input_steps(client, products, db, change, detail, field):
    response = client.post("/api/profiles", json={**VALUES, **change})
    assert response.status_code == 422
    expected = {"detail": detail, "field": field} if field else {"detail": detail}
    assert response.json() == expected
    assert db.query(models.Profile).count() == 0


def test_boundary_values_are_accepted(client, products):
    body = {**VALUES, "annual_income": 0, "current_assets": 10_000_000_000, "monthly_saving": 1_000_000_000,
            "target_years": 0, "age": 100}
    profile = client.post("/api/profiles", json=body).json()["profile"]
    assert (profile["current_assets"], profile["monthly_saving"], profile["target_years"]) == (10_000_000_000, 1_000_000_000, 0)


# ── A-31 고치기, A-32 이름, A-33 지우기, A-34 고르기 ────────

def test_replace_keeps_name_and_slot(client, products):
    created = client.post("/api/profiles", json=VALUES).json()["profile"]
    client.put(f"/api/profiles/{created['id']}/name", json={"name": "신혼집"})
    changed = client.put(f"/api/profiles/{created['id']}", json=NO_LOAN).json()["profile"]
    assert (changed["name"], changed["slot"], changed["loan_choice"], changed["current_assets"]) == ("신혼집", 1, "none", 80_000_000)


@pytest.mark.parametrize("name, ok", [("  신혼집  ", "신혼집"), ("열글자이름입니다요", "열글자이름입니다요"), ("가나다라마바사아자차", "가나다라마바사아자차")])
def test_rename(client, products, name, ok):
    created = client.post("/api/profiles", json=VALUES).json()["profile"]
    response = client.put(f"/api/profiles/{created['id']}/name", json={"name": name})
    assert response.status_code == 200
    assert response.json()["profile"]["name"] == ok


@pytest.mark.parametrize("name", ["", "   ", "열한글자가넘는이름입니다"])
def test_rename_rejects_empty_or_long(client, products, name):
    created = client.post("/api/profiles", json=VALUES).json()["profile"]
    response = client.put(f"/api/profiles/{created['id']}/name", json={"name": name})
    assert response.status_code == 422
    assert response.json() == {"detail": "이름은 1자 이상 10자 이하로 입력해 주세요.", "field": "name"}


def test_selected_id_is_last_selected(client, products):
    one, two = (client.post("/api/profiles", json=VALUES).json()["profile"]["id"] for _ in range(2))
    assert client.put(f"/api/profiles/{two}/select").status_code == 204
    assert client.get("/api/profiles").json()["selected_id"] == two
    client.delete(f"/api/profiles/{two}")
    assert client.get("/api/profiles").json()["selected_id"] == one  # 고른 것을 지우면 칸 번호가 가장 작은 것


def test_others_profile_is_404(client, products, apartment):
    created = client.post("/api/profiles", json=VALUES).json()["profile"]["id"]
    _as(client, 2)
    for response in (
        client.put(f"/api/profiles/{created}", json=VALUES),
        client.put(f"/api/profiles/{created}/name", json={"name": "남의 것"}),
        client.delete(f"/api/profiles/{created}"),
        client.put(f"/api/profiles/{created}/select"),
        client.get(f"/api/profile?profile_id={created}"),
        client.put(f"/api/profile/plan?profile_id={created}", json={"monthly_saving": 0, "target_years": 3}),
        _save_result(client, profile_id=created),
    ):
        assert response.status_code == 404
        assert response.json() == {"detail": "재무정보를 찾을 수 없습니다."}
    assert client.get("/api/profiles").json()["profiles"] == []


def test_needs_login(anon_client):
    assert anon_client.get("/api/profiles").status_code == 401
    assert anon_client.post("/api/profiles", json=VALUES).status_code == 401
    assert anon_client.delete("/api/saved-results/1").status_code == 401


# ── A-08 ~ A-11의 profile_id ──────────────────────────

def test_input_steps_write_to_chosen_profile(client, products):
    one = client.post("/api/profiles", json=VALUES).json()["profile"]["id"]
    two = client.post("/api/profiles", json=NO_LOAN).json()["profile"]["id"]

    client.put(f"/api/profile/plan?profile_id={two}", json={"monthly_saving": 3_000_000, "target_years": 10})
    client.put(f"/api/profile/finance?profile_id={two}", json={"age": 40, "annual_income": 1, "current_assets": 2})
    assert client.get(f"/api/profile?profile_id={two}").json()["profile"]["monthly_saving"] == 3_000_000
    assert client.get(f"/api/profile?profile_id={two}").json()["profile"]["age"] == 40

    first = client.get("/api/profile").json()["profile"]  # 번호가 없으면 칸 번호가 가장 작은 것
    assert first["id"] == one and first["monthly_saving"] == 1_000_000 and first["age"] == 29


def test_finance_without_any_profile_makes_profile_one(client):
    profile = client.put("/api/profile/finance", json={"age": 29, "annual_income": 0, "current_assets": 0}).json()["profile"]
    assert (profile["slot"], profile["name"]) == (1, "재무정보 1")


# ── 찜: A-21 profile_id, A-22, A-35 ─────────────────────

def test_saved_result_keeps_profile_and_survives_profile_delete(client, apartment):
    one = client.post("/api/profiles", json=VALUES).json()["profile"]["id"]
    saved = _save_result(client, profile_id=one)
    assert saved.status_code == 201
    assert saved.json()["profile_id"] == one

    client.delete(f"/api/profiles/{one}")
    results = client.get("/api/saved-results").json()["results"]
    assert len(results) == 1 and results[0]["profile_id"] is None  # 삭제된 재무정보

    again = client.post("/api/profiles", json=VALUES).json()["profile"]  # 같은 칸 번호로 다시 만들어도
    assert again["slot"] == 1
    assert client.get("/api/saved-results").json()["results"][0]["profile_id"] is None  # 이어지지 않는다


def test_saved_result_without_profile_id(client, apartment):
    assert _save_result(client).json()["profile_id"] is None


def test_unsave(client, apartment):
    saved = _save_result(client).json()
    assert client.delete(f"/api/saved-results/{saved['id']}").status_code == 204
    assert client.get("/api/saved-results").json() == {"results": []}
    missing = client.delete(f"/api/saved-results/{saved['id']}")
    assert missing.status_code == 404
    assert missing.json() == {"detail": "저장한 결과를 찾을 수 없습니다."}


def test_unsave_others_is_404(client, apartment):
    saved = _save_result(client).json()
    _as(client, 2)
    assert client.delete(f"/api/saved-results/{saved['id']}").status_code == 404
    _as(client, 1)
    assert len(client.get("/api/saved-results").json()["results"]) == 1
