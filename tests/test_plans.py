"""저축 계획 계산 (A-04). DB를 읽지 않는 계산이다."""
import pytest

BODY = {"current_assets": 50_000_000, "monthly_saving": 1_000_000, "target_years": 5}


def test_calc_plan_matches_spec_example(client):
    # API 명세서의 예시: 보유 5,000만, 월 100만, 5년 -> 누적 6,000만, 자기자금 1억 1,000만
    response = client.post("/api/calc/plan", json=BODY)
    assert response.status_code == 200
    assert response.json() == {"accumulated_saving": 60_000_000, "own_funds": 110_000_000}


def test_calc_plan_now_keeps_current_assets(client):
    # 목표 기간 "지금"(0년)이면 누적 저축액은 0이고 자기자금은 현재 보유자산과 같다 (P-04 ⑦)
    response = client.post("/api/calc/plan", json={**BODY, "target_years": 0})
    assert response.json() == {"accumulated_saving": 0, "own_funds": 50_000_000}


def test_calc_plan_zero_saving_and_zero_assets(client):
    response = client.post("/api/calc/plan", json={"current_assets": 0, "monthly_saving": 0, "target_years": 10})
    assert response.status_code == 200
    assert response.json() == {"accumulated_saving": 0, "own_funds": 0}


def test_calc_plan_accepts_the_largest_values(client):
    body = {"current_assets": 10_000_000_000, "monthly_saving": 1_000_000_000, "target_years": 10}
    response = client.post("/api/calc/plan", json=body)
    assert response.json() == {"accumulated_saving": 120_000_000_000, "own_funds": 130_000_000_000}


@pytest.mark.parametrize(
    "change, detail, field",
    [
        ({"target_years": 7}, "목표 기간을 다시 골라 주세요.", "target_years"),
        ({"monthly_saving": -1}, "0 이상의 숫자만 입력할 수 있습니다.", "monthly_saving"),
        ({"monthly_saving": 1_000_000_001}, "10억 원(100,000만 원)까지 입력할 수 있습니다.", "monthly_saving"),
        ({"monthly_saving": 1000000.5}, "소수는 입력할 수 없습니다. 만 원 단위의 정수로 입력해 주세요.", "monthly_saving"),
        ({"monthly_saving": "백만"}, "숫자만 입력할 수 있습니다.", "monthly_saving"),
        ({"current_assets": -1}, "0 이상의 숫자만 입력할 수 있습니다.", "current_assets"),
        ({"current_assets": 10_000_000_001}, "100억 원(1,000,000만 원)까지 입력할 수 있습니다.", "current_assets"),
    ],
)
def test_calc_plan_rejects_bad_values(client, change, detail, field):
    response = client.post("/api/calc/plan", json={**BODY, **change})
    assert response.status_code == 422
    assert response.json() == {"detail": detail, "field": field}


def test_calc_plan_rejects_missing_value(client):
    response = client.post("/api/calc/plan", json={"current_assets": 50_000_000, "monthly_saving": 1_000_000})
    assert response.status_code == 422
    assert response.json() == {"detail": "필요한 값이 빠졌습니다.", "field": "target_years"}


def test_calc_plan_does_not_save(client):
    client.post("/api/calc/plan", json=BODY)
    assert client.get("/api/profile").json() == {"profile": None}
