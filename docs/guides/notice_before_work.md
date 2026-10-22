# 작업 전에 읽어 주세요 (10월 13일 고침)

> 2026-10-13 아침에 쓴 안내다. 그 뒤에 바뀐 것은 [notice_sync_develop.md](notice_sync_develop.md)에 있다.

| 항목 | 내용 |
| --- | --- |
| 대상 | 팀원 전원 |
| 걸리는 시간 | 읽는 데 5분, 준비하는 데 10분 |
| 달라진 것 | **DB를 SQLAlchemy로 다룬다.** 강사님의 10월 13일 수업 자료에 따라 바꿨다. |
| 오늘의 목표 | 좌표가 들어 있고, API 네 개(A-02, A-03, A-04, A-05)가 동작하고, 재무정보·대출상품·지도 화면이 각각 뜬다. |

## 1. 준비 (순서대로)

VS Code의 터미널에서, 프로젝트 폴더(`C:\projects\Money_to_Home`)에서 한다.

### 1.1 최신 내용 받기

```
git checkout develop
```

```
git pull
```

### 1.2 가상 환경 켜기

```
.venv\Scripts\activate
```

줄 맨 앞에 `(.venv)`가 붙어야 한다.

### 1.3 라이브러리 다시 설치하기

SQLAlchemy가 추가되었다. **안 하면 서버가 `ModuleNotFoundError`로 켜지지 않는다.**

```
pip install -r requirements.txt
```

"애플리케이션 제어 정책에서 이 파일을 차단했습니다"가 나오면 같은 명령을 한두 번 다시 실행한다.

### 1.4 DB 채우기

이미 했으면 건너뛴다. 여러 번 실행해도 된다.

```
python data/load_trades.py data/collected
```

```
python data/load_supply_area.py
```

"아파트 1,055곳, 거래 17,268건"이 나오면 된다.

### 1.5 확인

```
pytest
```

`44 passed`가 나오면 된다.

```
uvicorn backend.main:app --reload --port 8000
```

브라우저에서 `http://localhost:8000/api/health`를 열어 `{"status":"ok","db":"ok"}`가 나오면 준비가 끝난 것이다.

| 확인 | 기대 |
| --- | --- |
| `pytest` | 44 passed |
| `/api/health` | `"db":"ok"` |
| `http://localhost:8000` | 시작 화면. 헤더가 없고 파란 버튼이 있다. |

## 2. DB를 다루는 방법이 바뀌었다

SQL을 직접 쓰지 않고 SQLAlchemy로 다룬다. 폴더마다 하는 일이 정해져 있다 (강사님의 구조).

| 폴더 | 하는 일 | 규칙 |
| --- | --- | --- |
| `models/` | DB의 표를 옮긴 클래스. 표 하나에 클래스 하나 | **표 8개가 이미 다 있다. 새로 만들지 않는다.** |
| `schemas/` | 요청과 응답의 모양, 값의 범위 | 기능마다 파일을 만든다. |
| `services/` | DB를 읽고 쓰는 함수, 계산 | `select(...)`는 여기에만 쓴다. `commit`하지 않는다. |
| `routers/` | 주소를 받는 곳 | DB 코드와 계산식을 쓰지 않는다. `services`를 부르기만 한다. |

### 쓰는 모양

`services/` — DB에서 읽는다.

```python
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.models import Apartment


def find_in_dong(db: Session, gu: str, dong: str) -> list[Apartment]:
    return list(db.scalars(select(Apartment).where(Apartment.gu == gu, Apartment.dong == dong)).all())
```

`routers/` — 세션을 받아 넘긴다.

```python
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.services import apartment


@router.get("/apartments/{apartment_id}", response_model=ApartmentOut)
def get_apartment(apartment_id: int, db: Session = Depends(get_db)):
    return apartment.find_by_id(db, apartment_id)
```

`schemas/` — 모델의 객체를 그대로 돌려주려면 이 한 줄을 넣는다.

```python
from pydantic import BaseModel, ConfigDict


class ApartmentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
```

### 본보기

새 API를 만들 때 아래 네 파일을 열어 같은 모양으로 만든다.

