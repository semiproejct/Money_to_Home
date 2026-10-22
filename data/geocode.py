"""아파트 주소를 카카오 로컬 API로 좌표(위도, 경도)로 바꿔 apartments 표에 넣는다. 담당: 안세환

DB 설계서 5장의 7번(주소를 좌표로 바꾼다), 요구사항 FR-DATA-04, T-DATA-07, R-06.
아파트는 data/load_trades.py(김목산)가 먼저 DB에 넣어 두어야 한다.
화면과 서버는 카카오를 부르지 않고 이 스크립트가 넣은 좌표만 읽는다 (NFR-08).

준비물
  .env 파일에 REST API 키:  KAKAO_REST_API_KEY=카카오_REST_API_키   (JavaScript 키가 아니다)
  .env의 DB 계정으로 접속한다 (backend.database.connect).

사용법 (프로젝트 폴더에서, 가상 환경을 켠 뒤)
  python data/geocode.py --check                  주소 형식 시험. 아파트 1곳을 네 가지 형식으로 물어본다. DB를 바꾸지 않는다
  python data/geocode.py --dry-run                몇 곳을 몇 번 부를지만 보여 준다. 카카오를 부르지 않고 DB를 바꾸지 않는다
  python data/geocode.py --limit 5                5곳만 바꿔 DB에 넣는다 (구마다 고르게 고른다)
  python data/geocode.py                          아직 바꾸지 않은 아파트 전부. 돌리기 전에 단체방에 알린다
  python data/geocode.py --from-file data/geocoded.csv
                                                  카카오를 부르지 않고 파일의 좌표를 DB에 넣는다 (나머지 세 명)

  --force       이미 바꾼 아파트도 다시 한다. 평소에는 geocode_status가 빈 아파트만 한다.
  --sido 이름   주소 앞에 붙일 시도 이름. new(전남광주통합특별시, 기본), old(광주광역시), short(광주)
                --check 결과를 보고 되는 쪽을 쓴다.

묻는 순서 (아파트마다)
  1. 지번 주소    "전남광주통합특별시 서구 치평동 1171-4"
  2. 도로명 주소  "전남광주통합특별시 서구 화산로 352"   (1에서 못 찾고 도로명이 있을 때만)
  그래도 못 찾으면 failed로 넣는다.

찾은 것으로 인정하는 조건 (셋 다 맞아야 한다)
  - 카카오의 정확히 일치 검색(analyze_type=exact)으로 나온 주소다. 비슷한 번지(1171-4 대신 1171)는 받지 않는다.
  - 그 주소의 구가 우리 아파트의 구와 같다.
  - 좌표가 광주 5개 구 범위(위도 35.0 ~ 35.3, 경도 126.6 ~ 127.0) 안이다.
  후보가 여럿이면 조건에 맞는 첫 번째를 쓴다. 좌표를 지어내지 않는다.

넣는 곳 (apartments)
  latitude, longitude   소수점 아래 7자리 (DECIMAL(10,7)). 실패하면 비운다.
  geocode_status        ok 또는 failed. 비어 있으면 아직 바꾸지 않은 것이다.

남기는 파일
  data/geocode_failed.csv   이번에 실패한 아파트와 이유. Git에 올리지 않는다.
  data/geocoded.csv         DB에서 변환을 마친 아파트 전부 (구, 동, 지번, 아파트명, 위도, 경도, 결과).
                            전체를 돌린 뒤 이 파일을 저장소에 올려 팀이 나눠 쓴다. 시험(--limit) 때 생긴 것은 올리지 않는다.

규칙
  - 키는 .env에서 읽는다. 화면과 파일에 출력하지 않고, 오류 문장에 섞여 나와도 가린다.
  - 호출 사이에 0.1초 쉰다. 50곳마다 저장하므로 중간에 멈춰도 다시 돌리면 남은 것부터 한다.
  - 키가 틀렸거나(401, 403) 호출 한도에 걸리면(429) 그때까지 한 것을 저장하고 멈춘다.
"""
import argparse
import csv
import json
import os
import sys
import time
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path

import requests

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

