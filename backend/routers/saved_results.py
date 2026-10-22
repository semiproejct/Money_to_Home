"""결과 저장 (3차). 담당: 박채은

- A-21 POST /api/saved-results      : 계산 결과 저장 (201)
- A-22 GET  /api/saved-results      : 내가 저장한 결과 목록. 최근 것부터
- A-23 GET  /api/saved-results/{id} : 저장한 결과 하나. 남의 것이면 404
- A-35 DELETE /api/saved-results/{id} : 찜 해제 (204). 남의 것이면 404 (2026-10-21)

셋 다 로그인해야 쓴다. 로그인하지 않았으면 401 (deps.require_login).
계산식은 여기에 쓰지 않는다. 저장할 때 다시 계산하는 일과 DB는 backend/services/saved_result.py가 한다.
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.deps import require_login
from backend.schemas.saved_result import SavedResultIn, SavedResultOut, SavedResultsOut
from backend.services import saved_result

router = APIRouter(prefix="/api/saved-results", tags=["결과 저장"])


@router.post("", response_model=SavedResultOut, status_code=201)
def save_result(body: SavedResultIn, db: Session = Depends(get_db), user_id: int = Depends(require_login)):
    return saved_result.save(db, user_id, body.conditions, body.apartment_id, body.area_band, body.profile_id)


@router.get("", response_model=SavedResultsOut)
def list_results(db: Session = Depends(get_db), user_id: int = Depends(require_login)):
    return {"results": saved_result.find_all(db, user_id)}


@router.get("/{id}", response_model=SavedResultOut)
def get_result(id: int, db: Session = Depends(get_db), user_id: int = Depends(require_login)):
    return saved_result.find_one(db, user_id, id)


@router.delete("/{id}", status_code=204)
def delete_result(id: int, db: Session = Depends(get_db), user_id: int = Depends(require_login)):
    saved_result.delete(db, user_id, id)
