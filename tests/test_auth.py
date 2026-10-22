"""회원 (A-14 ~ A-18). 임시 DB에 실제로 가입하고 로그인해 본다."""
import pytest

from backend import models
from backend.services import auth

SIGNUP = {"login_id": "home2026", "password": "money2home", "password_confirm": "money2home"}
FINANCE = {"age": 29, "annual_income": 36_000_000, "current_assets": 50_000_000}
MSG_ID = "아이디는 영문 소문자로 시작하는 5자 이상 20자 이하의 영문 소문자와 숫자여야 합니다."
MSG_PW = "비밀번호는 8자 이상이며 영문과 숫자를 포함해야 합니다."


# ---------------- A-14 아이디 확인 ----------------

@pytest.fixture
def client(anon_client):
    """이 파일의 테스트는 로그인하지 않은 브라우저에서 시작한다 (가입과 로그인을 직접 한다)."""
    return anon_client

def test_check_available(client):
    res = client.post("/api/auth/login-id/check", json={"login_id": "home2026"})
    assert res.status_code == 200
    assert res.json() == {"available": True}


def test_check_taken_is_409(client):
    client.post("/api/auth/signup", json=SIGNUP)
    res = client.post("/api/auth/login-id/check", json={"login_id": "home2026"})
    assert res.status_code == 409
    assert res.json() == {"detail": "이미 사용 중인 아이디입니다. 다른 아이디를 입력해 주세요.", "field": "login_id"}


@pytest.mark.parametrize("login_id", ["home", "Home2026", "2026home", "home_2026", "home 2026", "a" * 21, "홈이천이십육", ""])
def test_check_rule(client, login_id):
    res = client.post("/api/auth/login-id/check", json={"login_id": login_id})
    assert res.status_code == 422
    assert res.json() == {"detail": MSG_ID, "field": "login_id"}


@pytest.mark.parametrize("login_id", ["homes", "a2026", "a" * 20])
def test_check_rule_edges_pass(client, login_id):
    assert client.post("/api/auth/login-id/check", json={"login_id": login_id}).status_code == 200


# ---------------- A-15 회원가입 ----------------
def test_signup_logs_in(client, db):
    res = client.post("/api/auth/signup", json=SIGNUP)
    assert res.status_code == 201
    assert res.json() == {"login_id": "home2026"}
    cookie = res.headers["set-cookie"]
    assert cookie.startswith(f"{auth.COOKIE_NAME}=") and "HttpOnly" in cookie and "SameSite=lax" in cookie
    assert "Max-Age=1800" in cookie
    assert client.get("/api/auth/me").json() == {"login_id": "home2026"}  # 가입과 함께 로그인된다


def test_password_is_stored_as_hash(client, db):
    client.post("/api/auth/signup", json=SIGNUP)
    user = db.query(models.User).filter_by(login_id="home2026").one()
    assert "money2home" not in user.password_hash
    assert user.password_hash.startswith("$2")  # bcrypt
    assert auth.verify_password("money2home", user.password_hash)
    assert not auth.verify_password("money2homE", user.password_hash)


def test_signup_same_id_is_409(client, db):
    client.post("/api/auth/signup", json=SIGNUP)
    res = client.post("/api/auth/signup", json={**SIGNUP, "password": "other1234", "password_confirm": "other1234"})
    assert res.status_code == 409
    assert res.json()["field"] == "login_id"
    assert db.query(models.User).filter_by(login_id="home2026").count() == 1


@pytest.mark.parametrize("password", ["a1b2c3d", "abcdefgh", "12345678", "", "가나다라마바사아1"])
def test_signup_password_rule(client, password):
    res = client.post("/api/auth/signup", json={"login_id": "home2026", "password": password, "password_confirm": password})
    assert res.status_code == 422
    assert res.json() == {"detail": MSG_PW, "field": "password"}