URL = "https://dapi.kakao.com/v2/local/search/address.json"
SIDO_NAMES = {"new": "전남광주통합특별시", "old": "광주광역시", "short": "광주"}

# 광주 5개 구 범위. 이 밖의 좌표는 잘못 찾은 것으로 보고 failed로 넣는다.
LAT_MIN, LAT_MAX = Decimal("35.0"), Decimal("35.3")
LNG_MIN, LNG_MAX = Decimal("126.6"), Decimal("127.0")

SLEEP_SECONDS = 0.1
MAX_RETRY = 3
TIMEOUT_SECONDS = 10
COMMIT_EVERY = 50

FAILED_PATH = BASE_DIR / "data" / "geocode_failed.csv"
GEOCODED_PATH = BASE_DIR / "data" / "geocoded.csv"
GEOCODED_COLS = ["gu", "dong", "jibun", "name", "latitude", "longitude", "geocode_status"]
FAILED_COLS = ["gu", "dong", "jibun", "name", "road_address", "reason"]


class StopAll(Exception):
    """키가 틀렸거나 호출 한도에 걸려 더 물어도 소용없을 때."""


# ------------------------------------------------------------------
# 1. 키
# ------------------------------------------------------------------
def load_key():
    """.env의 KAKAO_REST_API_KEY. backend.config를 불러오면 .env 전체가 환경 변수로 올라온다."""
    import backend.config  # noqa: F401
    key = os.environ.get("KAKAO_REST_API_KEY", "").strip()
    if not key:
        sys.exit(".env 파일에 KAKAO_REST_API_KEY=REST_API_키 를 넣어 주세요. 프로젝트 폴더에서 실행했는지도 확인해 주세요.")
    return key


def hide_key(text, key):
    """오류 문장에 키가 섞여 나오지 않게 가린다."""
    return str(text).replace(key, "***") if key else str(text)


# ------------------------------------------------------------------
# 2. DB
# ------------------------------------------------------------------
def read_targets(cur, force):
    """좌표를 바꿀 아파트. --force가 없으면 geocode_status가 빈 것만."""
    sql = "SELECT id, gu, dong, jibun, name, road_address FROM apartments"
    if not force:
        sql += " WHERE geocode_status IS NULL"
    cur.execute(sql + " ORDER BY id")
    return list(cur.fetchall())


def spread_by_gu(rows, limit):
    """구마다 돌아가며 하나씩 골라 limit곳을 만든다. 5곳이면 5개 구에서 한 곳씩."""
    by_gu = {}
    for row in rows:
        by_gu.setdefault(row["gu"], []).append(row)
    picked = []
    while len(picked) < limit and any(by_gu.values()):
        for gu in sorted(by_gu):
            if by_gu[gu] and len(picked) < limit:
                picked.append(by_gu[gu].pop(0))
    return picked


def save_result(cur, apartment_id, lat, lng, status):
    cur.execute(
        "UPDATE apartments SET latitude = %s, longitude = %s, geocode_status = %s WHERE id = %s",
        (lat, lng, status, apartment_id),
    )


def export_geocoded(cur):
    """DB에서 변환을 마친 아파트 전부를 data/geocoded.csv로 남긴다. 팀이 나눠 쓰는 파일이다."""
    cur.execute(
        "SELECT gu, dong, jibun, name, latitude, longitude, geocode_status FROM apartments "
        "WHERE geocode_status IS NOT NULL ORDER BY gu, dong, jibun, name"
    )
    rows = list(cur.fetchall())
    with open(GEOCODED_PATH, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=GEOCODED_COLS)
        writer.writeheader()
        for r in rows:
            writer.writerow({
                **{c: r[c] for c in ("gu", "dong", "jibun", "name", "geocode_status")},
                "latitude": "" if r["latitude"] is None else str(r["latitude"]),
                "longitude": "" if r["longitude"] is None else str(r["longitude"]),
            })
    return len(rows)


