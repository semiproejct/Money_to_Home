# 목산님 가이드 — 자료와 탐색

> 2026-10-13 아침에 쓴 가이드다. 1번(A-02)은 끝났다. 표의 건수는 그때의 값이다.

| 항목 | 내용 |
| --- | --- |
| 담당 | 김목산 |
| 지금까지 | 수집, 적재, 공급면적 붙이기 스크립트 완료 (PR #18 합쳐짐). DB에 아파트 1,055곳, 거래 17,268건, 평균가 1,855줄 |
| 이번 목표 | 구와 동 목록 API, 아파트 찾기 API, 목록 화면 |
| 기준 | `docs/05_api_spec.md`의 A-02와 A-05, `CLAUDE.md`, Figma "확정 목업 v3"의 P-06 ⑤ |

## 순서

| 순서 | 할 일 | 끝난 기준 |
| --- | --- | --- |
| 0 | 수집 기간을 12개월로 맞출지 팀장과 정한다. | 5분. 아래 "먼저 정할 것" |
| 1 | 구와 동 목록 API (A-02) | `/docs`에서 5개 구와 동이 나온다. |
| 2 | 아파트 찾기 API (A-05) | 조건을 보내면 아파트 목록, 구분, 개수가 온다. |
| 3 | 목록 화면 (`list.js`, `list.css`) | 세환의 `map.html` 빈 자리에 카드가 뜬다. |
| 4 | 조건과 정렬 (2차) | 1차가 끝난 뒤 |

기능 하나가 되면 바로 PR을 올린다. 1번과 2번을 한 PR에 묶지 않는다.

## 정해진 것: 기간

수집과 평균의 기간은 같다. **수집을 실행한 달의 전월까지 12개월**이다 (2026-10-13에 정함).
10월에 수집하면 2025-10-01 ~ 2026-09-30이다. 화면에는 "최근 1년 실거래 평균"이라고 적는다.

문서의 건수(아파트 1,054곳, 거래 16,919건)는 CSV 기준이다. API로 받은 실제 건수와 달라도 문서를 고치지 않는다.

## 1. 구와 동 목록 API (A-02)

`GET /api/regions`

만들 파일

| 파일 | 내용 |
| --- | --- |
| `backend/services/apartment.py` (새 파일) | DB에서 구와 동, 아파트를 읽는 함수 |
| `backend/schemas/apartment.py` (새 파일) | 요청과 응답의 모양 |
| `backend/routers/apartments.py` | 주소를 받는다. 지금은 비어 있다. |

**`models/`는 만들지 않는다.** 표 8개의 클래스가 이미 있다 (`Apartment`, `ApartmentPrice`, `Trade` 등). 가져다 쓰기만 한다.

```python
from sqlalchemy import select
from backend.models import Apartment, ApartmentPrice

def find_in_dong(db, gu, dong):
    return list(db.scalars(select(Apartment).where(Apartment.gu == gu, Apartment.dong == dong)).all())

# 아파트의 면적대별 평균가는 apartment.prices로 읽는다. 평균가가 낮은 순이다.
```

본보기는 `services/profile.py`, `routers/profile.py`, `tests/test_profile.py`다.

응답의 모양

```json
{
  "regions": [
    {
      "gu": "서구",
      "latitude": 35.1520,
      "longitude": 126.8900,
      "dongs": [
        { "dong": "치평동", "apartment_count": 23, "latitude": 35.1490, "longitude": 126.8450 }
      ]
    }
  ]
}
```

규칙

- 평균가(`apartment_prices`)가 있는 아파트가 한 곳이라도 있는 구와 동만 낸다.
- 위치는 그 구나 동에 있는 아파트 좌표의 평균이다. **좌표가 아직 없으면 `null`이다.** 세환의 좌표 변환이 끝나기 전에는 전부 `null`로 나오는 것이 맞다.
- 구의 순서와 동의 순서를 정해 적는다 (가나다순을 권한다).

## 2. 아파트 찾기 API (A-05)

`POST /api/apartments/search`

지도와 목록이 함께 쓰는 가장 중요한 API다. 세환의 말풍선 색도 이 API의 구분으로 정해진다.

### 1차에 만들 범위

| 받는 값 | 1차 | 2차 |
| --- | --- | --- |
| `conditions` | 만든다 | |
| `where: { gu, dong }` | 만든다. `dong`을 빼면 구 전체 | |
| `where: { bounds }`, `{ keyword }` | | 나중에 |
| `filters`, `sort` | 받되 쓰지 않는다 (`sort`는 `category`로 고정) | 나중에 |

### 하는 일의 순서

```
1. schemas로 요청을 검사한다. 틀리면 422
2. loan_choice가 product면 loan_products에서 상품 한 줄을 읽는다. none이면 상품이 없다.
3. 그 구와 동의 아파트와 면적대별 평균가를 읽는다.
4. 면적마다 계산 함수를 불러 대출금액, 구분, 부족자금을 구한다.
5. 아파트의 구분을 정하고, 줄 세우고, 개수를 센다.
6. 응답을 만든다.
```

### 계산은 채은의 함수를 부른다

`backend/services/calc.py`에 다 있다. **계산식을 이 파일에 새로 쓰지 않는다.**

```python
from backend.services import calc, loan_product

product = loan_product.for_calc(loan_product.find_by_id(db, loan_product_id))   # 대출 없이 계산이면 None

saved = calc.accumulated_saving(monthly_saving, target_years)
own = calc.own_funds(current_assets, saved)                 # 목표 시점 자기자금
target = calc.target_price(own, product)                    # 목표 가능 가격

# 면적마다
loan = calc.loan_amount(avg_price, product)                 # product가 None이면 0
category = calc.category(current_assets, own, loan, avg_price, target_years)
shortage = calc.shortage(avg_price, own, loan)              # 음수면 여유자금
```

- 계산 함수에는 상품 객체를 그대로 넘기지 않는다. `loan_product.for_calc(상품)`으로 바꿔 넘긴다. 대출 없이 계산이면 `None`을 넘긴다.
- 목표 기간이 "지금"(0)일 때 목표 가능 가격의 자기자금은 현재 보유자산이다. `own_funds`의 결과가 그 값과 같으므로 따로 처리하지 않아도 된다.

### 응답에서 틀리기 쉬운 곳

| 값 | 규칙 |
| --- | --- |
| `apartments[].areas` | 평균가가 낮은 순. **첫째 것이 지도의 표시와 카드에 먼저 보이는 면적이다.** |
| `apartments[].category` | 아파트의 구분. `areas`의 첫째(가장 싼 면적)의 구분과 같다. |
| `counts` | **아파트 단위**로 센다. 면적 단위가 아니다. |
| 순서 | 지금 가능 → 기간 내 가능 → 자금 부족. 같은 구분 안에서는 평균가가 목표 가능 가격에 가까운 순 |
| `over_price_cap` | 평균가가 상품의 `max_house_price`를 넘으면 `true`. 상한이 없거나 대출 없이 계산이면 `false` |
| `latitude`, `longitude` | 좌표가 없으면 `null`. 결과에서 빼지 않는다. |
| `households` | 세대수는 아직 없다. `null`로 준다. |
| 결과 없음 | `apartments`를 빈 목록으로 준다. 오류가 아니다. |
| 자금 부족 | 빼지 않고 항상 준다. 끄고 켜는 것은 화면이 한다. |

### 지킬 것

- **요청에 든 값만 쓴다.** 로그인 정보와 `profiles` 표를 읽지 않는다 (NFR-18).
- 금액은 원 단위 정수다. 면적은 `schemas`에서 `float`로 적으면 알아서 바뀐다.
- **DB는 SQLAlchemy로 다룬다.** `select(...)`는 `services/apartment.py`에만 쓰고, router에는 쓰지 않는다. SQL 문장을 글자로 이어 붙이지 않는다.
- `services`에서 `commit`하지 않는다.
- 응답의 `schemas` 클래스에 `model_config = ConfigDict(from_attributes=True)`를 둔다.
- 오류는 `backend.errors.ApiError`로 낸다. 없는 상품 번호면 422다.

### 확인

`/docs`에서 아래를 보내 본다.

```json
{
  "conditions": {
    "current_assets": 50000000, "monthly_saving": 1000000, "target_years": 5,
    "loan_choice": "product", "loan_product_id": 1, "repayment_years": 30
  },
  "where": { "gu": "서구", "dong": "치평동" }
}
```

| 확인 | 기대 |
| --- | --- |
| `target_price` | 366666666 |
| `own_funds` | 110000000 |
| 평균가 3억 원 안팎의 면적 | `category`가 `within`, `shortage`가 음수 |
| `counts.total` | `apartments`의 길이와 같다. |
| `target_years`를 0으로 | `within`이 하나도 없다. |
| `loan_choice`를 `none`으로 | `loan_amount`가 전부 0, `target_price`가 `own_funds`와 같다. |
| 없는 동 이름 | 빈 목록. 오류가 아니다. |

테스트(`tests/test_apartments.py`)를 함께 올린다. 테스트는 MariaDB 없이 임시 DB로 돈다. `db` 픽스처에 아파트와 평균가 몇 줄을 넣고 확인한다. 본보기는 `tests/conftest.py`의 `products`와 `tests/test_profile.py`다.

## 3. 목록 화면

| 파일 | 내용 |
| --- | --- |
| `frontend/js/list.js` | 목록을 그린다. |
| `frontend/css/list.css` | 목록의 모양 |

- `map.html`은 세환의 파일이다. **고치지 않는다.** 세환이 만든 빈 자리(요소의 id)에 목록을 그려 넣는다. id는 세환이 정해 알려 준다.
- 모양은 Figma "확정 목업 v3"의 **P-06 ⑤ 목록 80%**를 따른다. 화면 하나의 링크를 Claude에 준다.
- 서버는 `api.post('/api/apartments/search', {...})`로 부른다. 조건은 `guard.conditions()`가 만들어 준다.
- 금액은 `format.won()`, 면적은 `format.area()`로 보여 준다.
- 색과 배지는 `common.css`의 것을 쓴다: `badge badge--now`, `badge--within`, `badge--lack`, `chip chip--now` 등.
- 서버에서 온 글자(아파트명 등)는 `textContent`로 넣는다. `innerHTML`을 쓰지 않는다.
- API가 아직 없을 때는 명세서의 예시 응답을 코드에 임시로 적어 두고 화면을 먼저 만든다.

목록에 보여 줄 것 (목업 기준)

| 자리 | 내용 |
| --- | --- |
| 머리 | "서구 치평동 · 23곳", 안내 아이콘, 닫기 |
| 개수 칩 | 지금 5, 기간 내 4, 부족 14 |
| 묶음 제목 | "지금 목표할 수 있는 곳 · 5" 등 |
| 카드 | 아파트명, 구분 배지, "111㎡ (전용 84㎡) · 거래 14건", "평균 3억 원 · 여유 2,000만 원" |
| 좌표가 없는 아파트 | "위치 없음" 표시 |

## 막히면

| 상황 | 할 일 |
| --- | --- |
| 계산 결과가 예시와 다르다. | 계산 함수를 고치지 말고 채은에게 알린다. |
| 응답의 모양을 바꾸고 싶다. | 명세서를 먼저 고치고 팀에 알린다. 세환의 지도가 같은 응답을 쓴다. |
| 좌표가 전부 `null`이다. | 정상이다. 세환의 좌표 변환이 끝나면 채워진다. |
| 30분 넘게 막힌다. | 화면을 캡처해 팀장에게 보낸다. |
