"""계산 모듈. 담당: 박채은

계산 규칙 C-01 ~ C-13을 이 파일에만 둔다 (NFR-13).
router와 화면에는 계산식을 쓰지 않고 이 파일의 함수를 부른다.

규칙
- 금액은 원 단위 정수로 받고 돌려준다 (NFR-12).
- 대출금액은 버림, 월 상환액은 반올림, 필요 월 저축액은 올림 (요구사항 명세서 부록 C).
- DB와 요청을 모른다. 숫자를 받아 숫자를 돌려준다. 그래서 DB 없이 테스트할 수 있다.
- 함수마다 tests/test_calc.py에 테스트를 붙인다.

만들 함수는 docs/06_architecture.md 4.3의 표에 있다. 이름과 받는 값은 그 표를 따른다.

    accumulated_saving       C-02       누적 저축액
    own_funds                C-03       목표 시점 자기자금
    loan_amount              C-05, C-13 예상 대출금액
    max_loan_amount          C-06       최대 예상 대출금액
    monthly_payment          C-07       예상 월 상환액
    target_price             C-08, C-13 목표 가능 가격
    category                 C-09       now, within, lack
    shortage                 C-10       부족자금. 음수면 여유자금
    required_monthly_saving  C-11       필요 월 저축액 또는 None
    allowed_growth_rate      C-12       허용 상승률 또는 None
"""
from decimal import ROUND_CEILING, ROUND_FLOOR, ROUND_HALF_UP, Decimal, localcontext

# 지금 가능, 기간 내 가능, 자금 부족. DB와 API의 값과 같다 (API 명세서 2장).
NOW = "now"
WITHIN = "within"
LACK = "lack"


def _dec(value) -> Decimal:
    """float로 온 비율과 금리를 Decimal로 바꾼다. 0.7이 0.69999...가 되지 않게 글자를 거친다."""
    return Decimal(str(value))


def _floor(value: Decimal) -> int:
    """원 미만을 버린다."""
    return int(value.to_integral_value(rounding=ROUND_FLOOR))


def accumulated_saving(monthly_saving: int, target_years: int) -> int:
    """C-02 누적 저축액 = 월 저축 가능액 × 12 × 목표 연수.

    목표 기간 "지금"은 0년이며 0원이다.
    """
    return monthly_saving * 12 * target_years


def own_funds(current_assets: int, accumulated: int) -> int:
    """C-03 목표 시점 자기자금 = 현재 보유자산 + 누적 저축액."""
    return current_assets + accumulated


def loan_amount(price: int, product: dict | None) -> int:
    """C-05 예상 대출금액(아파트 기준) = min(상품 최대 한도, 평균가 × 대출 비율).

    원 미만은 버린다.
    product는 대출 상품(max_limit, ltv_ratio). None이면 대출 없이 계산이라 0원이다 (C-13).
    """
    if product is None:
        return 0
    return min(product["max_limit"], _floor(Decimal(price) * _dec(product["ltv_ratio"])))


def max_loan_amount(current_assets: int, product: dict | None) -> int:
    """C-06 최대 예상 대출금액(아파트 선택 전)
    = min(상품 최대 한도, 현재 보유자산 × 대출 비율 ÷ (1 − 대출 비율)).

    대출 비율이 1이면 상품 최대 한도로 한다. 원 미만은 버린다.
    보유자산이 0원이면 0원이다. 오류가 아니다.
    product가 None이면 대출 없이 계산이라 0원이다 (C-13).
    """
    if product is None:
        return 0
    ratio = _dec(product["ltv_ratio"])
    if ratio == 1:
        return product["max_limit"]
    return min(product["max_limit"], _floor(Decimal(current_assets) * ratio / (1 - ratio)))


