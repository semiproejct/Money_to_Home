# 머니 to 홈 — AI 도구에 주는 규칙

이 파일은 Claude 같은 AI 도구가 이 프로젝트에서 일할 때 먼저 읽는 규칙이다. 네 명이 같은 규칙으로 AI를 쓰면 결과물의 모양이 같아진다. 사람이 읽어도 된다.

## 프로젝트

광주 5개 구 아파트의 내 집 마련 시뮬레이터. 보유자산, 저축 계획, 대출 상품으로 목표할 수 있는 아파트를 지도에 보여 준다. 4명이 2주 동안 만드는 수업 프로젝트다.

- 서버: Python 3.12, FastAPI, SQLAlchemy 2 (접속은 PyMySQL)
- DB: MariaDB 11.4
- 화면: HTML, CSS, JavaScript. Bootstrap, Sass, React 같은 라이브러리와 프레임워크를 쓰지 않는다. 모양은 `css/common.css`와 화면별 CSS로 만든다.
- 지도: 카카오맵 JavaScript SDK

## 지역 이름과 코드

**광주 5개 구**는 전남광주통합특별시의 동구, 서구, 남구, 북구, 광산구다. 2026-07-01에 광주광역시와 전라남도가 전남광주통합특별시로 합쳐지기 전의 광주광역시와 같은 범위다.

- 문서와 화면에 "광주광역시", "광주시"라고 쓰지 않는다. "광주 5개 구"라고 쓰고, 주소에는 "전남광주통합특별시 서구 치평동"처럼 쓴다.
- **29로 시작하는 옛 지역 코드를 쓰지 않는다.** 실거래가 API가 오류 없이 0건으로 답한다. 아래 코드를 쓴다 (2026-10-12에 API로 확인).
- 실거래 CSV(`data/아파트_실거래가_정렬.csv`)에는 전남의 시와 군이 섞여 있다. 광주 5개 구만 골라 쓴다.
- **실거래는 지난달까지 12개월을 수집하고, 그 12개월로 보여 준다.** 수집과 평균의 기간이 같다. 수집을 실행한 달의 전월까지 12개월이다 (10월에 실행하면 전년 10월 1일 ~ 올해 9월 30일). 평균가, 가격 범위, 거래 건수는 이 기간의 거래로 계산하고 화면에는 "최근 1년"으로 적는다. 이 기간 밖의 거래가 DB에 있어도 평균에는 쓰지 않는다.
- 문서의 자료 건수(아파트 1,054곳, 거래 16,919건 등)는 CSV 기준이다. API로 받은 실제 건수와 달라도 문서를 고치지 않는다.

| 구 | 시군구 코드 (`LAWD_CD`) | 옛 코드 (쓰지 않는다) |
| --- | --- | --- |
| 동구 | 12210 | 29110 |
| 서구 | 12240 | 29140 |
| 남구 | 12270 | 29155 |
| 북구 | 12300 | 29170 |
| 광산구 | 12330 | 29200 |

## 먼저 읽을 문서

일을 시작하기 전에 관련된 문서를 읽는다. 문서와 다르게 만들지 않는다.

| 알고 싶은 것 | 문서 |
| --- | --- |
| 전체 요약 | `docs/00_summary.md` |
| 무엇을 만드는가, 계산 규칙 C-01 ~ C-13 | `docs/02_requirements.md` |
| 화면의 동작과 문구 | `docs/03_ui_design.md`, `docs/03_ui_design_wireframe.md` |
| 표와 칸 | `docs/04_database_design.md`, `db/schema.sql` |
| API의 주소, 요청, 응답 | `docs/05_api_spec.md` |
| 폴더 구조 | `docs/06_architecture.md` |
| 누가 무엇을 어떤 순서로 하는가 | `docs/roles.md` |
| Git 사용법 | `docs/git_rule.md` |

## 반드시 지킬 것