def test_signup_password_confirm(client, db):
    res = client.post("/api/auth/signup", json={**SIGNUP, "password_confirm": "money2homE"})
    assert res.status_code == 422
    assert res.json() == {"detail": "비밀번호가 서로 다릅니다.", "field": "password_confirm"}
    assert db.query(models.User).count() == 1  # 테스트 사용자만 있다. 가입되지 않았다


def test_signup_missing_value(client):
    res = client.post("/api/auth/signup", json={"login_id": "home2026", "password": "money2home"})
    assert res.status_code == 422
    assert res.json() == {"detail": "필요한 값이 빠졌습니다.", "field": "password_confirm"}


def test_signup_long_password(client):
    # bcrypt는 72바이트까지만 읽는다. 그 뒤가 달라도 다른 비밀번호로 본다
    long = "a1" * 60
    client.post("/api/auth/signup", json={"login_id": "home2026", "password": long, "password_confirm": long})
    client.post("/api/auth/logout")
    assert client.post("/api/auth/login", json={"login_id": "home2026", "password": long[:-2] + "b2"}).status_code == 401
    assert client.post("/api/auth/login", json={"login_id": "home2026", "password": long}).status_code == 200


# ---------------- A-16 로그인 ----------------
def test_login(client):
    client.post("/api/auth/signup", json=SIGNUP)
    client.post("/api/auth/logout")
    res = client.post("/api/auth/login", json={"login_id": "home2026", "password": "money2home"})
    assert res.status_code == 200
    assert res.json() == {"login_id": "home2026"}
    assert client.get("/api/auth/me").status_code == 200


@pytest.mark.parametrize("body", [
    {"login_id": "home2026", "password": "money2homE"},  # 비밀번호가 틀림
    {"login_id": "home2027", "password": "money2home"},  # 없는 아이디
    {"login_id": "testuser", "password": "!"},  # 해시가 없는 테스트 사용자
    {"login_id": "HOME2026", "password": "money2home"},  # 규칙에 맞지 않는 아이디도 같은 답
])
def test_login_wrong_is_same_401(client, body):
    client.post("/api/auth/signup", json=SIGNUP)
    client.post("/api/auth/logout")
    res = client.post("/api/auth/login", json=body)
    assert res.status_code == 401
    assert res.json() == {"detail": "아이디 또는 비밀번호가 맞지 않습니다."}  # 어느 쪽이 틀렸는지 알리지 않는다
    assert client.get("/api/auth/me").status_code == 401


# ---------------- A-17 로그아웃, A-18 상태 확인 ----------------
def test_me_without_login_is_401(client):
    res = client.get("/api/auth/me")
    assert res.status_code == 401
    assert res.json() == {"detail": "로그인이 필요합니다."}


def test_logout(client):
    client.post("/api/auth/signup", json=SIGNUP)
    res = client.post("/api/auth/logout")
    assert res.status_code == 204
    assert client.get("/api/auth/me").status_code == 401
    assert client.post("/api/auth/logout").status_code == 401  # 로그인이 필요한 API다


# ---------------- 로그인 쿠키 ----------------
def test_cookie_changed_by_hand_is_rejected(client):
    client.post("/api/auth/signup", json=SIGNUP)
    token = client.cookies.get(auth.COOKIE_NAME)
    user_id, issued, signature = token.split(".")
    for forged in (f"1.{issued}.{signature}", f"{user_id}.{int(issued) + 1}.{signature}", f"{user_id}.{issued}", "abc", "1.2.3", "한글"):
        assert auth.read_token(forged) is None
    assert auth.read_token(token) == int(user_id)


def test_login_ends_30_minutes_after_last_request(client, monkeypatch):
    start = 1_800_000_000
    monkeypatch.setattr(auth, "now", lambda: start)
    client.post("/api/auth/signup", json=SIGNUP)

    # 29분 뒤에 요청하면 쿠키가 새로 나온다
    monkeypatch.setattr(auth, "now", lambda: start + 29 * 60)
    res = client.get("/api/auth/me")
    assert res.status_code == 200
    assert auth.COOKIE_NAME in res.headers.get("set-cookie", "")

    # 그 요청에서 29분 뒤(가입에서는 58분 뒤)에도 로그인 상태다
    monkeypatch.setattr(auth, "now", lambda: start + 58 * 60)
    assert client.get("/api/auth/me").status_code == 200

    # 마지막 요청에서 30분이 넘으면 풀린다
    monkeypatch.setattr(auth, "now", lambda: start + 58 * 60 + 30 * 60 + 1)
    assert client.get("/api/auth/me").status_code == 401


