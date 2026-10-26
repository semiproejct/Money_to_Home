# 2. 구축 및 운영 가이드

새 운영자가 프로젝트를 넘겨받았다고 가정하고, **처음 실행하는 방법 · 정상 동작을 확인하는 방법 · 문제가 생겼을 때 먼저 볼 것**을 순서대로 적었습니다.

| 항목 | 내용 |
| --- | --- |
| 운영 주소 | https://money-to-home.onrender.com/ (Render 무료 서버 + Aiven 무료 MySQL) |
| 로컬 주소 | http://localhost:8000 |
| 기준 | `develop` 브랜치, 2026-10-26 |

---

## ① 실행 전 준비

### 1. 프로그램

| 프로그램 | 버전 | 확인 명령 |
| --- | --- | --- |
| Python | 3.12 (운영 3.12.10) | `python --version` |
| MariaDB | 11.4 (로컬). 운영은 MySQL 8 (Aiven) | `mysql --version` 또는 HeidiSQL 접속 |
| Git | 아무 최신판 | `git --version` |
| 브라우저 | Chrome · Edge 최신판 | |

Node.js는 쓰지 않습니다. 화면은 서버(FastAPI)가 `frontend/` 폴더를 그대로 내려 줍니다.

### 2. 코드 받기

```
git clone https://github.com/semiproejct/Money_to_Home.git
cd Money_to_Home
git switch develop
```

### 3. 환경 변수 (`.env`)

`.env.example`을 복사해 `.env`로 이름을 바꾸고 값을 채웁니다. **`.env`는 저장소에 올리지 않습니다** (`.gitignore`에 등록).

| 이름 | 쓰는 곳 | 비고 |
| --- | --- | --- |
| `DATA_GO_KR_KEY` | 실거래가 · 건축물대장 수집 스크립트 | 공공데이터포털 일반 인증키(Decoding). 서비스 실행에는 필요 없음 |
| `KAKAO_JS_KEY` | 화면의 카카오맵 | 카카오 개발자 콘솔에 **사이트 도메인 등록** 필수 |
| `KAKAO_REST_API_KEY` | 좌표 · 주변 시설 수집 스크립트 | 화면 코드에 넣지 않음 |
| `DB_HOST` · `DB_PORT` · `DB_NAME` · `DB_USER` · `DB_PASSWORD` | 서버의 DB 접속 | 로컬 기본 `localhost` · `3306` · `money_to_home` |
| `DB_SSL` · `DB_SSL_CA` | 클라우드 DB(Aiven) 접속 | 로컬은 비워 둠 |
| `SESSION_SECRET_KEY` | 로그인 쿠키 서명(HMAC) | 길고 무작위인 문자열 |

LLM API Key는 쓰지 않습니다 (설계서 ① 참고).

### 4. 데이터베이스 만들기

HeidiSQL에서 [파일] > [SQL 파일 불러오기]로 열고 F9를 누릅니다. 이 순서대로 합니다.

1. `db/schema.sql`: DB와 표 10개를 만듭니다. 여러 번 실행해도 됩니다.
2. `db/seed_loan_products.sql`: 대출 상품 2개를 넣습니다.
3. (2026-10-21 이전에 DB를 만든 경우만) `db/migrate_20261021_multi_profile.sql`: 재무정보를 회원당 3칸으로 바꿉니다. **한 번만** 실행합니다. `profiles`에 `id` 칸이 이미 있으면 실행하지 않습니다.

### 5. 패키지 설치

```
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

### 6. 자료 넣기

외부 API를 부르지 않고 저장소에 든 파일에서 넣습니다. **순서를 지킵니다** (뒤의 것은 앞에서 넣은 아파트에 붙습니다).

```
python data/load_trades.py data/collected
python data/load_supply_area.py
python data/geocode.py --from-file data/geocoded.csv
python data/load_households.py --from-file data/households.csv
python data/load_facilities.py --from-file data/facilities.csv
```

---

## ② 서비스 실행

**프로젝트 맨 위 폴더(`Money_to_Home`)에서** 실행합니다. `.venv\Scripts` 같은 하위 폴더에서 실행하면 `ModuleNotFoundError: No module named 'backend'`가 납니다.

```
.venv\Scripts\activate
uvicorn backend.main:app --reload --port 8000
```

정상이면 아래가 나옵니다.

```
INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
INFO:     Application startup complete.
```

브라우저에서 `http://localhost:8000`을 엽니다. 주소에 `frontend`를 넣지 않습니다.

### 운영(Render) 설정