1. **요구사항에 없는 기능을 만들지 않는다.** 필요해 보여도 먼저 묻는다.
2. **계산식은 `backend/services/calc.py`에만 둔다.** router와 JavaScript에 계산식을 쓰지 않는다. 화면은 서버가 준 숫자를 보여 주기만 한다.
3. **금액은 원 단위 정수다.** API의 요청과 응답, DB, 브라우저 저장소 모두 같다. 만원은 화면에서 보여 줄 때만 쓴다.
4. **API의 모양은 `docs/05_api_spec.md`를 따른다.** 주소, 이름, 형식을 바꾸려면 명세서를 먼저 고치고 팀에 알린다.
5. **DB는 SQLAlchemy로 다룬다.** `select(Model).where(...)`처럼 쓴다. SQL 문장을 글자로 이어 붙이지 않는다. 꼭 SQL을 직접 써야 하면 `text("... :name")`과 매개변수로 넘기고, f-string으로 값을 넣지 않는다.
6. **오류 응답은 `{"detail": "...", "field": "..."}` 한 모양이다.** router에서는 `backend.errors.ApiError`를 낸다. 내부 정보(SQL, 경로)를 응답에 넣지 않는다.
7. **키와 비밀번호를 코드에 적지 않는다.** `.env`에만 두고 `backend.config.settings`로 읽는다. `.env`의 값을 출력하거나 문서에 적지 않는다.
8. **주민등록번호를 저장하거나 서버에 보내지 않는다.** 화면에서 만 나이를 계산하는 데만 쓴다. 실명, 연락처, 계좌번호, 주소, 위치도 모으지 않는다.
9. **요청을 처리하는 중에 외부 API를 부르지 않는다.** 실거래가, 좌표, 주변 시설은 `data/`의 스크립트가 미리 DB에 넣는다 (주변 시설은 `data/load_facilities.py`, 2026-10-19). 화면도 카카오 장소 검색(`libraries=services`)을 쓰지 않는다.
10. **계산과 탐색 API는 요청에 든 값만 쓴다.** 로그인 정보와 `profiles` 표를 읽지 않는다.
11. **서버나 DB에서 온 글자를 화면에 넣을 때 `textContent`를 쓴다.** `innerHTML`에 넣지 않는다.
12. **쓰지 않는 말**: "구매 가능", "승인", "추천", "10년 후 집값". 대신 "지금 가능", "기간 내 가능", "자금 부족"을 쓴다.

## Figma 목업