def monthly_payment(amount: int, annual_rate_pct: float, repayment_years: int) -> int:
    """C-07 예상 월 상환액. 원리금균등 상환.

    대출금액 × m × (1+m)^N ÷ ((1+m)^N − 1)
    m은 연 금리 ÷ 12, N은 상환 연수 × 12.
    annual_rate_pct는 연 % 값이다 (연 4.0%면 4.0. loan_products.annual_rate_pct와 같다).
    금리가 0이면 대출금액 ÷ N. 원 단위로 반올림한다.
    대출 없이 계산(C-13)이면 이 함수를 부르지 않는다.
    """
    months = repayment_years * 12
    with localcontext() as ctx:
        ctx.prec = 50
        m = _dec(annual_rate_pct) / 100 / 12
        if m == 0:
            payment = Decimal(amount) / months
        else:
            growth = (1 + m) ** months
            payment = Decimal(amount) * m * growth / (growth - 1)
        return int(payment.to_integral_value(rounding=ROUND_HALF_UP))


def target_price(own: int, product: dict | None) -> int:
    """C-08 목표 가능 가격 = min(자기자금 + 상품 최대 한도, 자기자금 ÷ (1 − 대출 비율)).

    자기자금은 "지금"이면 현재 보유자산, 그 외에는 C-03을 넣는다.
    대출 비율이 1이면 자기자금 + 상품 최대 한도로 한다. 원 미만은 버린다.
    product가 None이면 대출 없이 계산이라 자기자금과 같다 (C-13).
    """
    if product is None:
        return own
    with_limit = own + product["max_limit"]
    ratio = _dec(product["ltv_ratio"])
    if ratio == 1:
        return with_limit
    return min(with_limit, _floor(Decimal(own) / (1 - ratio)))


def category(current_assets: int, own: int, loan: int, price: int, target_years: int) -> str:
    """C-09 3단계 구분.

    지금 가능(now): 현재 보유자산 + C-05 ≥ 평균가
    기간 내 가능(within): 지금 가능이 아니고 C-03 + C-05 ≥ 평균가
    자금 부족(lack): 그 외
    목표 기간이 "지금"(0년)이면 within은 나오지 않는다.
    대출 없이 계산(C-13)이면 loan에 0을 넣는다.
    """
    if current_assets + loan >= price:
        return NOW
    if target_years > 0 and own + loan >= price:
        return WITHIN
    return LACK


def shortage(price: int, own: int, loan: int) -> int:
    """C-10 부족자금 = 평균가 − C-03 − C-05.

    음수면 그 절댓값이 여유자금이다.
    대출 없이 계산(C-13)이면 loan에 0을 넣는다.
    """
    return price - own - loan


def required_monthly_saving(
    price: int, loan: int, current_assets: int, target_years: int
) -> int | None:
    """C-11 필요 월 저축액 = (평균가 − C-05 − 현재 보유자산) ÷ (12 × 목표 연수).

    원 단위로 올린다.
    목표 기간이 "지금"(0년)이거나 값이 0 이하이면 None이다.
    ※ C-11은 부족자금(C-10)이 0보다 클 때만 표시한다. 이 함수는 월 저축 가능액을 받지 않으므로,
      부르는 쪽이 shortage()가 0 이하이면 None으로 둔다 (API 명세서 A-07).
    대출 없이 계산(C-13)이면 loan에 0을 넣는다.
    """
    if target_years <= 0:
        return None
    need = price - loan - current_assets
    if need <= 0:
        return None
    value = Decimal(need) / (12 * target_years)
    return int(value.to_integral_value(rounding=ROUND_CEILING))


def allowed_growth_rate(target: int, price: int, target_years: int) -> float | None:
    """C-12 허용 상승률 = (목표 시점 자기자금으로 구한 C-08 ÷ 평균가)^(1 ÷ 목표 연수) − 1.

    연 %로 돌려준다 (4.09...%면 4.0). 소수 첫째 자리까지 두고 그 아래는 버린다.
    목표 기간이 "지금"(0년)이거나 결과가 음수면 None이다.
    target에는 target_price(목표 시점 자기자금, 상품)의 값을 넣는다.
    """
    if target_years <= 0:
        return None
    with localcontext() as ctx:
        ctx.prec = 50
        ratio = Decimal(target) / Decimal(price)
        # Decimal의 ** 는 소수 지수도 계산한다. 결과를 % 단위로 바꾼다.
        rate_pct = (ratio ** (Decimal(1) / target_years) - 1) * 100
        if rate_pct < 0:
            return None
        return float(rate_pct.quantize(Decimal("0.1"), rounding=ROUND_FLOOR))
