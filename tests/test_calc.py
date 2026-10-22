"""계산 모듈의 테스트. 담당: 박채은

backend/services/calc.py에 함수를 만들 때마다 여기에 테스트를 붙인다 (NFR-03).
정상값, 경계값(0원, 목표 기간 "지금", 최대 한도 초과, 대출 없이 계산),
손으로 계산한 사례 5건 이상을 넣는다.

예시 값 (API 명세서 3장과 와이어프레임이 같은 값을 쓴다)
    보유자산 5,000만 원, 월 저축 100만 원, 5년
    첫째 상품: 최대 한도 3억 6,000만 원, 대출 비율 70%, 연 4.0%, 상환 30년

    누적 저축액            60,000,000
    목표 시점 자기자금    110,000,000
    최대 예상 대출금액    116,666,666
    그때의 월 상환액          556,985
    목표 가능 가격        366,666,666

    3억 원 아파트:   대출 210,000,000 / 월 상환 1,002,572 / 부족자금 -20,000,000 (기간 내 가능)
    4억 5천 아파트:  부족자금 25,000,000 / 필요 월 저축액 1,416,667

쓰는 모양
    from backend.services import calc

    def test_accumulated_saving():
        assert calc.accumulated_saving(1_000_000, 5) == 60_000_000
"""
import pytest

from backend.services import calc

# 문서의 예시 상품 (db/seed_loan_products.sql의 1번, 2번과 같은 값)
PRODUCT_1 = {"max_limit": 360_000_000, "ltv_ratio": 0.7, "annual_rate_pct": 4.0}
PRODUCT_2 = {"max_limit": 500_000_000, "ltv_ratio": 0.8, "annual_rate_pct": 4.5}


# ---------------------------------------------------------------------------
# 손으로 계산한 사례 1: 문서의 예시 값 (보유 5,000만, 월 100만, 5년, 첫째 상품)
# ---------------------------------------------------------------------------


def test_example_conditions():
    acc = calc.accumulated_saving(1_000_000, 5)
    own = calc.own_funds(50_000_000, acc)
    max_loan = calc.max_loan_amount(50_000_000, PRODUCT_1)

    assert acc == 60_000_000
    assert own == 110_000_000
    # 50,000,000 × 0.7 ÷ 0.3 = 116,666,666.67 → 버림
    assert max_loan == 116_666_666
    assert calc.monthly_payment(max_loan, 4.0, 30) == 556_985
    # 110,000,000 ÷ 0.3 = 366,666,666.67 → 버림. 110,000,000 + 360,000,000보다 작다.
    assert calc.target_price(own, PRODUCT_1) == 366_666_666


# ---------------------------------------------------------------------------
# 손으로 계산한 사례 2: 3억 원 아파트 → 기간 내 가능
# ---------------------------------------------------------------------------


def test_example_300m_within():
    price = 300_000_000
    loan = calc.loan_amount(price, PRODUCT_1)

    assert loan == 210_000_000  # 300,000,000 × 0.7
    assert calc.monthly_payment(loan, 4.0, 30) == 1_002_572
    assert calc.shortage(price, 110_000_000, loan) == -20_000_000  # 여유자금 2,000만
    # 지금: 5,000만 + 2억 1,000만 = 2억 6,000만 < 3억. 목표 시점: 1억 1,000만 + 2억 1,000만 = 3억 2,000만 ≥ 3억
    assert calc.category(50_000_000, 110_000_000, loan, price, 5) == calc.WITHIN
    # (366,666,666 ÷ 300,000,000)^(1/5) − 1 = 4.095...% → 4.0
    assert calc.allowed_growth_rate(366_666_666, price, 5) == 4.0


# ---------------------------------------------------------------------------
# 손으로 계산한 사례 3: 4억 5,000만 원 아파트 → 자금 부족
# ---------------------------------------------------------------------------


def test_example_450m_lack():
    price = 450_000_000
    loan = calc.loan_amount(price, PRODUCT_1)

    assert loan == 315_000_000  # 450,000,000 × 0.7. 한도 3억 6,000만보다 작다.
    assert calc.shortage(price, 110_000_000, loan) == 25_000_000
    assert calc.category(50_000_000, 110_000_000, loan, price, 5) == calc.LACK
    # (450,000,000 − 315,000,000 − 50,000,000) ÷ 60 = 1,416,666.67 → 올림
    assert calc.required_monthly_saving(price, loan, 50_000_000, 5) == 1_416_667
    # 목표 가능 가격이 평균가보다 작으면 결과가 음수 → 없음
    assert calc.allowed_growth_rate(366_666_666, price, 5) is None