- 파일: https://www.figma.com/design/TSra3U9pIFYKxXvSNS4pu7/money-to-home-mockup
- 기준 섹션: [확정 목업 v3](https://www.figma.com/design/TSra3U9pIFYKxXvSNS4pu7/money-to-home-mockup?node-id=2034-2). 이 섹션의 화면을 보고 구현한다. 그 위쪽의 화면은 예전 것이라 따르지 않는다.
- **새 스타일 (2026-10-18 ~ 19)**: 사본 파일 [money-to-home-mockup (복사)](https://www.figma.com/design/JKGSjtSMUR9UrTIHWXyUe9)의 목업 v2 페이지에서 설명 글자가 "새로운 스타일(맵 적용용)"(프레임 2038:98), "새로운 스타일(전체 적용용)"(프레임 6013:2048)인 화면. v3와 다르면 이것을 따른다. 모양은 `frontend/css/new-style.css` 한 파일이 다른 CSS 뒤에 읽혀 덮어쓴다.
- 화면을 읽을 때는 파일 전체가 아니라 **프레임 하나의 링크**를 쓴다. Figma에서 프레임을 고르고 "Copy link to selection"으로 받는다. 파일 전체나 섹션을 통째로 읽으면 범위가 커서 제대로 읽지 못한다.
- 색, 글자 크기, 버튼, 입력란 같은 공통 값은 `frontend/css/common.css`에 있는 이름을 먼저 쓴다. 거기 없는 값만 Figma에서 읽는다. Figma를 읽는 횟수에는 한도가 있다.
- 목업에 없는 상태는 지어내지 말고 가장 가까운 화면을 따른 뒤, 무엇을 그렇게 했는지 알린다.
- Figma를 열 수 없으면 `docs/mockups/`의 PNG를 본다. 화면마다 한 장이고 목록은 `docs/mockups/README.md`에 있다 (2026-10-13에 내보낸 사본. 기준은 Figma다).

## 담당

자기 담당 파일만 고친다. 남의 파일을 고쳐야 하면 고치지 말고 그 담당에게 알릴 내용을 적어 준다.

| 담당 | 파일 |
| --- | --- |
| 김해원 (입력과 공통) | `backend/main.py`, `config.py`, `database.py`, `deps.py`, `errors.py`, `routers/profile.py`, `routers/plans.py`, `routers/system.py`, `models/`의 열 파일, `services/profile.py`, `schemas/common.py`, `schemas/profile.py`, `schemas/plan.py`, `frontend/index.html`, `profile.html`, `plan.html`, `css/common.css`, `css/region.css`, `css/new-style.css`, `css/scenario-charts.css`, `js/api.js`, `store.js`, `format.js`, `guard.js`, `layout.js`, `js/region.js`, `js/scenario-charts.js` |
| 박채은 (대출과 계산) | `backend/services/calc.py`, `routers/loans.py`, `routers/scenario.py`, `services/loan_product.py`, `schemas/loan.py`, `tests/test_calc.py`, `db/seed_loan_products.sql`, `frontend/loan.html`, `js/loan.js`, `css/loan.css`, `js/scenario.js`, `css/scenario.css`, `js/splash.js`, `img/logo.svg`, `img/logo-splash.svg` |
| 김목산 (자료와 탐색) | `backend/routers/apartments.py`, `services/apartment.py`, `schemas/apartment.py`, `data/collect_trades.py`, `data/load_trades.py`, `frontend/js/list.js`, `css/list.css`, `frontend/share.html`, `js/share.js`, `js/share-page.js`, `css/share.css`, `css/share-page.css` |
| 안세환 (지도와 아파트 창) | `backend/routers/apartment_detail.py`, `services/apartment_detail.py`, `schemas/apartment_detail.py`, `data/geocode.py`, `data/geocoded.csv`, `data/load_facilities.py`, `data/facilities.csv`, `frontend/map.html`, `js/map-view.js`, `sheet.js`, `apartment.js`, 지도와 아래 창의 CSS |

네 명 모두 화면, 서버, DB를 다 쓴다. 기능 하나를 화면부터 DB까지 한 사람이 맡는다. 순서는 `docs/roles.md`에 있다.

- `backend/main.py`에는 새 router를 등록하는 한 줄만 더한다.
- `frontend/map.html`은 안세환이 틀과 빈 자리를 만든다. 목록(김목산)과 시나리오 탭(박채은)은 각자의 JavaScript와 CSS 파일에서 만든다.

## 코드를 쓰는 방법

### 서버

- 층을 지킨다 (강사님의 구조).
  - `models/` : DB의 표를 옮긴 클래스. 표 하나에 클래스 하나. **이미 열 개가 다 있다 (2026-10-19 `apartment_facility.py`, 2026-10-20 `bus_stop.py` 더함). 새로 만들지 않는다.**
  - `schemas/` : 요청과 응답의 모양, 값의 범위 (Pydantic)
  - `services/` : DB를 읽고 쓰는 함수와 계산. `select(...)`는 여기에만 쓴다.
  - `routers/` : 주소를 받는 곳. `schemas`로 검사하고 `services`를 부르고 응답을 만든다. DB를 다루는 코드와 계산식을 쓰지 않는다.
- `services/calc.py`는 숫자만 안다 (DB와 요청을 모른다). 대출 상품을 넘길 때는 `loan_product.for_calc(상품)`으로 바꿔 넘긴다.
- 표는 `db/schema.sql`로 만든다. `Base.metadata.create_all()`을 서버 코드에서 부르지 않는다. 표나 칸을 바꾸려면 `db/schema.sql`과 DB 설계서를 먼저 고치고 `models/`를 맞춘다. `models/`는 팀장의 파일이므로 팀장에게 말한다.
- DB 세션은 `db: Session = Depends(get_db)`로 받아 `services`의 함수에 넘긴다. 직접 열지 않는다. `services`에서 `commit`하지 않는다. 요청이 끝날 때 `get_db`가 저장한다. 저장한 직후의 값이 필요하면 `db.flush()`와 `db.refresh(객체)`를 쓴다.
- 응답은 `models`의 객체를 그대로 돌려준다. `schemas`의 클래스에 `model_config = ConfigDict(from_attributes=True)`를 두면 알아서 바뀐다.
- `data/` 폴더의 수집·적재 스크립트는 한 번 돌리는 것이라 SQL을 직접 쓴다 (`backend.database.connect`). 서버 코드에서는 `connect`를 쓰지 않는다.
- 지금 사용자는 `user_id: int = Depends(get_current_user_id)`로 받는다. 번호를 코드에 적지 않는다.
- 새 API를 만들 때는 이미 있는 `routers/profile.py`, `services/profile.py`, `schemas/profile.py`의 모양을 따른다. 테스트는 `tests/test_profile.py`를 따른다. 테스트는 MariaDB 없이 임시 DB로 돈다 (`tests/conftest.py`).
- 입력 검증의 문구는 `docs/05_api_spec.md` 5장의 문장을 그대로 쓴다.
- 계산의 버림, 반올림, 올림은 `docs/02_requirements.md` 부록 C를 따른다. 대출금액은 버림, 월 상환액은 반올림, 필요 월 저축액은 올림이다.

### 화면

- 화면마다 HTML 파일 하나. CSS와 JavaScript도 화면 이름으로 따로 둔다.
- 모든 화면이 `js/api.js`, `store.js`, `format.js`, `guard.js`, `layout.js`를 이 순서로 먼저 불러 쓴다 (`frontend/index.html` 참고).
- 서버는 `api.get`, `api.post`, `api.put`으로만 부른다. `fetch`를 직접 쓰지 않는다.
- 브라우저 저장소는 `store.get`, `store.set`으로만 읽고 쓴다. `sessionStorage`를 직접 쓰지 않는다.
- **앞 단계가 빠졌으면 그 화면으로 보내고 한 줄로 알려 준다** (`js/guard.js`). 대출상품 화면은 맨 처음에 `if (!guard.requireStep('loan')) return;`, 지도 화면은 `if (!guard.requireInput()) return;`을 부른다. 입력 화면은 HTML에 `<p class="notice form-page__notice" id="step-notice" hidden></p>`를 두고, 다 그린 뒤 `guard.showNotice()`를 부른다. 넣은 값이 하나도 없으면 시작 화면으로 간다. 본보기는 `plan.html`과 `plan.js`다.
- 금액과 면적은 `format.won`, `format.area`로 보여 준다. 전용면적의 ㎡는 소수점 아래를 버린다 (84.94 → "전용 84㎡". `format.exclusive`). 공급면적은 반올림한다.
- 화면의 모양(색, 글자, 여백)은 [Figma 파일 "money-to-home-mockup"의 섹션 "확정 목업 v3"](https://www.figma.com/design/TSra3U9pIFYKxXvSNS4pu7/money-to-home-mockup?node-id=2034-2)을 따른다. 배치, 문구, 상태는 와이어프레임 설명서를 따른다. 둘이 다르면 목업을 따른다.
- **모바일에는 헤더가 없다.** 서비스 이름(로고)도 두지 않는다. 지도 화면의 맨 위는 내 조건 줄(목표 가능 가격, 수정, 로그인)이고, 입력 화면은 위 52px을 흰 여백으로 둔다.
- **로고는 "쌓이는 동전 + 지붕"이다** (`img/logo.svg`, 2026-10-19). 시작 화면을 탭에서 처음 열 때만 1초 동안 파란 스플래시를 띄운다 (`js/splash.js`, `store`의 `place.splash_seen`). 웹(1200px 이상)에서는 스플래시를 띄우지 않는다.
- **웹(가로 1200px 이상) 배치** (2026-10-19, `common.css`의 "웹 배치"): 입력 화면 여덟 개(시작, 재무정보, 대출상품, 저축 계획, 입력 요약, 로그인, 회원가입, 내 정보)는 가운데 흰 기둥(폭 560px) 하나, 양옆은 회색. 헤더 줄은 없고 로고만 왼쪽 위(왼쪽에서 132px)에 띄운다. 대출 "자세히"는 웹에서 아래에서 올라오지 않고 가운데 모달(높이 770px 고정, 스크롤바 없음)로 뜬다. 지도와 저장한 결과 화면은 아직 모바일 모양이다.
- **지도의 아파트 표시는 말풍선이고, 모양은 시안 7번(흰 바탕, 구분 색 글자와 테두리)이다** (2026-10-16. 예전의 모양 A 그라데이션은 쓰지 않는다). 위에 면적, 그 아래에 실거래 평균가를 적고, 꼬리는 왼쪽 아래에 있다. 누른 표시는 색이 뒤집히고 1.2배다. 여유·부족 금액은 표시에 적지 않고, 표시를 누르면 아래 창에서 보여 준다. 범례는 왼쪽 위 작은 상자로 처음부터 펼쳐 둔다.
- 구분의 색은 지금 가능이 파랑, 기간 내 가능이 라임, 자금 부족이 빨강이다 (팔레트 F 라임).
- **지도를 넓게 보면 말풍선 대신 동마다 표시 하나로 묶는다.** 카카오맵의 확대 수준 5부터 동 표시, 4 이하는 말풍선이다 (2026-10-15 변경. 그 전은 6). 동 표시는 연보라 동그라미에 동 이름과 숫자(그 동에서 목표할 수 있는 아파트 수 = 지금 가능 + 기간 내 가능)다. 누르면 그 동이 가운데로 오면서 확대된다. 확대 수준 7부터는 동 표시도 겹쳐서 구마다 표시 하나로 묶는다 (2026-10-15 변경. 그 전은 8) ("광산구 / 216"). 동작은 동 표시와 같다. 구·동을 고르면 그 지역에 맞춰 옮긴다: 동은 그 동 전체(3 ~ 6. 그 동의 말풍선을 다 그린다. 고른 동 안에서는 그 동의 아파트만 보인다), 구는 아파트가 있는 동들의 범위(7 ~ 8). 자세한 것은 `docs/guides/boundary_data.md`.
- **가까이 볼 때 겹치는 말풍선은 하나로 묶는다.** 넓이의 35% 넘게 겹치면 앞의 하나만 그리고 가려진 수를 "+2"로 적는다. 누르면 한 단계 확대해 풀고, 좌표가 똑같아 풀 수 없으면 누를 때마다 다음 아파트를 앞으로 꺼낸다.
- **자금 부족 표시의 스위치는 처음에 꺼져 있다.** 켜야 자금이 부족한 아파트의 말풍선이 보인다. 목록에는 스위치와 상관없이 나온다.
- 지도 화면이 보는 지역은 `store`의 `map` 묶음에 `gu`, `dong`으로 둔다. **지역은 조건 창(`js/filter.js`) 맨 위에서 고른다** (2026-10-18. 구·동 선택 버튼은 없앴다. `js/region.js`의 창은 남아 있지만 화면에서 열지 않는다). 지도 화면의 자세한 구조는 `docs/guides/handoff_map.md`에 있다.
- **넓게 볼 때 구 표시는 고정된 자리에 둔다.** 가장 넓은 수준(9)에서 겹치지 않게 한 번 정해 수준 7 ~ 9에서 그대로 쓴다 (`map-view.js`의 `spreadGuMarkers`, 보정은 `GU_MARKER_NUDGE`). 구를 고르면 한 화면에 그 구의 동이 가장 많이 들어오는 자리로 옮긴다 (`denseFit`).
- **목록은 iOS 그룹형이다** (`js/list.js`). 기본 정렬은 구분순. 구분 칩(지금 · 기간 내 · 부족)으로 켜고 끄고(`store`의 `map.list_cats`), 보기 방식은 기본 · 게이지(`map.list_view`).
- **시나리오 탭의 그래프 두 개는 `js/scenario-charts.js`가 그린다** (A-27의 DB 값과 A-07의 값만 쓴다. 앞으로의 집값은 그리지 않는다). 그래프 안 금액은 "3.5억"처럼 짧게 적는다. 모양은 `css/scenario-charts.css`에 있고 지도와 공유받은 화면이 같이 불러 쓴다.
- **아파트 창**: 머리 줄 닫기 ✕ 앞에 공유 아이콘, 지번·도로명 주소 옆에 복사 아이콘 (`js/share.js`, FR-APT-18). 공유 링크는 `share.html?apt=번호&area=면적대`이고 **재무정보를 넣지 않는다.** 주변 시설은 A-06의 `facilities`로 채운다 (화면에서 카카오 장소 검색을 부르지 않는다).
- **다른 아파트 · 목록 · 다른 탭을 열면 늘 맨 위부터 보여 준다** (2026-10-19). 앞에서 내려 둔 스크롤 자리를 남기지 않는다 (`sheet.js`의 `scrollToTop`. 30% 단계처럼 높이가 0일 때는 창이 커질 때 다시 한다).
- 화면 파일은 서버가 `Cache-Control: no-cache`로 준다 (#109). 그래도 JS·CSS를 고치면 그 화면 HTML의 `?v=` 숫자를 올린다.
- 색과 크기는 `css/common.css`의 `:root`에 있는 이름을 쓴다. 색 값을 화면 파일에 직접 적지 않는다.
- 모바일이 기본이다. 누르는 영역은 가로세로 44픽셀 이상으로 한다.
- **모바일을 먼저 만든다. 웹(가로 1200픽셀 이상)은 나중에 같은 HTML에 미디어 쿼리로 더한다** (NFR-15). 그때 고치기 쉽게 아래를 지킨다.
  - 모바일과 웹을 다른 HTML로 만들지 않는다. 화면마다 파일은 하나다.
  - 본문의 폭을 픽셀로 직접 적지 않는다. `common.css`의 `--page-width`를 쓴다.
  - 지도 화면의 아래 창은 지도와 한 덩어리로 묶지 않고 따로 둔다. 웹에서는 아래 창이 왼쪽 단으로 옮겨 간다.

### 공통

- 주석과 문서는 한국어로 쓴다. 변수, 함수, 파일의 이름은 영어로 쓴다.
- 이름은 API와 DB의 이름과 같게 쓴다 (`current_assets`, `monthly_saving`, `target_years`).
- 새 라이브러리를 더하지 않는다. 꼭 필요하면 먼저 묻는다.

## 실행

프로젝트 폴더에서, 가상 환경을 켠 뒤 실행한다.

```
.venv\Scripts\activate
uvicorn backend.main:app --reload --port 8000
pytest
```

- 화면: http://localhost:8000
- API 목록: http://localhost:8000/docs
- 상태 확인: http://localhost:8000/api/health

## 일을 마치기 전에

- `pytest`가 통과하는지 본다.
- 서버를 켜서 만든 것을 직접 돌려 본다. 아래 "검증하고 결과를 보여 주는 방법"을 따른다.
- `git status`로 자기 담당 파일만 바뀌었는지, `.env`가 없는지 본다.
- `git add .`을 쓰지 않는다. 파일 이름을 적어 담는다.
- 커밋 메시지는 `종류: 내용` 형식이다. 예: `feat: 대출 계산 API 추가`
- `main`과 `develop`에 직접 올리지 않는다. `develop`에서 만든 작업 브랜치를 올리고 PR을 보낸다.

## 검증하고 결과를 보여 주는 방법

일을 마치면 "됐습니다"라고만 하지 않는다. 실제로 값을 넣어 돌려 보고, **넣은 값과 나온 값을 표로 보여 준다.** 사람이 표만 보고 맞는지 판단할 수 있어야 한다.

### 무엇을 넣어 보는가

| 만든 것 | 넣어 보는 값 | 맞는지 보는 방법 |
| --- | --- | --- |
| 계산 함수, 계산 API | 무작위 정상 값 1,000건 이상. 0원, 상한 값, 목표 기간 "지금"을 꼭 섞는다. | 계산식을 그 자리에서 따로 써서 비교한다. `calc.py`를 다시 부르지 않는다. 불일치가 0건이어야 한다. |
| 입력을 받는 API | 무작위 잘못된 값 수백 건. 음수, 상한 초과, 소수, 글자, 빠진 값, `null`, `true` | 모두 422이고, 문장과 `field`가 API 명세서 5장과 같은지 본다. |
| DB를 읽는 API | 실제 DB(MariaDB)로 부른다. | 같은 내용을 SQL로 따로 세어 비교한다. 응답 시간도 적는다. |
| `data/`의 스크립트 | `--dry-run`으로 한 번, 실제로 두 번 실행한다. | 실행 전과 후의 줄 수를 적는다. 두 번째 실행에서 바뀌는 것이 없어야 한다. 결과를 SQL로 따로 계산해 비교한다. |
| 화면 | 서버를 켜고 단계마다 값을 넣는다. 정상 값, 0, 오류가 나는 값, 새로 고침 | 단계마다 제목, 버튼의 글자와 켜짐 여부, 오류 문구, 보관된 값을 적는다. |

### 어떻게 보여 주는가

- **표로 보여 준다.** 무작위로 넣은 것 가운데 8 ~ 12건을 골라 입력과 결과를 한 줄씩 적는다. 0원, 상한, "지금"이 든 줄을 반드시 넣는다.
- **전체 건수와 불일치 건수를 적는다.** 예: "정상 입력 2,000건 중 불일치 0건, 잘못된 입력 500건 중 거부하지 못한 것 0건"
- **확인한 것과 확인하지 못한 것을 나눠 적는다.** 돌려 보지 않은 것을 "된다"고 적지 않는다. 코드만 쓰고 띄워 보지 않았으면 그렇게 적는다.
- **실제 DB를 바꿨으면 말한다.** 무엇이 몇 줄 바뀌었는지, 되돌렸는지를 적는다. 시험용으로 잠깐 넣은 값은 저장하지 않고 되돌린다 (`rollback`).
- 결과는 PR 설명에도 붙인다. 검토하는 사람이 다시 돌려 보지 않아도 되게 한다.

예시 (저축 계획 계산 API)

| 보유자산(원) | 월 저축(원) | 기간 | 누적 저축액 | 자기자금 | 결과 |
| ---: | ---: | ---: | ---: | ---: | --- |
| 0 | 0 | 3년 | 0 | 0 | 일치 |
| 10,000,000,000 | 1,000,000,000 | 0년 | 0 | 10,000,000,000 | 일치 |
| 2,464,380,000 | 4,410,000 | 10년 | 529,200,000 | 2,993,580,000 | 일치 |

### 지킬 것

- 무작위로 돌린 스크립트는 저장소에 넣지 않는다. 확인용으로 한 번 쓰고 버린다.
- 저장소의 `tests/`에는 값이 고정된 테스트를 넣는다. 아래 "예시 값"과 경계 값을 쓴다. 돌릴 때마다 결과가 달라지는 테스트를 넣지 않는다.
- 시험에 실제 개인정보를 쓰지 않는다. 주민등록번호가 필요하면 지어낸 생년월일을 쓴다.
- 외부 API(실거래가, 카카오)를 시험할 때는 한 구, 한 달처럼 작게 부른다. 키를 화면이나 결과에 찍지 않는다.

## 예시 값

문서, 와이어프레임, 테스트가 같은 값을 쓴다. 결과를 확인할 때 쓴다.

| 입력 | 값 |
| --- | --- |
| 현재 보유자산 | 50,000,000 |
| 월 저축 가능액 | 1,000,000 |
| 목표 기간 | 5년 |
| 첫째 상품 | 최대 한도 360,000,000, 대출 비율 0.7, 연 4.0%, 상환 30년 |

| 결과 | 값 |
| --- | --- |
| 누적 저축액 | 60,000,000 |
| 목표 시점 자기자금 | 110,000,000 |
| 최대 예상 대출금액 | 116,666,666 |
| 그때의 월 상환액 | 556,985 |
| 목표 가능 가격 | 366,666,666 |
| 3억 원 아파트 | 대출 210,000,000, 월 상환 1,002,572, 부족자금 -20,000,000 (기간 내 가능) |
| 4억 5,000만 원 아파트 | 부족자금 25,000,000, 필요 월 저축액 1,416,667 |
