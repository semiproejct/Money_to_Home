# 머니 to 홈 제출 산출물

| 번호 | 산출물 | 내용 | 위치 |
| --- | --- | --- | --- |
| 1 | 서비스 기획 및 아키텍처 설계서 | 프로젝트 개요, 전체 아키텍처, 요청 흐름, 주요 설계 결정 | [01_architecture.md](01_architecture.md) · [PDF](pdf/01_architecture.pdf) |
| 2 | 풀스택 서비스 코드 저장소 | 백엔드(FastAPI) · DB(스키마 · 마이그레이션) · 화면 코드와 README | [저장소](https://github.com/semiproejct/Money_to_Home) · [README](../../README.md) |
| 3 | 인사이트 대시보드 | 데이터와 계산 결과를 보여 주는 지도 · 목록 · 시나리오 화면 | [04_service_screens.md](04_service_screens.md) · [PDF](pdf/04_service_screens.pdf) · [서비스](https://money-to-home.onrender.com/) |
| 4 | 구축 및 운영 가이드 | 실행 전 준비, 실행, 상태 · 동작 확인, 로그, 데이터 갱신, 재배포, 장애 점검 | [02_operation_guide.md](02_operation_guide.md) · [PDF](pdf/02_operation_guide.pdf) |
| 5 | 트러블슈팅 보고서 | 실제 문제 7건의 원인, 해결 과정, 재발 방지 | [03_troubleshooting.md](03_troubleshooting.md) · [PDF](pdf/03_troubleshooting.pdf) |
| 6 | 최종 발표 자료 | 프로젝트 목표, 서비스 구조, 구현 결과, 화면 | 별도 제출 (PPTX · PDF) |

## 참고 설계 문서

| 문서 | 내용 |
| --- | --- |
| [요구사항 명세서](../02_requirements.md) | 기능 요구사항 159개, 계산식 C-01 ~ C-13 |
| [화면 설계서](../03_ui_design.md) | 화면 목록과 동작 |
| [DB 설계서](../04_database_design.md) | 표 10개, ERD, 칸 정의 |
| [API 명세서](../05_api_spec.md) | REST API 35개 |

## 프로젝트 템플릿 항목과 다른 점

- **LLM API:** 사용하지 않았습니다. 결과가 "얼마가 부족한가"라는 숫자라서 같은 입력에 같은 값이 나오고 검산할 수 있도록 결정적인 계산식(`backend/services/calc.py`)으로 계산합니다. 이유는 설계서 ①에 있습니다.
- **대시보드:** 관리자용 대시보드 대신 사용자 지도 화면에서 데이터와 지표를 보여 줍니다 (산출물 3).