| 파일 | 볼 것 |
| --- | --- |
| `backend/services/profile.py` | DB에서 읽고, 없으면 만들고, 고치는 방법 |
| `backend/routers/profile.py` | 세션을 받아 서비스에 넘기는 방법 |
| `backend/schemas/profile.py` | 입력 검사와 응답의 모양 |
| `tests/test_profile.py` | 테스트 쓰는 방법 |

### 알아 둘 것

- 표는 여전히 `db/schema.sql`로 만든다. 표나 칸을 바꾸려면 팀장에게 말한다.
- 아파트의 면적대별 평균가는 `apartment.prices`로 읽는다. 평균가가 낮은 순으로 온다.
- 계산 함수에 대출 상품을 넘길 때는 `loan_product.for_calc(상품)`으로 바꿔 넘긴다. 대출 없이 계산이면 `None`을 넘긴다.
- 저장한 직후의 값이 필요하면 `db.flush()`와 `db.refresh(객체)`를 쓴다.
- 테스트는 MariaDB 없이 임시 DB로 돈다. `db`, `products`, `client` 픽스처가 `tests/conftest.py`에 있다.
- `data/` 폴더의 수집·적재 스크립트는 SQL을 직접 써도 된다. 한 번 돌리는 것이라 그대로 둔다.

## 3. 정해진 것

| 항목 | 내용 |
| --- | --- |
| DB | SQLAlchemy로 다룬다. |
| 헤더 | 모바일에는 없다. 입력 화면은 맨 위에 `<div class="top-space"></div>`를 둔다. 지도 화면의 맨 위는 내 조건 줄이다. |
| 지도의 표시 | 말풍선 A(그라데이션). 면적과 실거래 평균가만 적는다. 여유·부족 금액은 누르면 아래 창에 나온다. |
| 범례 | 처음부터 펼쳐 둔다. |
| 색 | 팔레트 F 라임. 지금 가능은 파랑, 기간 내 가능은 라임, 자금 부족은 빨강. `common.css`에 들어 있다. |
| 지역 이름 | "광주시"가 아니라 "광주 5개 구"라고 쓴다. 지역 코드는 12로 시작하는 새 코드를 쓴다. |
| 발표 | 팀장의 노트북으로 한다. |

## 4. 화면을 만들 때

- 모양은 Figma "확정 목업 v3"을 따른다. 링크는 `CLAUDE.md`와 README에 있다.
- Claude에는 **화면 하나의 링크**만 준다. Figma에서 프레임을 고르고 "Copy link to selection"으로 받는다.
- 색과 글자 크기는 `common.css`의 이름을 쓴다. 값을 직접 적지 않는다.

```html
<div class="top-space"></div>
<button class="button button--primary">다음</button>
<span class="badge badge--within">기간 내 가능</span>
```

- 본보기는 `frontend/index.html`이다. `<head>`와 `<script>` 줄을 그대로 복사해 시작한다.
- API가 아직 없으면 API 명세서의 예시 응답을 코드에 임시로 적어 두고 화면을 먼저 만든다.

## 5. 지킬 것

| 규칙 | 이유 |
| --- | --- |
| 자기 담당 파일만 고친다. `models/`는 팀장의 파일이다. | 합칠 때 충돌하지 않는다. |
| 계산식은 `services/calc.py`에만 둔다. | 화면마다 숫자가 달라지지 않는다. |
| router에 DB 코드를 쓰지 않는다. | 강사님의 구조다. 테스트하기도 쉽다. |
| 저장소 값은 `store.set`, 서버 호출은 `api.get`·`api.post`만 쓴다. | 화면끼리 값이 이어진다. |
| 금액은 원 단위 정수로 주고받는다. | 만원과 섞이면 10,000배 틀린다. |
| `git add .`을 쓰지 않는다. 파일 이름을 적어 담는다. | `.env`가 올라가지 않는다. |
| PR은 기능 하나가 되면 바로 올린다. base는 `develop` | 작을수록 검토가 빠르다. |
| PR을 올리기 전에 `pytest`를 돌린다. | 남의 것을 깨뜨리지 않았는지 본다. |
| 합쳐지면 단체방에 알린다. 알림을 보면 `git pull` 한다. | 서로 다른 코드로 일하지 않는다. |

`requirements.txt`가 바뀌었다는 알림을 받으면 `pip install -r requirements.txt`를 다시 한다.

## 6. 각자 할 일

