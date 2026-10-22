"""A-05 아파트 찾기와 A-12 구별·동별 개수의 응답을 서버에 잠깐 기억해 둔다 (2026-10-20).

광주 전체(1,055곳)를 계산하면 0.1 ~ 0.3초가 걸린다. 같은 요청(조건 · 범위 · 정렬이 같음)이 다시 오면 계산하지 않고
기억해 둔 응답(JSON)을 그대로 보낸다. 지도를 처음 열 때, 구 표시를 오갈 때, 다른 사람이 같은 조건으로 볼 때 빨라진다.

언제 다시 계산하나
- 자료를 새로 넣으면: 적재 스크립트(data/load_*.py)는 넣을 때마다 data_collections에 한 줄을 더한다.
  그 줄의 가장 큰 번호를 기억의 열쇠에 넣으므로, 새로 넣은 뒤의 요청은 새로 계산한다.
- TTL_SECONDS가 지나면: 대출 상품처럼 data_collections를 거치지 않고 바뀌는 자료도 이 시간 뒤에는 반영된다.
- 서버를 다시 켜면 모두 지워진다 (메모리에만 둔다).

입력값(재무정보)은 요청에 담겨 오고, 응답에 다른 사람의 정보가 들어가지 않는다. 그래서 같은 요청이면 누구에게 보내도 같다.
오류(422 등)는 기억하지 않는다.
"""
import threading
import time
from collections import OrderedDict

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.models import DataCollection

TTL_SECONDS = 600  # 10분
MAX_ITEMS = 256  # 이보다 많으면 가장 오래 안 쓴 것부터 버린다 (지도를 끌 때마다 영역이 달라 쌓인다)

enabled = True  # 테스트는 끈다 (tests/conftest.py). 켠 채로 확인하는 테스트는 따로 있다
_items: OrderedDict = OrderedDict()  # 열쇠 → (기억한 때, 응답 JSON bytes)
_lock = threading.Lock()


def data_version(db: Session):
    """자료의 판. data_collections의 가장 큰 번호. 자료를 새로 넣으면 바뀐다"""
    return db.scalar(select(func.max(DataCollection.id)))


def get_or_make(db: Session, name: str, request_key: str, make) -> bytes:
    """기억해 둔 응답이 있으면 그것을, 없으면 make()로 만들어 기억하고 돌려준다. make는 JSON bytes를 돌려준다"""
    if not enabled:
        return make()
    key = (name, data_version(db), request_key)
    now = time.monotonic()
    with _lock:
        hit = _items.get(key)
        if hit is not None and now - hit[0] < TTL_SECONDS:
            _items.move_to_end(key)
            return hit[1]
    value = make()  # 계산하는 동안은 잠그지 않는다 (같은 요청이 겹치면 둘 다 계산할 뿐 결과는 같다)
    with _lock:
        _items[key] = (now, value)
        _items.move_to_end(key)
        while len(_items) > MAX_ITEMS:
            _items.popitem(last=False)
    return value


def clear():
    with _lock:
        _items.clear()