# ------------------------------------------------------------------
# 3. 카카오에 묻기
# ------------------------------------------------------------------
def ask_kakao(session, key, query):
    """주소 하나를 정확히 일치 검색으로 묻고 documents를 돌려준다."""
    last_error = None
    for attempt in range(1, MAX_RETRY + 1):
        try:
            res = session.get(
                URL,
                params={"query": query, "analyze_type": "exact", "size": 10},
                headers={"Authorization": f"KakaoAK {key}"},
                timeout=TIMEOUT_SECONDS,
            )
        except requests.RequestException as e:
            last_error = hide_key(e, key)
            time.sleep(attempt)
            continue
        if res.status_code == 200:
            return res.json().get("documents", [])
        if res.status_code == 401:
            raise StopAll("키가 맞지 않습니다 (401). .env의 KAKAO_REST_API_KEY가 REST API 키인지 확인해 주세요.")
        if res.status_code == 403:
            raise StopAll("권한이 없습니다 (403). 카카오 개발자 콘솔에서 그 앱의 카카오맵 사용 설정을 켰는지 확인해 주세요.")
        if res.status_code == 429:
            raise StopAll("호출 한도에 걸렸습니다 (429). 내일 같은 명령으로 다시 돌리면 남은 것부터 합니다.")
        last_error = f"응답 코드 {res.status_code}"
        time.sleep(attempt)
    raise RuntimeError(f"{MAX_RETRY}번 시도했지만 실패했습니다: {last_error}")


def to_coord(text):
    """카카오의 좌표 글자를 소수점 아래 7자리로 맞춘다 (DECIMAL(10,7))."""
    return Decimal(str(text)).quantize(Decimal("0.0000001"), rounding=ROUND_HALF_UP)


def region_of(doc):
    """후보의 (시도, 구) 이름. 지번 주소를 먼저 보고, 없으면 도로명 주소를 본다."""
    part = doc.get("address") or doc.get("road_address") or {}
    return part.get("region_1depth_name", ""), part.get("region_2depth_name", "")


def inside_gwangju(lat, lng):
    return LAT_MIN <= lat <= LAT_MAX and LNG_MIN <= lng <= LNG_MAX


def pick(docs, gu):
    """조건에 맞는 첫 후보. (좌표, 없을 때의 이유)를 돌려준다."""
    if not docs:
        return None, "결과 없음"
    other_gu, outside = [], 0
    for doc in docs:
        _, doc_gu = region_of(doc)
        try:
            lat, lng = to_coord(doc["y"]), to_coord(doc["x"])
        except (KeyError, ArithmeticError, ValueError):
            continue
        if doc_gu != gu:
            other_gu.append(doc_gu or "?")
        elif not inside_gwangju(lat, lng):
            outside += 1
        else:
            return (lat, lng, doc.get("address_name", "")), None
    if outside:
        return None, "광주 5개 구 범위 밖의 좌표"
    return None, "구가 다른 결과만 있음: " + ", ".join(sorted(set(other_gu)))


def queries_for(apt, sido):
    """(방법, 물어볼 주소)를 묻는 순서대로. sido는 "전남광주통합특별시" 같은 시도 이름이다 (new 같은 옵션 이름이 아니다)."""
    if sido not in SIDO_NAMES.values():
        raise ValueError(f"시도 이름이 아닙니다: {sido}")
    items = [("지번", f"{sido} {apt['gu']} {apt['dong']} {apt['jibun']}")]
    if apt.get("road_address"):
        items.append(("도로명", f"{sido} {apt['gu']} {apt['road_address']}"))
    return items


def geocode_one(session, key, apt, sido):
    """아파트 하나. (좌표 또는 None, 찾은 방법, 실패 이유)"""
    reasons = []
    for method, query in queries_for(apt, sido):
        docs = ask_kakao(session, key, query)
        time.sleep(SLEEP_SECONDS)
        found, reason = pick(docs, apt["gu"])
        if found:
            return found, method, None
        reasons.append(f"{method} [{query}]: {reason}")
    if not apt.get("road_address"):
        reasons.append("도로명 없음")
    return None, None, " / ".join(reasons)