| 항목 | 값 |
| --- | --- |
| 배포 브랜치 | `main` |
| Build Command | `pip install -r requirements.txt` |
| Start Command | `uvicorn backend.main:app --host 0.0.0.0 --port $PORT` |
| 환경 변수 | `.env`의 값 (DB는 Aiven 값), `DB_SSL=true`, `PYTHON_VERSION=3.12.10` |
| CA 인증서 (선택) | Secret File `ca.pem`, `DB_SSL_CA=/etc/secrets/ca.pem` |

무료 서버라 한동안 접속이 없으면 잠듭니다. 첫 요청이 30~60초 늦을 수 있습니다.

---

## ③ 실행 상태 확인

```
curl http://localhost:8000/api/health
```

| 응답 | 뜻 | 할 일 |
| --- | --- | --- |
| `{"status":"ok","db":"ok"}` | 서버와 DB 모두 정상 | 없음 |
| `{"status":"ok","db":"error"}` | 서버는 켜졌지만 DB 연결 실패 | ⑧의 2번 (DB 연결) 확인. 자세한 원인은 서버 로그에만 남음 |
| 연결 거부 · 응답 없음 | 서버가 꺼짐 | ② 다시 실행 |

운영: `curl https://money-to-home.onrender.com/api/health`

---

## ④ 서비스 정상 동작 확인

### 1. API가 정상 응답하는지

| 확인 | 명령 | 정상 결과 |
| --- | --- | --- |
| 대출 상품 | `curl http://localhost:8000/api/loan-products` | `"products"`에 보금자리론 · 주택담보대출 2개 |
| 자료 기준일 | `curl http://localhost:8000/api/data-status` | `{"trades_base_date":"2026-10-12", ...}` |
| 저축 계산 | 아래 1 | `{"accumulated_saving":90000000,"own_funds":140000000}` |
| 아파트 찾기 | 아래 2 | `"counts": {"now":5,"within":14,"lack":3,"total":22}` |
| 값 검사 | 아래 3 | 422 `{"detail":"숫자만 입력할 수 있습니다.","field":"current_assets"}` |

```
# 1. 저축 계산
curl -X POST http://localhost:8000/api/calc/plan -H "Content-Type: application/json" ^
  -d "{\"current_assets\":50000000,\"monthly_saving\":1500000,\"target_years\":5}"

# 2. 아파트 찾기 (서구 치평동). 한글이 깨지면 /docs 화면에서 같은 값으로 시험한다
curl -X POST http://localhost:8000/api/apartments/search -H "Content-Type: application/json" ^
  -d "{\"conditions\":{\"current_assets\":50000000,\"monthly_saving\":1500000,\"target_years\":5,\"loan_choice\":\"product\",\"loan_product_id\":1,\"repayment_years\":30},\"where\":{\"gu\":\"서구\",\"dong\":\"치평동\"}}"

# 3. 값 검사 (일부러 틀린 값)
curl -X POST http://localhost:8000/api/calc/plan -H "Content-Type: application/json" ^
  -d "{\"current_assets\":\"오천만\",\"monthly_saving\":1,\"target_years\":5}"
```

모든 API는 `http://localhost:8000/docs`(Swagger UI)에서 직접 요청을 보내 볼 수 있습니다.

### 2. 자동 테스트

```
pytest
```

정상: `333 passed`. 실패가 있으면 바뀐 코드가 계산이나 API 약속을 깨뜨린 것입니다.

### 3. 화면에 실제 데이터가 표시되는지

| 순서 | 확인 | 정상 모습 |
| --- | --- | --- |
| 1 | 시작 → 재무정보 → 대출상품 → 저축 계획 | 대출상품 화면에 "예상 최대 대출금액", 저축 계획 화면에 "5년 뒤 자기자금" |
| 2 | 지도 화면 | 광주 5개 구 표시와 아파트 수, 오른쪽 위 "실거래 2026년 10월 12일 기준" |
| 3 | 서구 → 치평동 | 남색 동 경계와 아파트 말풍선, 목록 "서구 치평동 · 22곳" |
| 4 | 아파트 말풍선 누르기 | 로드뷰, 아파트 정보, 주변 시설과 도보 시간 |
| 5 | 시나리오 탭 | 부족 · 여유자금, 허용 상승률 |
| 6 | 로그인 → 찜 → 마이페이지 | 재무정보 칸과 찜한 시나리오 목록 |

지도가 회색으로만 나오면 카카오 도메인 등록 문제입니다 (⑧의 6번).

---

## ⑤ 로그 확인

| 어디 | 보는 법 | 내용 |
| --- | --- | --- |
| 백엔드 (로컬) | `uvicorn`을 실행한 터미널 | 요청마다 `"GET /api/... HTTP/1.1" 200`, 오류 시 `money_to_home` 로거의 Traceback |
| 백엔드 (운영) | Render 대시보드 → 서비스 → **Logs** | 위와 같음. 배포 · 재시작 기록 포함 |
| 프론트엔드 | 브라우저 F12 → **Console**, **Network** | JavaScript 오류, 실패한 API 요청의 상태 코드와 응답 본문 |
| DB | HeidiSQL에서 직접 조회 | `SELECT * FROM data_collections ORDER BY id DESC;` 등 |