| 담당 | 순서 | 만들 파일 |
| --- | --- | --- |
| 김해원 | 재무정보 화면 → 저축 계산 API (A-04) → 저축 계획 화면 → PR 검토 | `profile.html`, `routers/plans.py`, `plan.html` |
| 박채은 | **대출 상품 조사** → 대출 계산 API (A-03) → 대출상품 화면 → 시나리오 API (A-07) | `db/seed_loan_products.sql`, `routers/loans.py`, `schemas/loan.py`, `loan.html` |
| 김목산 | 수집 기간 정하기 → 구와 동 API (A-02) → **아파트 찾기 API (A-05)** → 목록 화면 | `services/apartment.py`, `schemas/apartment.py`, `routers/apartments.py`, `list.js` |
| 안세환 | **좌표 변환** → 지도 틀 → 말풍선 표시 → 아래 창 → 아파트 한 곳 API (A-06) | `data/geocode.py`, `map.html`, `services/apartment_detail.py`, `schemas/apartment_detail.py` |

가이드: 채은님 `loan_research.md`, 목산님 `guide_moksan.md`, 세환님 `guide_sehwan.md`

한마디씩

- **채은님**: 공식 안내 페이지에서만 가져오고 출처 주소를 꼭 적는다. 테스트의 숫자는 고치지 않는다. 대출 계산 API는 DB에서 상품을 읽어 `for_calc`로 바꾼 뒤 계산 함수에 넘긴다.
- **목산님**: `models/`는 만들지 않는다. `services/apartment.py`부터 만든다. 개수는 아파트 단위로 세고, 좌표가 없는 아파트도 결과에서 빼지 않는다.
- **세환님**: 주소 형식을 3 ~ 5건으로 먼저 시험한다. 전체를 돌리기 전에 단체방에 알린다. 지도 틀은 빈 자리만 있어도 먼저 올린다.

## 7. 서로 맞춰야 하는 것

| 맞출 것 | 누가 정하는가 | 누가 쓰는가 |
| --- | --- | --- |
| 아래 창의 빈 자리 이름 (id) | 세환님이 정해 단체방에 알린다. | 목산님, 채은님 |
| 고른 아파트를 담는 곳 (`map-state.js`) | 세환님 | 목산님, 채은님 |
| 저장소에 넣는 값의 이름 | 이미 정해져 있다 (`store.js`). | 팀장, 채은님, 세환님 |
| 아파트 찾기 API의 응답 모양 | 이미 정해져 있다 (API 명세서 A-05). | 목산님이 만들고 세환님이 쓴다. |

모양을 바꿔야 하면 혼자 바꾸지 않는다. 문서를 먼저 고치고 단체방에 알린다.

## 8. 서로 기다리는 순서

```
세환: 좌표 변환 ─→ 지도에 실제 아파트
세환: 지도 틀   ─→ 목산: 목록 화면, 채은: 시나리오 탭
목산: A-05      ─→ 세환: 말풍선의 색, 목산: 목록
```

기다리는 동안 할 일이 각자 있다. API와 조사는 누구도 기다리지 않는다.

## 9. 막히면

| 상황 | 할 일 |
| --- | --- |
| `ModuleNotFoundError: No module named 'sqlalchemy'` | 가상 환경을 켜고 `pip install -r requirements.txt`를 한다. |
| `/api/health`가 `"db":"error"` | `.env`의 `DB_USER`와 `DB_PASSWORD`를 본다. 고친 뒤 서버를 껐다 켠다. |
| `pytest`가 실패한다. | 자기가 고친 것 때문인지 본다. 아니면 화면을 캡처해 올린다. |
| 30분 넘게 막힌다. | 화면을 캡처해 단체방에 올린다. 혼자 오래 붙잡지 않는다. |
| `git status`에 `.env`가 보인다. | 아무것도 하지 말고 팀장에게 알린다. |
| `CONFLICT`가 나온다. | 혼자 풀지 말고 그 파일의 담당과 같이 본다. |
| 표나 칸을 바꿔야 한다. | 팀장에게 말한다. `db/schema.sql`과 `models/`를 함께 고쳐야 한다. |
| 계산 결과가 예시와 다르다. | 계산 함수를 고치지 말고 채은님에게 알린다. |