# ------------------------------------------------------------------
# 4. 실행
# ------------------------------------------------------------------
def run_check(cur, key):
    """아파트 1곳을 네 가지 형식으로 물어 어느 형식이 되는지 본다 (R-06). DB를 바꾸지 않는다."""
    cur.execute(
        "SELECT id, gu, dong, jibun, name, road_address FROM apartments "
        "WHERE road_address IS NOT NULL ORDER BY id LIMIT 1"
    )
    apt = cur.fetchone()
    if not apt:
        sys.exit("DB에 아파트가 없습니다. data/load_trades.py를 먼저 돌려 주세요.")
    print(f"시험할 아파트: {apt['gu']} {apt['dong']} {apt['jibun']} {apt['name']} (도로명: {apt['road_address']})\n")
    tests = [
        ("새 이름 + 지번", f"{SIDO_NAMES['new']} {apt['gu']} {apt['dong']} {apt['jibun']}"),
        ("옛 이름 + 지번", f"{SIDO_NAMES['old']} {apt['gu']} {apt['dong']} {apt['jibun']}"),
        ("광주 + 지번", f"{SIDO_NAMES['short']} {apt['gu']} {apt['dong']} {apt['jibun']}"),
        ("새 이름 + 도로명", f"{SIDO_NAMES['new']} {apt['gu']} {apt['road_address']}"),
    ]
    session = requests.Session()
    for label, query in tests:
        docs = ask_kakao(session, key, query)
        time.sleep(SLEEP_SECONDS)
        found, reason = pick(docs, apt["gu"])
        print(f"[{label}] {query}")
        print(f"  후보 {len(docs)}개, 결과: " + (f"찾음 {found[0]}, {found[1]} ({found[2]})" if found else f"못 찾음 ({reason})"))
        if docs:
            sido, gu = region_of(docs[0])
            print(f"  카카오가 돌려준 시도 이름: {sido}, 구: {gu}")
    print("\n찾은 형식을 단체방에 알려 주세요 (R-06). 지번 형식이 되는 쪽을 --sido로 쓴다 (기본 new).")
    if docs:
        print("\n마지막 응답의 첫 후보 (참고):")
        print(json.dumps(docs[0], ensure_ascii=False, indent=2))


def run_geocode(conn, cur, key, targets, sido):
    session = requests.Session()
    failed, ok_count, done = [], 0, 0
    stop_message = None
    try:
        for apt in targets:
            found, method, reason = geocode_one(session, key, apt, sido)
            if found:
                lat, lng, address = found
                save_result(cur, apt["id"], lat, lng, "ok")
                ok_count += 1
                print(f"  ok      {apt['gu']} {apt['dong']} {apt['jibun']} {apt['name']} -> {lat}, {lng} ({method}: {address})")
            else:
                save_result(cur, apt["id"], None, None, "failed")
                failed.append({**{c: apt.get(c) or "" for c in FAILED_COLS[:-1]}, "reason": reason})
                print(f"  failed  {apt['gu']} {apt['dong']} {apt['jibun']} {apt['name']} - {reason}")
            done += 1
            if done % COMMIT_EVERY == 0:
                conn.commit()
                print(f"  ... {done:,}/{len(targets):,} 저장")
    except StopAll as e:
        stop_message = str(e)
    except RuntimeError as e:
        stop_message = hide_key(e, key)
    conn.commit()
    return ok_count, failed, done, stop_message


