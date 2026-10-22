"""여러 API가 함께 쓰는 값의 범위와 검사 함수 (API 명세서 5장).

금액은 모두 원 단위 정수다. 검사에 걸리면 ValueError에 사용자에게 보여 줄 문장을 넣는다.
"""

MAX_ASSET = 10_000_000_000  # 연 소득, 현재 보유자산: 100억 원
MAX_MONTHLY_SAVING = 1_000_000_000  # 월 저축 가능액: 10억 원
TARGET_YEARS = (0, 3, 5, 10)  # 목표 기간. 0은 "지금"
MIN_AGE, MAX_AGE = 15, 100


def check_age(value: int) -> int:
    if not MIN_AGE <= value <= MAX_AGE:
        raise ValueError("만 15세부터 100세까지 입력할 수 있습니다.")
    return value


def check_asset(value: int) -> int:
    if value < 0:
        raise ValueError("0 이상의 숫자만 입력할 수 있습니다.")
    if value > MAX_ASSET:
        raise ValueError("100억 원(1,000,000만 원)까지 입력할 수 있습니다.")
    return value


def check_monthly_saving(value: int) -> int:
    if value < 0:
        raise ValueError("0 이상의 숫자만 입력할 수 있습니다.")
    if value > MAX_MONTHLY_SAVING:
        raise ValueError("10억 원(100,000만 원)까지 입력할 수 있습니다.")
    return value


def check_target_years(value: int) -> int:
    if value not in TARGET_YEARS:
        raise ValueError("목표 기간을 다시 골라 주세요.")
    return value