def test_other_requests_also_keep_login(client, monkeypatch):
    start = 1_800_000_000
    monkeypatch.setattr(auth, "now", lambda: start)
    client.post("/api/auth/signup", json=SIGNUP)
    monkeypatch.setattr(auth, "now", lambda: start + 20 * 60)
    client.get("/api/health")  # 로그인과 상관없는 요청도 "마지막 요청"이다
    monkeypatch.setattr(auth, "now", lambda: start + 45 * 60)
    assert client.get("/api/auth/me").status_code == 200


# ---------------- 재무정보는 로그인한 회원의 것만 ----------------
def test_profile_needs_login(client, db):
    # 로그인하지 않은 사용자의 값은 브라우저에만 둔다. 재무정보 API는 401이다 (FR-PROFILE-04)
    assert client.put("/api/profile/finance", json=FINANCE).status_code == 401
    assert client.get("/api/profile").status_code == 401
    assert client.put("/api/profile/plan", json={"monthly_saving": 1_000_000, "target_years": 5}).status_code == 401
    assert db.query(models.Profile).count() == 0

    client.post("/api/auth/signup", json=SIGNUP)
    assert client.get("/api/profile").json()["profile"] is None  # 새 회원은 저장한 값이 없다
    client.put("/api/profile/finance", json={**FINANCE, "age": 40})
    assert client.get("/api/profile").json()["profile"]["age"] == 40

    client.post("/api/auth/logout")
    assert client.get("/api/profile").status_code == 401
    assert db.query(models.Profile).count() == 1


def test_two_users_do_not_see_each_other(client):
    client.post("/api/auth/signup", json=SIGNUP)
    client.put("/api/profile/finance", json=FINANCE)
    client.post("/api/auth/logout")

    other = {"login_id": "other2026", "password": "other1234", "password_confirm": "other1234"}
    client.post("/api/auth/signup", json=other)
    assert client.get("/api/profile").json()["profile"] is None


# ---------------- A-19 비밀번호 변경 (3차) ----------------
NEW_PW = {"current_password": "money2home", "new_password": "newpass2026", "new_password_confirm": "newpass2026"}


def test_change_password(client):
    client.post("/api/auth/signup", json=SIGNUP)
    res = client.put("/api/auth/password", json=NEW_PW)
    assert res.status_code == 204
    assert client.get("/api/auth/me").status_code == 200  # 바꾼 뒤에도 로그인 상태다
    client.post("/api/auth/logout")
    assert client.post("/api/auth/login", json={"login_id": "home2026", "password": "money2home"}).status_code == 401
    assert client.post("/api/auth/login", json={"login_id": "home2026", "password": "newpass2026"}).status_code == 200


def test_change_password_wrong_current(client):
    client.post("/api/auth/signup", json=SIGNUP)
    res = client.put("/api/auth/password", json={**NEW_PW, "current_password": "wrong1234"})
    assert res.status_code == 422
    assert res.json() == {"detail": "지금 비밀번호가 맞지 않습니다.", "field": "current_password"}
    client.post("/api/auth/logout")
    assert client.post("/api/auth/login", json={"login_id": "home2026", "password": "money2home"}).status_code == 200


@pytest.mark.parametrize("body, field, detail", [
    ({**NEW_PW, "new_password": "short1", "new_password_confirm": "short1"}, "new_password", MSG_PW),
    ({**NEW_PW, "new_password": "abcdefgh", "new_password_confirm": "abcdefgh"}, "new_password", MSG_PW),
    ({**NEW_PW, "new_password_confirm": "newpass2027"}, "new_password_confirm", "비밀번호가 서로 다릅니다."),
    ({"current_password": "money2home", "new_password": "newpass2026"}, "new_password_confirm", "필요한 값이 빠졌습니다."),
])
def test_change_password_rules(client, body, field, detail):
    client.post("/api/auth/signup", json=SIGNUP)
    res = client.put("/api/auth/password", json=body)
    assert res.status_code == 422
    assert res.json() == {"detail": detail, "field": field}