# ---------------------------------------------------------------------------
# 손으로 계산한 사례 4: 둘째 상품 (80%, 한도 5억, 연 4.5%, 40년)
# ---------------------------------------------------------------------------


def test_second_product():
    # 50,000,000 × 0.8 ÷ 0.2 = 200,000,000
    max_loan = calc.max_loan_amount(50_000_000, PRODUCT_2)
    assert max_loan == 200_000_000
    # m = 0.045 ÷ 12 = 0.00375, N = 480 → 899,125.67 → 반올림
    assert calc.monthly_payment(max_loan, 4.5, 40) == 899_126


# ---------------------------------------------------------------------------
# 손으로 계산한 사례 5: 대출 없이 계산 (C-13)
# ---------------------------------------------------------------------------


def test_without_loan():
    assert calc.loan_amount(300_000_000, None) == 0
    assert calc.max_loan_amount(50_000_000, None) == 0
    # 목표 가능 가격은 자기자금과 같다
    assert calc.target_price(110_000_000, None) == 110_000_000
    # 1억 원 아파트: 지금 5,000만 < 1억, 목표 시점 1억 1,000만 ≥ 1억
    assert calc.category(50_000_000, 110_000_000, 0, 100_000_000, 5) == calc.WITHIN
    assert calc.shortage(100_000_000, 110_000_000, 0) == -10_000_000
    # 3억 원 아파트: (300,000,000 − 0 − 50,000,000) ÷ 60 = 4,166,666.67 → 올림
    assert calc.required_monthly_saving(300_000_000, 0, 50_000_000, 5) == 4_166_667


# ---------------------------------------------------------------------------
# 손으로 계산한 사례 6: 다른 금리와 기간
# ---------------------------------------------------------------------------


def test_monthly_payment_other_rate():
    # 1억, 연 3.5%, 20년: m = 0.035 ÷ 12, N = 240 → 579,959.72 → 반올림
    assert calc.monthly_payment(100_000_000, 3.5, 20) == 579_960


# ---------------------------------------------------------------------------
# 경계값
# ---------------------------------------------------------------------------


def test_target_years_now():
    """목표 기간 "지금"(0년)"""
    assert calc.accumulated_saving(1_000_000, 0) == 0
    assert calc.own_funds(50_000_000, 0) == 50_000_000
    # 지금이면 within이 나오지 않는다
    assert calc.category(50_000_000, 50_000_000, 210_000_000, 300_000_000, 0) == calc.LACK
    assert calc.required_monthly_saving(300_000_000, 210_000_000, 50_000_000, 0) is None
    assert calc.allowed_growth_rate(366_666_666, 300_000_000, 0) is None


def test_zero_assets():
    """보유자산 0원이면 최대 예상 대출금액이 0원이다. 오류가 아니다."""
    assert calc.max_loan_amount(0, PRODUCT_1) == 0
    assert calc.target_price(0, PRODUCT_1) == 0
    assert calc.own_funds(0, 0) == 0


def test_over_max_limit():
    """최대 한도를 넘으면 한도까지만 빌린다."""
    # 6억 × 0.7 = 4억 2,000만 > 한도 3억 6,000만
    assert calc.loan_amount(600_000_000, PRODUCT_1) == 360_000_000
    # 보유 2억: 2억 ÷ 0.3 = 6억 6,666만 > 2억 + 한도 3억 6,000만 = 5억 6,000만
    assert calc.max_loan_amount(200_000_000, PRODUCT_1) == 360_000_000
    assert calc.target_price(200_000_000, PRODUCT_1) == 560_000_000


def test_category_boundary_now():
    """보유자산 + 대출금액이 평균가와 같으면 지금 가능이다 (≥)."""
    assert calc.category(90_000_000, 150_000_000, 210_000_000, 300_000_000, 5) == calc.NOW


def test_category_boundary_within():
    """자기자금 + 대출금액이 평균가와 같으면 기간 내 가능이다 (≥)."""
    assert calc.category(50_000_000, 90_000_000, 210_000_000, 300_000_000, 5) == calc.WITHIN


def test_loan_amount_floor():
    """원 미만은 버린다. 333,333,333 × 0.7 = 233,333,333.1"""
    assert calc.loan_amount(333_333_333, PRODUCT_1) == 233_333_333


def test_ratio_one():
    """대출 비율이 1이면 최대 예상 대출금액은 한도, 목표 가능 가격은 자기자금 + 한도다."""
    product = {"max_limit": 300_000_000, "ltv_ratio": 1.0}
    assert calc.max_loan_amount(50_000_000, product) == 300_000_000
    assert calc.target_price(50_000_000, product) == 350_000_000


