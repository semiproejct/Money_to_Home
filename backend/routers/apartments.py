"""아파트 탐색. 담당: 김목산

- A-02 GET  /api/regions           : 구와 동의 목록
- A-05 POST /api/apartments/search : 아파트 찾기
- A-12 POST /api/regions/summary   : 구별·동별 개수 (2차)
- A-13 GET  /api/data-status       : 수집 기준일 (2차)
- A-24 POST /api/apartments/{id}/similar : 비슷한 아파트 (3차)
- A-27 GET  /api/apartments/{id}/price-history?area_band= : 실거래 기록과 같은 동 비교 (시나리오 탭 그래프)

A-06 아파트 한 곳은 backend/routers/apartment_detail.py에 있다 (담당: 안세환).

요청의 conditions만 쓴다. 로그인 정보와 profiles 표를 읽지 않는다 (NFR-18).
DB를 다루는 코드는 backend/services/apartment.py, 계산은 backend/services/calc.py에 있다 (NFR-13).
A-05와 A-12는 같은 요청의 응답을 잠깐 기억해 둔다 (backend/services/response_cache.py, 2026-10-20).
"""
from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.schemas.apartment import (
    DataStatusOut,
    PriceHistoryOut,
    RegionsOut,
    SearchIn,
    SearchOut,
    SimilarIn,
    SimilarOut,
    SummaryIn,
    SummaryOut,
)
from backend.services import apartment, response_cache

router = APIRouter(prefix="/api", tags=["아파트 탐색"])


@router.get("/regions", response_model=RegionsOut)
def list_regions(db: Session = Depends(get_db)):
    return {"regions": apartment.regions(db)}



@router.post("/apartments/search", response_model=SearchOut)
def search_apartments(body: SearchIn, db: Session = Depends(get_db)):
    where = body.where

    def make() -> bytes:
        result = apartment.search(
            db, body.conditions, where.gu, where.dong, body.filters, body.sort, where.keyword, where.bounds,
            everywhere=bool(where.all),
        )
        return SearchOut.model_validate(result).model_dump_json().encode()

    content = response_cache.get_or_make(db, "search", body.model_dump_json(), make)
    return Response(content=content, media_type="application/json")


@router.post("/regions/summary", response_model=SummaryOut)
def summarize_regions(body: SummaryIn, db: Session = Depends(get_db)):
    def make() -> bytes:
        result = apartment.regions_summary(db, body.conditions, body.level, body.gu, body.filters)
        return SummaryOut.model_validate(result).model_dump_json().encode()

    content = response_cache.get_or_make(db, "summary", body.model_dump_json(), make)
    return Response(content=content, media_type="application/json")


@router.get("/data-status", response_model=DataStatusOut)
def get_data_status(db: Session = Depends(get_db)):
    return apartment.data_status(db)


@router.post("/apartments/{apartment_id}/similar", response_model=SimilarOut)
def similar_apartments(apartment_id: int, body: SimilarIn, db: Session = Depends(get_db)):
    return apartment.similar(db, apartment_id, body.area_band, body.conditions, body.offset, body.sort)


@router.get("/apartments/{apartment_id}/price-history", response_model=PriceHistoryOut)
def price_history(apartment_id: int, area_band: int = Query(...), db: Session = Depends(get_db)):
    return apartment.price_history(db, apartment_id, area_band)