def test_change_password_needs_login(client):
    assert client.put("/api/auth/password", json=NEW_PW).status_code == 401


def test_password_stored_as_new_hash(client, db):
    client.post("/api/auth/signup", json=SIGNUP)
    before = db.query(models.User).filter_by(login_id="home2026").one().password_hash
    client.put("/api/auth/password", json=NEW_PW)
    db.expire_all()
    after = db.query(models.User).filter_by(login_id="home2026").one().password_hash
    assert after != before and after.startswith("$2") and "newpass2026" not in after


# ---------------- A-20 회원 탈퇴 (3차) ----------------
def test_withdraw_deletes_everything(client, db, products):
    client.post("/api/auth/signup", json=SIGNUP)
    client.put("/api/profile/finance", json=FINANCE)
    user_id = db.query(models.User).filter_by(login_id="home2026").one().id
    db.add(models.SavedResult(
        user_id=user_id, apartment_name="가아파트", gu="서구", dong="치평동", area_band=84, exclusive_area="84.9", avg_price=1,
        current_assets=0, monthly_saving=0, target_years=0, loan_choice="none", accumulated_saving=0, shortage=1, category="lack",
    ))
    db.commit()

    res = client.request("DELETE", "/api/auth/me", json={"password": "money2home"})
    assert res.status_code == 204
    db.expire_all()
    assert db.query(models.User).filter_by(login_id="home2026").count() == 0
    assert db.query(models.Profile).filter_by(user_id=user_id).count() == 0
    assert db.query(models.SavedResult).filter_by(user_id=user_id).count() == 0
    assert client.get("/api/auth/me").status_code == 401  # 로그아웃된다
    assert client.post("/api/auth/login", json={"login_id": "home2026", "password": "money2home"}).status_code == 401
    # 같은 아이디로 다시 가입할 수 있다
    assert client.post("/api/auth/login-id/check", json={"login_id": "home2026"}).status_code == 200


def test_withdraw_keeps_other_users(client, db):
    other = {"login_id": "other2026", "password": "other1234", "password_confirm": "other1234"}
    client.post("/api/auth/signup", json=other)
    client.put("/api/profile/finance", json=FINANCE)
    client.post("/api/auth/logout")
    client.post("/api/auth/signup", json=SIGNUP)
    client.request("DELETE", "/api/auth/me", json={"password": "money2home"})
    db.expire_all()
    assert db.query(models.User).filter_by(login_id="other2026").count() == 1
    assert db.query(models.Profile).count() == 1


def test_withdraw_wrong_password(client, db):
    client.post("/api/auth/signup", json=SIGNUP)
    res = client.request("DELETE", "/api/auth/me", json={"password": "wrong1234"})
    assert res.status_code == 422
    assert res.json() == {"detail": "비밀번호가 맞지 않습니다.", "field": "password"}
    assert db.query(models.User).filter_by(login_id="home2026").count() == 1
    assert client.get("/api/auth/me").status_code == 200


def test_withdraw_needs_login(client):
    assert client.request("DELETE", "/api/auth/me", json={"password": "money2home"}).status_code == 401


# ---------------- 가입 동의 (3차, FR-USER-05) ----------------
@pytest.mark.parametrize("agreed, stored", [(True, True), (False, False), (None, False)])
def test_signup_agreed_time(client, db, agreed, stored):
    body = {**SIGNUP} if agreed is None else {**SIGNUP, "agreed": agreed}
    client.post("/api/auth/signup", json=body)
    user = db.query(models.User).filter_by(login_id="home2026").one()
    assert (user.terms_agreed_at is not None) == stored