def run_from_file(conn, cur, path, force):
    """파일의 좌표를 DB에 넣는다. 카카오를 부르지 않는다."""
    if not os.path.exists(path):
        sys.exit(f"파일이 없습니다: {path}")
    cur.execute("SELECT id, gu, dong, jibun, name, geocode_status FROM apartments")
    ids = {(r["gu"], r["dong"], r["jibun"], r["name"]): (r["id"], r["geocode_status"]) for r in cur.fetchall()}

    saved, skipped, unknown = 0, 0, []
    with open(path, encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            key = (row["gu"], row["dong"], row["jibun"], row["name"])
            if key not in ids:
                unknown.append(key)
                continue
            apartment_id, status = ids[key]
            if status is not None and not force:
                skipped += 1
                continue
            ok = row["geocode_status"] == "ok"
            save_result(
                cur, apartment_id,
                to_coord(row["latitude"]) if ok else None,
                to_coord(row["longitude"]) if ok else None,
                "ok" if ok else "failed",
            )
            saved += 1
    conn.commit()
    cur.execute("SELECT COUNT(*) AS n FROM apartments WHERE geocode_status IS NULL")
    left = cur.fetchone()["n"]
    print(f"파일에서 넣음 {saved:,}곳, 이미 있어 건너뜀 {skipped:,}곳, DB에 없는 아파트 {len(unknown):,}곳")
    for key in unknown[:10]:
        print("  DB에 없음: " + " ".join(key))
    if left:
        print(f"아직 좌표가 없는 아파트 {left:,}곳 (파일에 없던 아파트). 필요하면 python data/geocode.py 로 그 곳만 바꾼다.")


def save_failed(cur, failed):
    """실패 목록 파일. 이번에 실패한 곳에, 앞서 실패해 DB에 아직 failed로 남은 곳을 더한다.
    여러 번에 나눠 돌려도 실패한 아파트가 파일에서 빠지지 않는다. 남은 실패 수를 돌려준다."""
    cur.execute("SELECT gu, dong, jibun, name FROM apartments WHERE geocode_status = 'failed'")
    still_failed = {(r["gu"], r["dong"], r["jibun"], r["name"]) for r in cur.fetchall()}
    key = lambda r: (r["gu"], r["dong"], r["jibun"], r["name"])

    rows = {}
    if FAILED_PATH.exists():
        with open(FAILED_PATH, encoding="utf-8-sig") as f:
            for r in csv.DictReader(f):
                if key(r) in still_failed:
                    rows[key(r)] = r
    for r in failed:
        rows[key(r)] = r  # 이번 결과가 앞의 것을 대신한다

    with open(FAILED_PATH, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=FAILED_COLS)
        writer.writeheader()
        writer.writerows(sorted(rows.values(), key=key))
    return len(rows)


def main():
    ap = argparse.ArgumentParser(description="아파트 주소를 카카오 API로 좌표로 바꿔 DB에 넣는다")
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--sido", choices=sorted(SIDO_NAMES), default="new")
    ap.add_argument("--from-file", default=None)
    args = ap.parse_args()

    from backend.database import connect
    conn = connect()
    try:
        with conn.cursor() as cur:
            if args.from_file:
                if args.dry_run:
                    sys.exit("--from-file은 --dry-run 없이 돌려 주세요. 카카오를 부르지 않습니다.")
                run_from_file(conn, cur, args.from_file, args.force)
                return

            if args.check:
                run_check(cur, load_key())
                return

            targets = read_targets(cur, args.force)
            if args.limit:
                targets = spread_by_gu(targets, args.limit)
            if not targets:
                print("바꿀 아파트가 없습니다. 모두 변환을 마쳤습니다. 다시 하려면 --force를 줍니다.")
                return
            with_road = sum(1 for t in targets if t.get("road_address"))
            print(f"좌표로 바꿀 아파트 {len(targets):,}곳 (주소 앞: {SIDO_NAMES[args.sido]})")
            print(f"카카오 호출: 최소 {len(targets):,}번, 최대 {len(targets) + with_road:,}번 (지번으로 못 찾으면 도로명으로 한 번 더)")
            if args.dry_run:
                print("--dry-run이라 카카오를 부르지 않고 DB를 바꾸지 않았습니다.")
                return

            key = load_key()
            ok_count, failed, done, stop_message = run_geocode(conn, cur, key, targets, SIDO_NAMES[args.sido])
            exported = export_geocoded(cur)
            failed_total = save_failed(cur, failed)
    finally:
        conn.close()

    print(f"\n결과: {done:,}곳 중 성공 {ok_count:,}곳, 실패 {len(failed):,}곳")
    if failed_total:
        print(f"실패 목록: {FAILED_PATH.relative_to(BASE_DIR)} (지금까지 실패한 {failed_total:,}곳. 지도에는 나오지 않고 목록에만 나온다)")
    print(f"팀 공유 파일: {GEOCODED_PATH.relative_to(BASE_DIR)} ({exported:,}곳)")
    if stop_message:
        sys.exit(f"\n멈춤: {stop_message}")


if __name__ == "__main__":
    main()
