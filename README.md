# 머니 to 홈

내 자산·저축·대출로 목표할 수 있는 집을 지도에서 찾는 내 집 마련 시뮬레이터

## 프로젝트 소개

보유자산과 저축 계획, 대출 상품을 선택하면 지금 또는 10년 안에 구매를 목표로 할 수 있는 광주 5개 구의 아파트를 지도에 보여 주고, 그 집을 사려면 자금이 얼마나 더 필요한지 계산해 주는 서비스입니다.

- 미래 집값을 예측하지 않습니다. 모든 금액을 현재 가치 기준으로 계산합니다.
- 대출 금액은 상품의 공개 조건으로 계산한 추정치이며, 실제 대출 여부와 한도는 금융기관 심사로 결정됩니다.
- 지도에 표시되는 아파트는 판매 중인 매물이 아니라 실거래 기록이 있는 아파트입니다.

| 항목 | 내용 |
| --- | --- |
| 기간 | 2026.10.06 ~ (2주) |
| 인원 | 4명 |
| 대상 지역 | 광주 5개 구 (전남광주통합특별시의 동구, 서구, 남구, 북구, 광산구. 옛 광주광역시) |
| 대상 주택 | 아파트 매매 |

## 서비스 흐름

재무정보 입력 → 대출상품 선택 → 저축 계획 → 지도(아파트 탐색) → 동이나 아파트 선택 → 필요자금 결과(시나리오)

## 주요 기능

| 기능 | 내용 |
| --- | --- |
| 재무정보 입력 | 주민등록번호 앞 7자리로 만 나이 계산(저장하지 않음), 연 소득과 현재 보유자산 입력 |
| 대출상품 선택 | 한국주택금융공사, 카카오뱅크 대표 상품의 조건 안내, 예상 대출금액과 월 상환액 계산. 대출 없이 계산할 수도 있음 |
| 저축 계획 | 월 저축 가능액과 목표 기간으로 누적 저축액 계산 |
| 아파트 탐색 | 실거래 평균가를 기준으로 지금 가능, 목표 기간 안에 가능, 자금 부족으로 구분 |
| 지도 표시 | 지도 전체 화면에 아파트를 구분해서 표시하고, 아래에서 올라오는 창에 목록과 아파트 정보를 표시 |
| 필요자금 결과 | 필요자금, 부족·여유자금, 필요 월 저축액, 허용 상승률 |

## 산출물