별도 로그 파일은 만들지 않습니다. 서버는 오류를 표준 출력(터미널 · Render Logs)에 남기고, 사용자 응답에는 DB 접속 정보 같은 내부 내용을 넣지 않습니다.

---

## ⑥ 데이터 갱신

실거래가는 월 단위로 쌓이므로 매달 한 번 갱신합니다. `.env`에 `DATA_GO_KR_KEY`가 있어야 합니다.

```
# 1. 시험 호출 (저장하지 않음)
python data/collect_trades.py --test

# 2. 지난달까지 12개월 수집 (data/collected/<구코드>_<연월>.csv)
python data/collect_trades.py

# 3. 실패한 것이 있으면 data/collected/failed.csv를 보고 그것만 다시
python data/collect_trades.py --only 12240-202609

# 4. DB에 적재 (평균가 다시 계산, 수집 기준일 기록)
python data/load_trades.py data/collected
```

**갱신 확인**

1. `curl http://localhost:8000/api/data-status`의 `trades_base_date`가 새 날짜로 바뀌었는지 봅니다.
2. 지도 화면 오른쪽 위 "실거래 ○월 ○일 기준"이 바뀌었는지 봅니다.
3. 같은 아파트의 평균가 · 거래 건수가 새 자료로 바뀌었는지 봅니다.

아파트 찾기 응답 캐시는 수집 기준일이 바뀌면 자동으로 무효가 됩니다. 그 밖의 자료도 10분 뒤에는 반영됩니다.

운영 DB(Aiven)는 로컬에서 갱신한 뒤 HeidiSQL로 내보내 Aiven에 실행하거나, `.env`의 DB 값을 Aiven으로 바꿔 적재 스크립트를 실행합니다.

---

## ⑦ 재배포 또는 업데이트

```
feature 브랜치에서 수정 → PR (1명 이상 승인) → develop 머지
→ 로컬에서 pytest · 화면 확인
→ develop을 main에 PR로 머지
→ Render가 main을 자동 재빌드 · 재실행
→ /api/health 확인 → 화면 확인
```

| 확인할 것 | 이유 |
| --- | --- |
| CSS · JS를 고쳤으면 HTML의 `?v=` 숫자를 올렸는지 | 올리지 않으면 브라우저가 옛 파일을 캐시에서 씁니다 (CSS · JS는 1일 캐시) |
| DB 구조를 바꿨으면 `db/migrate_*.sql`을 운영 DB에도 실행했는지 | Render는 코드만 배포합니다 |
| 백엔드를 고친 뒤 로컬 서버를 다시 켰는지 | `--reload`가 변경을 놓치는 일이 있습니다 |

---

## ⑧ 장애 발생 시 기본 점검 순서

| 순서 | 점검 | 방법 | 자주 보는 원인 |
| --- | --- | --- | --- |
| 1 | 백엔드 서버 상태 | `curl /api/health`, Render 대시보드 상태 | 서버 꺼짐, Render 무료 서버 잠듦(첫 요청 30~60초) |
| 2 | DB 연결 | `/api/health`의 `db` 값, HeidiSQL 접속 | `.env`의 DB 값 오타, Aiven `DB_SSL` 누락, DB 서버 꺼짐 |
| 3 | DB 구조 | `SHOW COLUMNS FROM profiles;` 등 | 마이그레이션 미실행 → 화면에 "인터넷 연결" 오류 (트러블슈팅 보고서 6) |
| 4 | 애플리케이션 로그 | 터미널 · Render Logs의 Traceback | 코드 오류, 새 API가 반영되지 않음(서버 재시작 필요) |
| 5 | 프론트엔드 콘솔 | F12 Console · Network | JS 오류, API 404 · 422 · 500 |
| 6 | 외부 서비스 · 키 | 카카오 SDK 요청 응답 | 카카오 도메인 미등록 → `domain mismatched!` 401, 지도 안 뜸 |
| 7 | 환경 변수 | `.env` · Render Environment | `SESSION_SECRET_KEY` 바뀜 → 기존 로그인 풀림 |
| 8 | 데이터 적재 상태 | `/api/data-status`, `SELECT COUNT(*) FROM trades;` | 적재 스크립트 순서 틀림, 수집 실패(`failed.csv`) |
| 9 | 브라우저 캐시 | 강력 새로고침(Ctrl + Shift + R) | `?v=` 숫자를 올리지 않은 배포 |

LLM API 점검 항목은 해당 없습니다 (LLM을 쓰지 않음).