def test_zero_rate():
    """금리가 0이면 대출금액 ÷ N. 1억 2,000만 ÷ 120 = 100만"""
    assert calc.monthly_payment(120_000_000, 0, 10) == 1_000_000


def test_required_monthly_saving_none_when_no_need():
    """보유자산과 대출금액만으로 평균가를 넘으면 필요 월 저축액이 없다."""
    assert calc.required_monthly_saving(300_000_000, 210_000_000, 100_000_000, 5) is None


def test_allowed_growth_rate_zero_and_floor():
    # 목표 가능 가격과 평균가가 같으면 0.0 (음수가 아니므로 보여 준다)
    assert calc.allowed_growth_rate(300_000_000, 300_000_000, 5) == 0.0
    # (1.1)^(1/3) − 1 = 3.228...% → 3.2
    assert calc.allowed_growth_rate(110_000_000, 100_000_000, 3) == 3.2
    # (366,666,666 ÷ 350,000,000)^(1/5) − 1 = 0.934...% → 0.9
    assert calc.allowed_growth_rate(366_666_666, 350_000_000, 5) == 0.9


def test_returns_int():
    """금액은 원 단위 정수다 (NFR-12)."""
    values = [
        calc.accumulated_saving(1_000_000, 5),
        calc.own_funds(50_000_000, 60_000_000),
        calc.loan_amount(300_000_000, PRODUCT_1),
        calc.max_loan_amount(50_000_000, PRODUCT_1),
        calc.monthly_payment(210_000_000, 4.0, 30),
        calc.target_price(110_000_000, PRODUCT_1),
        calc.shortage(300_000_000, 110_000_000, 210_000_000),
        calc.required_monthly_saving(450_000_000, 315_000_000, 50_000_000, 5),
    ]
    assert all(type(value) is int for value in values)


# ---------------------------------------------------------------------------
# 계산 검증 표 (남은 작업 계획 B-7). 실제 DB의 아파트 8곳을 손으로 계산하고 화면(A-07)의 값과 맞춰 봤다.
#
# 평균가는 2026-10-14에 A-05로 받은 값이고, 상품은 DB에 넣은 실제 두 상품이다.
# 손 계산은 calc.py를 부르지 않고 요구사항 명세서 부록 C의 식을 따로 써서 했다.
# 같은 날 A-07(POST /api/apartments/{id}/scenario)의 응답과 8건 모두 일치했다.
# 여기서는 calc의 함수를 A-07과 같은 순서로 불러 그 손 계산 값이 나오는지 고정해 둔다.
#
#   대출금액 = min(한도, 평균가 × 0.7) 버림
#   월 상환액 = 대출금액 × m × (1+m)^N ÷ ((1+m)^N − 1), m = 연 금리 ÷ 12, N = 상환 연수 × 12, 반올림
#   부족자금 = 평균가 − 자기자금 − 대출금액
#   필요 월 저축액 = (평균가 − 대출금액 − 보유자산) ÷ (12 × 목표 연수) 올림. 부족할 때만
#   허용 상승률 = (목표 가능 가격 ÷ 평균가)^(1 ÷ 목표 연수) − 1, 소수 첫째 자리 버림
# ---------------------------------------------------------------------------

# db/seed_loan_products.sql의 실제 상품 (기준일 2026-10-01, 2026-09-17)
PRODUCT_HF = {"max_limit": 360_000_000, "ltv_ratio": 0.7, "annual_rate_pct": 5.2, "max_house_price": 600_000_000}
PRODUCT_KAKAO = {"max_limit": 1_000_000_000, "ltv_ratio": 0.7, "annual_rate_pct": 5.42, "max_house_price": None}