| 일자 | 문서 | 내용 |
| --- | --- | --- |
| 10/11 | [설계 문서 요약](docs/00_summary.md) | 아래 문서들을 처음 보는 사람도 이해할 수 있게 풀어 쓴 요약. 먼저 읽기를 권합니다. |
| 10/06 | [프로젝트 기획서](docs/01_project_overview.md) | 주제, 배경, 목표, 범위 |
| 10/07 | [요구사항 명세서](docs/02_requirements.md) | 기능 요구사항 159개, MoSCoW 우선순위, User Story, Task 분해 |
| 10/08 | [화면 설계서](docs/03_ui_design.md) | 화면 목록, 공통 구조, 입력 화면과 지도 화면의 동작, 면적 표기, 와이어프레임 링크 |
| 10/11 | [와이어프레임 설명서](docs/03_ui_design_wireframe.md) | 와이어프레임 110장의 그림과 한 장마다의 설명 (본 와이어프레임 109장, 보류 1장) |
| 10/13 | [Figma 목업](https://www.figma.com/design/TSra3U9pIFYKxXvSNS4pu7/money-to-home-mockup?node-id=2034-2) | 모바일 화면의 목업. 색, 글자, 여백 같은 모양의 기준. 섹션 "확정 목업 v3"을 본다. |
| 10/11 | [DB 설계서](docs/04_database_design.md) | 공식 초안. 표 8개와 관계도(ERD), 칸 정의, 테이블 생성 스크립트([db/schema.sql](db/schema.sql)) |
| 10/11 | [API 명세서](docs/05_api_spec.md) | 초안. REST API 후보 26개, 공통 규칙, 화면과 API의 대응. 구조에 관한 열 가지는 정함 |
| 10/11 | [아키텍처 문서](docs/06_architecture.md) | 초안. 전체 구성, 기술 스택, 폴더 구조, 만드는 순서, 검토 결과 |

## 기술 스택

| 구분 | 기술 |
| --- | --- |
| Frontend | HTML, CSS, JavaScript |
| Backend | Python, FastAPI, SQLAlchemy |
| Database | MariaDB 11.4 (MySQL 호환) |
| Data | Pandas, 국토교통부 아파트 매매 실거래가 API |
| Map | 카카오맵 API |

## 팀원

| 이름 | 역할 | GitHub |
| --- | --- | --- |
| 김해원 | 팀장. 입력과 공통 (재무정보, 저축 계획, 문서, 통합) | [KHW1003](https://github.com/KHW1003) |
| 김목산 | 자료와 탐색 (실거래 자료 적재, 아파트 찾기, 목록) | [kimmoksan](https://github.com/kimmoksan) |
| 박채은 | 대출과 계산 (계산 모듈, 대출상품, 시나리오) | [chaeeun](https://github.com/chaeeun) |
| 안세환 | 지도와 아파트 창 (좌표 변환, 지도, 아래 창, 아파트 정보) | [sehwan-An](https://github.com/sehwan-An) |

네 명 모두 화면, 서버, DB를 다 씁니다. 할 일의 순서는 [역할 분담](docs/roles.md)에 있습니다.

## 폴더 구조

```
├─ docs/            프로젝트 문서, 와이어프레임 그림
├─ db/              테이블 생성 스크립트, 대출 상품 자료
├─ backend/         FastAPI 서버
│  ├─ main.py       앱을 만들고 API와 화면을 연결
│  ├─ models/       DB의 표를 옮긴 클래스 (SQLAlchemy)
│  ├─ schemas/      요청과 응답의 모양, 값의 범위
│  ├─ routers/      API
│  └─ services/     DB를 읽고 쓰는 함수, 계산 모듈
├─ frontend/        웹 화면 (HTML, CSS, JavaScript)
├─ tests/           자동 테스트
├─ data/            실거래 자료와 수집·가공 스크립트
├─ requirements.txt 설치할 라이브러리와 버전
├─ CLAUDE.md        AI 도구에 주는 프로젝트 규칙
├─ .env.example     키 이름만 적은 견본. 복사해서 .env로 씁니다.
└─ .gitignore
```

## 실행 방법

처음 하는 사람은 [개발 환경 맞추기](docs/setup_guide.md)를 순서대로 따라 합니다. 요약하면 아래와 같습니다.

1. `.env.example`을 복사해 `.env`로 이름을 바꾸고 값을 채웁니다. `.env`는 저장소에 올리지 않습니다.
2. MariaDB 11.4에서 `db/schema.sql`과 `db/seed_loan_products.sql`을 차례로 실행합니다. HeidiSQL에서는 [파일] > [SQL 파일 불러오기]로 열고 F9를 누릅니다.
3. 가상 환경을 만들고 라이브러리를 설치합니다.

```
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

4. 실거래 자료, 좌표, 세대수, 주변 시설을 DB에 넣습니다. 외부 API를 부르지 않고 저장소에 든 파일에서 넣습니다. 이 순서대로 합니다 (뒤의 것은 앞에서 넣은 아파트에 붙습니다).

```
python data/load_trades.py data/collected
python data/load_supply_area.py
python data/geocode.py --from-file data/geocoded.csv
python data/load_households.py --from-file data/households.csv
python data/load_facilities.py --from-file data/facilities.csv
```

이미 DB를 만들어 둔 사람은 `db/schema.sql`을 다시 실행해 새 표(`apartment_facilities`, 2026-10-19)를 만든 뒤 마지막 줄만 실행하면 됩니다.

5. 서버를 켭니다.

```
uvicorn backend.main:app --reload --port 8000
```

6. 브라우저에서 `http://localhost:8000`을 엽니다. 주소에 `frontend`를 넣지 않습니다. API 목록은 `http://localhost:8000/docs`, 상태 확인은 `http://localhost:8000/api/health`입니다.
7. 자동 테스트는 `pytest`로 돌립니다.

## 협업 규칙

**브랜치**

| 브랜치 | 용도 |
| --- | --- |
| `main` | 제출용 완성본. 직접 push하지 않습니다. |
| `develop` | 개발 통합. PR은 이 브랜치로 보냅니다. |
| `feature/기능명` | 기능 개발 |
| `docs/문서명` | 문서 작업 |
| `fix/버그명` | 버그 수정 |

**커밋 메시지**

`종류: 내용` 형식으로 씁니다. 예: `docs: 요구사항 명세서 추가`

| 종류 | 쓰는 때 |
| --- | --- |
| `feat` | 새 기능 |
| `fix` | 버그 수정 |
| `docs` | 문서 |
| `refactor` | 동작은 그대로 두고 코드 정리 |
| `chore` | 설정, 폴더 구조 |

**Pull Request**

- 팀원 1명 이상의 승인을 받은 뒤 머지합니다.
- 머지한 브랜치는 삭제합니다.