# (사례, 평균가, 보유자산, 월 저축, 목표 연수, 상품, 상환 연수,
#  기대값: 대출금액, 월 상환액, 구분, 부족자금, 필요 월 저축액, 허용 상승률)
VERIFY_CASES = [
    # A 동구 두산위브2차 59㎡. 333,861,111 × 0.7 = 233,702,777.7 → 233,702,777
    #   333,861,111 − 110,000,000 − 233,702,777 = −9,841,666 (여유)
    #   목표 가능 가격 110,000,000 ÷ 0.3 = 366,666,666 → (366,666,666 ÷ 333,861,111)^(1/5) − 1 = 1.89% → 1.8
    ("A 기간 내 가능", 333_861_111, 50_000_000, 1_000_000, 5, PRODUCT_HF, 30,
     233_702_777, 1_283_287, calc.WITHIN, -9_841_666, None, 1.8),
    # B 동구 두산위브2차 84㎡. 433,300,000 × 0.7 = 303,310,000
    #   433,300,000 − 110,000,000 − 303,310,000 = 19,990,000 (부족)
    #   (433,300,000 − 303,310,000 − 50,000,000) ÷ 60 = 1,333,166.7 → 1,333,167
    ("B 자금 부족", 433_300_000, 50_000_000, 1_000_000, 5, PRODUCT_HF, 30,
     303_310_000, 1_665_508, calc.LACK, 19_990_000, 1_333_167, None),
    # C 동구 라인1차 84㎡. 165,666,667 × 0.7 = 115,966,666.9 → 115,966,666
    #   지금 50,000,000 + 115,966,666 = 165,966,666 ≥ 165,666,667 → 지금 가능
    #   (366,666,666 ÷ 165,666,667)^(1/5) − 1 = 17.23% → 17.2
    ("C 지금 가능", 165_666_667, 50_000_000, 1_000_000, 5, PRODUCT_HF, 30,
     115_966_666, 636_786, calc.NOW, -60_299_999, None, 17.2),
    # D 동구 무등산아이파크 84㎡. 606,009,756 × 0.7 = 424,206,829 > 한도 → 360,000,000
    #   평균가가 상품의 대상 주택 가격 상한 6억을 넘는다 (계산에서는 빼지 않는다)
    #   (606,009,756 − 360,000,000 − 50,000,000) ÷ 60 = 3,266,829.3 → 3,266,830
    ("D 한도·상한 초과", 606_009_756, 50_000_000, 1_000_000, 5, PRODUCT_HF, 30,
     360_000_000, 1_976_799, calc.LACK, 136_009_756, 3_266_830, None),
    # E 동구 해광파크 108㎡, 대출 없이 3년. 자기자금 50,000,000 + 1,500,000 × 36 = 104,000,000
    #   118,000,000 − 104,000,000 = 14,000,000 (부족). (118,000,000 − 50,000,000) ÷ 36 = 1,888,888.9 → 1,888,889
    ("E 대출 없이 3년", 118_000_000, 50_000_000, 1_500_000, 3, None, None,
     0, None, calc.LACK, 14_000_000, 1_888_889, None),
    # F 동구 라인1차 133㎡, 목표 기간 "지금", 카카오 40년. 235,000,000 × 0.7 = 164,500,000
    #   80,000,000 + 164,500,000 = 244,500,000 ≥ 235,000,000 → 지금 가능. "지금"이라 필요 월 저축액·허용 상승률 없음
    ("F 지금, 카카오 40년", 235_000_000, 80_000_000, 2_000_000, 0, PRODUCT_KAKAO, 40,
     164_500_000, 839_506, calc.NOW, -9_500_000, None, None),
    # G 동구 두산위브2차 59㎡, 보유자산 0원, 월 저축 0원, 10년, 카카오 15년
    #   333,861,111 − 0 − 233,702,777 = 100,158,334. 100,158,334 ÷ 120 = 834,652.8 → 834,653
    #   목표 가능 가격 0원 → 허용 상승률 없음
    ("G 보유 0원, 저축 0원", 333_861_111, 0, 0, 10, PRODUCT_KAKAO, 15,
     233_702_777, 1_899_640, calc.LACK, 100_158_334, 834_653, None),
    # H 동구 라인1차 84㎡, 보유자산 0원, 월 250만 원, 10년, 대출 없이. 자기자금 300,000,000
    #   (300,000,000 ÷ 165,666,667)^(1/10) − 1 = 6.11% → 6.1
    ("H 보유 0원, 대출 없이 10년", 165_666_667, 0, 2_500_000, 10, None, None,
     0, None, calc.WITHIN, -134_333_333, None, 6.1),
]


@pytest.mark.parametrize(
    "label, price, assets, saving, years, product, repay, loan_exp, pay_exp, cat_exp, short_exp, need_exp, growth_exp",
    VERIFY_CASES,
    ids=[case[0] for case in VERIFY_CASES],
)
def test_verify_table(label, price, assets, saving, years, product, repay,
                      loan_exp, pay_exp, cat_exp, short_exp, need_exp, growth_exp):
    """services/scenario.py와 같은 순서로 calc를 불러 손 계산 값과 맞춘다."""
    own = calc.own_funds(assets, calc.accumulated_saving(saving, years))
    loan = calc.loan_amount(price, product)
    short = calc.shortage(price, own, loan)

    assert loan == loan_exp
    if product is not None:
        assert calc.monthly_payment(loan, product["annual_rate_pct"], repay) == pay_exp
    assert calc.category(assets, own, loan, price, years) == cat_exp
    assert short == short_exp
    need = calc.required_monthly_saving(price, loan, assets, years) if short > 0 else None
    assert need == need_exp
    assert calc.allowed_growth_rate(calc.target_price(own, product), price, years) == growth_exp
