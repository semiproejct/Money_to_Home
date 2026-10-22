"""아파트마다 주변 시설(지하철역 · 학교 · 대형마트 · 편의점 · 병원 · 버스정류장)을 카카오 로컬 API로 찾아 apartment_facilities에 넣는다.

요구사항 FR-MAP-23 (와이어프레임 C6). 화면 모양은 안세환, 미리 받아 두는 방식은 2026-10-19 팀장 결정.
아파트와 좌표는 data/load_trades.py, data/geocode.py가 먼저 DB에 넣어 두어야 한다.
화면과 서버는 카카오를 부르지 않고 이 스크립트가 넣은 값만 읽는다 (NFR-08). 바뀐 시설은 이 스크립트를 다시 돌려 반영한다.

준비물
  .env 파일에 REST API 키:  KAKAO_REST_API_KEY=카카오_REST_API_키   (data/geocode.py와 같은 키)
  .env의 DB 계정으로 접속한다 (backend.database.connect).

사용법 (프로젝트 폴더에서, 가상 환경을 켠 뒤)
  python data/load_facilities.py --check            시험. 아파트 1곳을 찾아 화면에 보여 준다. 파일과 DB를 바꾸지 않는다
  python data/load_facilities.py --dry-run          몇 곳을 몇 번쯤 부를지만 보여 준다. 카카오를 부르지 않고 DB를 바꾸지 않는다
  python data/load_facilities.py --limit 5          5곳만 찾아 data/facilities.csv에 적고 DB에 넣는다 (구마다 고르게)
  python data/load_facilities.py                    남은 아파트 전부를 찾아 적고 DB에 넣는다. 돌리기 전에 단체방에 알린다
  python data/load_facilities.py --from-file data/facilities.csv
                                                    카카오를 부르지 않고 파일의 값을 DB에 넣는다 (나머지 세 명).
                                                    버스정류장 표(bus_stops)도 data/bus_stops_gwangju.csv로 같이 채운다

  python data/load_facilities.py --add-bus         버스정류장 줄을 data/bus_stops_gwangju.csv로 다시 계산해 넣는다 (2026-10-20 더함).
                                                    카카오를 부르지 않는다. 몇 초면 끝나고 몇 번을 돌려도 결과가 같다. --dry-run과 같이 쓸 수 있다.
                                                    버스정류장 표(bus_stops)도 같이 채운다
  python data/load_facilities.py --make-bus-stops 전국버스정류장위치정보.csv
                                                    국토교통부 「전국 버스정류장 위치정보」(공공데이터포털 15067528, CP949 CSV)에서
                                                    광주광역시만 골라 data/bus_stops_gwangju.csv를 만든다. 원본은 크므로(약 20MB) 저장소에 올리지 않는다

  --force       data/facilities.csv에 이미 있는 아파트도 다시 찾는다 (시설을 최신으로 바꿀 때). 평소에는 없는 아파트만 찾는다.

찾는 것 (아파트 좌표에서 직선거리, 가까운 순)
  kind         반경    방법
  subway       1km    지하철역(SW8) 가운데 가장 가까운 역. 그 역의 1 ~ 8번 출구를 이름으로 찾아("○○역 5번출구") 가장 가까운 출구 번호와 거리
                       출구를 못 찾으면 출구 번호를 비우고 역까지의 거리
  school       1km    학교(SC4) 가운데 가장 가까운 곳
  mart         1km    대형마트(MT1)
  convenience  1km    편의점(CS2)
  hospital     1km    병원(HP8). 분류 이름에 '동물'이 든 곳(동물병원)은 뺀다
  elementary   1km    학교(SC4)에서 "초등학교"로 찾고 분류 이름에 초등학교가 든 곳
  middle       1km    중학교, 같은 방법
  high         1km    고등학교, 같은 방법
  university   5km    대학교, 같은 방법. 1km 안에는 거의 없어 5km
  bus          1km    data/bus_stops_gwangju.csv(광주BIS 정류장 4,267곳) 가운데 직선거리로 가장 가까운 곳 (2026-10-20 더함).
                       카카오 장소 검색은 시내버스 정류장을 돌려주지 않아(시외버스 정류장만 나옴) 국토교통부 자료로 계산한다.
                       지도는 정류장 표(bus_stops, A-28)를 모두 띄우고, 이 줄은 정류장 표를 못 읽을 때만 대신 쓴다. place_count는 1km 안의 정류장 수
  반경 안에 없으면 이름과 거리를 비운다 (화면은 "근처에 없음"). 시설을 지어내지 않는다.
  place_count는 반경 안의 수(카카오의 total_count). 병원은 받은 쪽(최대 45곳)에서 동물병원을 뺀 수다.
  latitude, longitude는 그 곳의 좌표다. 지하철역은 가장 가까운 출구의 좌표 (2026-10-19 더함. 지도에서 아파트와 점선으로 잇는다).

넣는 곳
  apartment_facilities   넣을 때마다 전부 지우고 파일의 값으로 다시 넣는다. 몇 번을 돌려도 결과가 같다
  bus_stops              data/bus_stops_gwangju.csv의 정류장 전부 (2026-10-20 더함). 지도가 화면 안 정류장을 A-28로 읽는다.
                         --from-file, --add-bus 때 전부 지우고 다시 넣는다. 표가 없으면 db/schema.sql의 bus_stops 부분을 먼저 실행한다
  data_collections       dataset 'facilities', 기준일은 받은 날 가운데 가장 늦은 날. 마지막 줄과 기준일·줄 수가 같으면 더하지 않는다
                         버스정류장 표는 dataset 'bus_stops', 기준일은 정류장 자료의 수집일. 같은 규칙

남기는 파일
  data/facilities.csv    받은 결과 (구, 동, 지번, 아파트명, 종류, 이름, 거리, 출구, 수, 반경, 위도, 경도, 받은 날).
                         아파트를 찾을 때마다 적으므로 중간에 멈춰도 다시 돌리면 남은 것부터 찾는다.
                         전체를 받은 뒤 저장소에 올려 팀이 나눠 쓴다. 시험(--limit) 때 생긴 것은 올리지 않는다.

규칙
  - 키는 .env에서 읽는다. 화면과 파일에 출력하지 않고, 오류 문장에 섞여 나와도 가린다.
  - 호출 사이에 0.05초 쉰다. 아파트 한 곳에 10 ~ 12번, 1km 안에 역이 있으면 8번 더 부른다.
  - 키가 틀렸거나(401, 403) 호출 한도에 걸리면(429) 그때까지 받은 것을 남기고 멈춘다.
"""
import argparse
import csv
import math
import os
import re
import sys
import time
from datetime import date
from pathlib import Path

import requests

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

CATEGORY_URL = "https://dapi.kakao.com/v2/local/search/category.json"
KEYWORD_URL = "https://dapi.kakao.com/v2/local/search/keyword.json"

RADIUS = 1000
UNIVERSITY_RADIUS = 5000
SKIP_WORD = "동물"  # 카카오의 병원 분류에는 동물병원도 들어 있다
EXIT_NUMBERS = 8  # 지하철역은 1 ~ 8번 출구를 찾는다
HOSPITAL_PAGES = 3  # 병원은 동물병원을 빼고 세려고 15곳씩 3쪽(최대 45곳)까지 받는다

# (kind, 분류 코드) 분류로 찾는 다섯 가지. subway는 출구를 따로 찾는다
CATEGORY_KINDS = [("subway", "SW8"), ("school", "SC4"), ("mart", "MT1"), ("convenience", "CS2"), ("hospital", "HP8")]
# (kind, 찾는 말, 반경) 학교 종류별. 학교 분류(SC4)에서 이 말로 찾고, 분류 이름에 같은 말이 든 곳만 쓴다
SCHOOL_KINDS = [
    ("elementary", "초등학교", RADIUS),
    ("middle", "중학교", RADIUS),
    ("high", "고등학교", RADIUS),
    ("university", "대학교", UNIVERSITY_RADIUS),
]
CALLS_PER_APARTMENT = 14  # --dry-run에 보여 줄 어림. 분류 5 + 학교 4 + 병원 쪽 1 + 역이 가까운 곳의 출구 8

# 버스정류장 (2026-10-20). 국토교통부 「전국 버스정류장 위치정보」에서 광주만 고른 파일. 카카오를 부르지 않는다
BUS_STOPS_PATH = BASE_DIR / "data" / "bus_stops_gwangju.csv"
BUS_STOPS_COLS = ["stop_id", "name", "latitude", "longitude", "collected_on"]
BUS_CITY = "광주광역시"  # 원본의 도시명
EARTH_RADIUS_M = 6371000

SLEEP_SECONDS = 0.05
MAX_RETRY = 3
TIMEOUT_SECONDS = 10

OUT_PATH = BASE_DIR / "data" / "facilities.csv"
OUT_COLS = ["gu", "dong", "jibun", "name", "kind", "place_name", "distance", "exit_no", "place_count", "radius",
            "latitude", "longitude", "collected_on"]
SOURCE = "카카오 로컬 API (장소 검색)"
BUS_SOURCE = "국토교통부 전국 버스정류장 위치정보"
NO_TABLE = 1146  # MariaDB: 표가 없다


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
# 2. 카카오에 묻기
# ------------------------------------------------------------------
def ask(session, key, url, params):
    """한 번 묻고 (documents, meta)를 돌려준다. 키 · 권한 · 한도 문제면 StopAll."""
    last_error = None
    for attempt in range(1, MAX_RETRY + 1):
        time.sleep(SLEEP_SECONDS)
        try:
            res = session.get(url, params=params, headers={"Authorization": f"KakaoAK {key}"}, timeout=TIMEOUT_SECONDS)
        except requests.RequestException as e:
            last_error = hide_key(e, key)
            time.sleep(attempt)
            continue
        if res.status_code == 200:
            body = res.json()
            return body.get("documents", []), body.get("meta", {})
        if res.status_code == 401:
            raise StopAll("키가 맞지 않습니다 (401). .env의 KAKAO_REST_API_KEY가 REST API 키인지 확인해 주세요.")
        if res.status_code == 403:
            raise StopAll("권한이 없습니다 (403). 카카오 개발자 콘솔에서 그 앱의 카카오맵 사용 설정을 켰는지 확인해 주세요.")
        if res.status_code == 429:
            raise StopAll("호출 한도에 걸렸습니다 (429). 내일 같은 명령으로 다시 돌리면 남은 것부터 합니다.")
        last_error = f"응답 코드 {res.status_code}"
        time.sleep(attempt)
    raise RuntimeError(f"{MAX_RETRY}번 시도했지만 실패했습니다: {last_error}")


def near_params(apartment, radius):
    return {"x": str(apartment["longitude"]), "y": str(apartment["latitude"]), "radius": radius, "sort": "distance"}


def found(kind, radius, place=None, count=0, distance=None, exit_no=None, point=None):
    """CSV 한 줄의 값 부분. place가 없으면 반경 안에 없는 것이다.
    point는 (경도, 위도) 글자. 없으면 그 곳의 좌표. 지하철역은 출구의 좌표를 넘긴다 (지도에서 아파트와 잇는 점선의 끝)"""
    x, y = point if point else ((place.get("x"), place.get("y")) if place else ("", ""))
    return {
        "kind": kind,
        "place_name": place["place_name"] if place else "",
        "distance": "" if place is None else str(int(distance if distance is not None else place["distance"])),
        "exit_no": "" if exit_no is None else str(exit_no),
        "place_count": str(count),
        "radius": str(radius),
        "latitude": y or "",
        "longitude": x or "",
    }


def nearest_exit(session, key, apartment, station):
    """역에서 가장 가까운 출구 (번호, 거리 m, 경도, 위도). 못 찾으면 None.

    카카오의 역 이름은 "김대중컨벤션센터역 광주1호선", 출구 이름은 "김대중컨벤션센터역 광주1호선 5번출구"다.
    "○○역 출구"로는 출구가 나오지 않아 "○○역 1번출구" ~ "○○역 8번출구"를 하나씩 묻는다 (광주1호선은 6번까지).
    지하철출구 분류이고 그 역 이름으로 시작하며 번호가 맞는 곳의 아파트에서의 거리 가운데 가장 가까운 것.
    """
    station_name = station["place_name"].split(" ")[0]
    best = None
    for number in range(1, EXIT_NUMBERS + 1):
        params = {"query": f"{station_name} {number}번출구", "x": str(apartment["longitude"]),
                  "y": str(apartment["latitude"]), "sort": "distance", "size": 5}
        docs, _ = ask(session, key, KEYWORD_URL, params)
        for place in docs:
            name = place.get("place_name", "")
            if ("지하철출구" in place.get("category_name", "") and name.startswith(station_name)
                    and re.search(rf"\s{number}번\s*출구$", name)):
                distance = int(place["distance"])
                if best is None or distance < best[1]:
                    best = (number, distance, place.get("x"), place.get("y"))
                break
    return best


def by_category(session, key, apartment, kind, code):
    """분류로 찾은 가장 가까운 곳. 병원은 동물병원을 빼고 세고 고른다"""
    params = {**near_params(apartment, RADIUS), "category_group_code": code}
    if kind != "hospital":
        docs, meta = ask(session, key, CATEGORY_URL, params)
        place = docs[0] if docs else None
        count = int(meta.get("total_count", len(docs)))
    else:
        kept, skipped, total = [], 0, 0
        for page in range(1, HOSPITAL_PAGES + 1):
            docs, meta = ask(session, key, CATEGORY_URL, {**params, "page": page})
            total = int(meta.get("total_count", 0))
            for doc in docs:
                if SKIP_WORD in doc.get("category_name", ""):
                    skipped += 1
                else:
                    kept.append(doc)
            if meta.get("is_end", True):
                break
        place = kept[0] if kept else None
        count = max(total - skipped, len(kept))
    if place is None:
        return found(kind, RADIUS)
    if kind == "subway":
        exit_found = nearest_exit(session, key, apartment, place)
        if exit_found:
            return found(kind, RADIUS, place, count, distance=exit_found[1], exit_no=exit_found[0],
                         point=(exit_found[2], exit_found[3]))
    return found(kind, RADIUS, place, count)


def by_school(session, key, apartment, kind, word, radius):
    """학교 종류별 가장 가까운 곳. 이름으로 찾고 분류 이름에 같은 말이 든 곳만"""
    params = {**near_params(apartment, radius), "query": word, "category_group_code": "SC4"}
    docs, meta = ask(session, key, KEYWORD_URL, params)
    matched = [doc for doc in docs if word in doc.get("category_name", "")]
    if not matched:
        return found(kind, radius)
    return found(kind, radius, matched[0], int(meta.get("total_count", len(matched))))


def collect_one(session, key, apartment):
    """아파트 한 곳의 아홉 줄 (값 부분). 버스정류장은 카카오가 아니라 파일로 따로 계산한다 (run_add_bus)"""
    rows = [by_category(session, key, apartment, kind, code) for kind, code in CATEGORY_KINDS]
    rows += [by_school(session, key, apartment, kind, word, radius) for kind, word, radius in SCHOOL_KINDS]
    return rows


# ------------------------------------------------------------------
# 2-1. 버스정류장 (파일로 계산. 카카오를 부르지 않는다)
# ------------------------------------------------------------------
def make_bus_stops(source):
    """국토교통부 「전국 버스정류장 위치정보」 CSV(CP949)에서 광주만 골라 BUS_STOPS_PATH로 쓴다"""
    with open(source, newline="", encoding="cp949") as f:
        rows = [r for r in csv.DictReader(f) if r.get("도시명") == BUS_CITY]
    if not rows:
        sys.exit(f"{source}에 {BUS_CITY} 정류장이 없습니다. 국토교통부 전국 버스정류장 위치정보 파일인지 확인해 주세요.")
    with open(BUS_STOPS_PATH, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow(BUS_STOPS_COLS)
        for r in rows:
            writer.writerow([r["정류장번호"], r["정류장명"], r["위도"], r["경도"], r["정보수집일"]])
    print(f"저장: {BUS_STOPS_PATH} ({BUS_CITY} 정류장 {len(rows):,}곳)")


def read_bus_stops():
    """[(이름, 위도, 경도, 수집일)]. 파일이 없으면 멈춘다"""
    if not BUS_STOPS_PATH.exists():
        sys.exit(f"{BUS_STOPS_PATH}이 없습니다. --make-bus-stops로 먼저 만들어 주세요.")
    with open(BUS_STOPS_PATH, newline="", encoding="utf-8-sig") as f:
        return [(r["name"], float(r["latitude"]), float(r["longitude"]), r["collected_on"]) for r in csv.DictReader(f)]


def meters_between(lat1, lng1, lat2, lng2):
    """두 좌표 사이의 직선거리(m). 하버사인 공식"""
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = p2 - p1, math.radians(lng2 - lng1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * EARTH_RADIUS_M * math.asin(math.sqrt(a))


def nearest_bus(apartment, stops):
    """아파트에서 가장 가까운 버스정류장 (값 부분). 반경(1km) 안에 없으면 비운다"""
    lat, lng = float(apartment["latitude"]), float(apartment["longitude"])
    near = []
    for name, s_lat, s_lng, _ in stops:
        if abs(s_lat - lat) > 0.01 or abs(s_lng - lng) > 0.012:  # 1km보다 확실히 먼 곳은 계산하지 않는다
            continue
        distance = meters_between(lat, lng, s_lat, s_lng)
        if distance <= RADIUS:
            near.append((distance, name, s_lat, s_lng))
    if not near:
        return found("bus", RADIUS)
    distance, name, s_lat, s_lng = min(near)
    place = {"place_name": name, "x": f"{s_lng:.7f}", "y": f"{s_lat:.7f}", "distance": round(distance)}
    return found("bus", RADIUS, place, len(near))


# ------------------------------------------------------------------
# 3. 파일과 DB
# ------------------------------------------------------------------
def read_apartments(cur):
    """좌표가 있는 아파트"""
    cur.execute(
        "SELECT id, gu, dong, jibun, name, latitude, longitude FROM apartments "
        "WHERE latitude IS NOT NULL AND longitude IS NOT NULL ORDER BY id"
    )
    return list(cur.fetchall())


def apartment_key(row):
    return (row["gu"], row["dong"], row["jibun"], row["name"])


def read_out(path):
    if not Path(path).exists():
        return []
    with open(path, newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def write_out(rows):
    """파일 전체를 다시 쓴다 (아파트 순서 그대로)"""
    with open(OUT_PATH, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=OUT_COLS)
        writer.writeheader()
        writer.writerows(rows)


def spread_by_gu(apartments, limit):
    """구마다 돌아가며 하나씩 골라 limit곳을 만든다"""
    by_gu = {}
    for row in apartments:
        by_gu.setdefault(row["gu"], []).append(row)
    picked = []
    while len(picked) < limit and any(by_gu.values()):
        for gu in sorted(by_gu):
            if by_gu[gu] and len(picked) < limit:
                picked.append(by_gu[gu].pop(0))
    return picked


def to_int(value):
    return int(value) if str(value or "").strip() else None


def to_coord(value):
    """카카오의 좌표 글자를 소수점 아래 7자리로 (DECIMAL(10,7)). 없으면 None (예전 CSV에는 좌표 칸이 없다)"""
    text = str(value or "").strip()
    return round(float(text), 7) if text else None


def load_into_db(conn, rows, dry_run):
    """파일의 값으로 apartment_facilities를 다시 채운다. 전부 지운 뒤 넣으므로 몇 번을 돌려도 결과가 같다"""
    cur = conn.cursor()
    ids = {apartment_key(a): a["id"] for a in read_apartments(cur)}
    values = []
    missing = set()
    for r in rows:
        apartment_id = ids.get(apartment_key(r))
        if apartment_id is None:
            missing.add(apartment_key(r))
            continue
        values.append((
            apartment_id, r["kind"], r["place_name"] or None, to_int(r["distance"]), to_int(r["exit_no"]),
            to_int(r["place_count"]) or 0, to_int(r["radius"]), to_coord(r.get("latitude")), to_coord(r.get("longitude")),
        ))
    cur.execute("DELETE FROM apartment_facilities")
    cur.executemany(
        "INSERT INTO apartment_facilities (apartment_id, kind, place_name, distance, exit_no, place_count, radius, latitude, longitude) "
        "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)",
        values,
    )
    base = max((r["collected_on"] for r in rows if r.get("collected_on")), default=None)
    added = False
    if base and values:
        cur.execute("SELECT base_date, row_count FROM data_collections WHERE dataset = 'facilities' ORDER BY id DESC LIMIT 1")
        last = cur.fetchone()
        if not last or str(last["base_date"]) != base or last["row_count"] != len(values):
            cur.execute(
                "INSERT INTO data_collections (dataset, source, base_date, row_count) VALUES ('facilities', %s, %s, %s)",
                (SOURCE, base, len(values)),
            )
            added = True
    if dry_run:
        conn.rollback()
    else:
        conn.commit()
    return {"rows": len(values), "apartments": len({v[0] for v in values}), "not_in_db": len(missing),
            "base_date": base, "collection_added": added}


def load_bus_stops_table(conn, dry_run):
    """data/bus_stops_gwangju.csv로 bus_stops 표를 다시 채운다 (A-28). 전부 지운 뒤 넣으므로 몇 번을 돌려도 결과가 같다"""
    if not BUS_STOPS_PATH.exists():
        print(f"버스정류장 표: {BUS_STOPS_PATH.name}이 없어 건너뜀 (--make-bus-stops로 만든다)")
        return
    with open(BUS_STOPS_PATH, newline="", encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))
    values = [(r["stop_id"], r["name"], to_coord(r["latitude"]), to_coord(r["longitude"])) for r in rows]
    cur = conn.cursor()
    try:
        cur.execute("DELETE FROM bus_stops")
    except Exception as error:  # 표를 아직 만들지 않은 DB
        if error.args and error.args[0] == NO_TABLE:
            conn.rollback()
            print("버스정류장 표: bus_stops 표가 없습니다. HeidiSQL에서 db/schema.sql의 bus_stops 부분(CREATE TABLE)을 먼저 실행해 주세요.")
            return
        raise
    cur.executemany("INSERT INTO bus_stops (stop_id, name, latitude, longitude) VALUES (%s, %s, %s, %s)", values)
    base = max((r["collected_on"] for r in rows if r.get("collected_on")), default=None)
    added = False
    if base and values:
        cur.execute("SELECT base_date, row_count FROM data_collections WHERE dataset = 'bus_stops' ORDER BY id DESC LIMIT 1")
        last = cur.fetchone()
        if not last or str(last["base_date"]) != base or last["row_count"] != len(values):
            cur.execute(
                "INSERT INTO data_collections (dataset, source, base_date, row_count) VALUES ('bus_stops', %s, %s, %s)",
                (BUS_SOURCE, base, len(values)),
            )
            added = True
    if dry_run:
        conn.rollback()
    else:
        conn.commit()
    word = "넣으면" if dry_run else "넣음"
    print(f"버스정류장 표 {word}: {len(values):,}곳, 기준일 {base}, data_collections {'한 줄 더함' if added else '그대로 (마지막 줄과 같음)'}"
          + (" (dry-run이라 되돌림)" if dry_run else ""))


# ------------------------------------------------------------------
# 4. 실행
# ------------------------------------------------------------------
def print_load(result, dry_run):
    word = "넣으면" if dry_run else "넣음"
    print(f"DB {word}: 아파트 {result['apartments']:,}곳, {result['rows']:,}줄")
    if result["not_in_db"]:
        print(f"  파일에는 있지만 DB에 없거나 좌표가 없는 아파트 {result['not_in_db']:,}곳")
    if result["base_date"]:
        print(f"  기준일 {result['base_date']}, data_collections {'한 줄 더함' if result['collection_added'] else '그대로 (마지막 줄과 같음)'}"
              + (" (dry-run이라 되돌림)" if dry_run else ""))


def run_check(conn, key):
    apartments = read_apartments(conn.cursor())
    if not apartments:
        sys.exit("좌표가 있는 아파트가 없습니다. data/geocode.py를 먼저 돌려 주세요.")
    apartment = spread_by_gu(apartments, 1)[0]
    print(f"시험: {apartment['gu']} {apartment['dong']} {apartment['name']} (파일과 DB는 바꾸지 않음)")
    with requests.Session() as session:
        values = collect_one(session, key, apartment)
    if BUS_STOPS_PATH.exists():
        values.append(nearest_bus(apartment, read_bus_stops()))
    for row in values:
        where = f"{row['place_name']} {row['distance']}m" if row["place_name"] else "근처에 없음"
        exit_text = f" ({row['exit_no']}번 출구)" if row["exit_no"] else ""
        print(f"  {row['kind']:<12} {where}{exit_text} · {int(row['radius']) // 1000}km 안 {row['place_count']}곳")


def run_collect(conn, key, limit, force, dry_run):
    apartments = read_apartments(conn.cursor())
    done_rows = [] if force else read_out(OUT_PATH)
    done = {apartment_key(r) for r in done_rows}
    todo = [a for a in apartments if apartment_key(a) not in done]
    if limit:
        todo = spread_by_gu(todo, limit)
    print(f"좌표가 있는 아파트 {len(apartments):,}곳, 이미 받은 곳 {len(done):,}곳, 이번에 찾을 곳 {len(todo):,}곳"
          f" (카카오 약 {len(todo) * CALLS_PER_APARTMENT:,}번)")
    if dry_run:
        return
    today = date.today().isoformat()
    todo_keys = {apartment_key(a) for a in todo}
    rows = [r for r in read_out(OUT_PATH) if apartment_key(r) not in todo_keys]  # 다시 찾는 아파트의 옛 줄만 뺀다
    stopped = None
    with requests.Session() as session:
        for index, apartment in enumerate(todo, start=1):
            try:
                values = collect_one(session, key, apartment)
            except StopAll as e:
                stopped = str(e)
                break
            except RuntimeError as e:
                print(f"  건너뜀: {apartment['gu']} {apartment['dong']} {apartment['name']} ({e})")
                continue
            base = {"gu": apartment["gu"], "dong": apartment["dong"], "jibun": apartment["jibun"], "name": apartment["name"]}
            rows += [{**base, **value, "collected_on": today} for value in values]
            if index % 20 == 0 or index == len(todo):
                write_out(rows)
                print(f"  {index:,} / {len(todo):,}곳")
    write_out(rows)
    print(f"저장: {OUT_PATH} ({len(rows):,}줄)")
    if stopped:
        print(f"멈춤: {stopped}")
    print_load(load_into_db(conn, rows, dry_run=False), dry_run=False)


def run_add_bus(conn, dry_run):
    """facilities.csv의 버스정류장 줄을 정류장 파일로 모두 다시 계산한다 (예전 버스 줄은 버린다). 다른 줄은 그대로 둔다"""
    rows = [r for r in read_out(OUT_PATH) if r["kind"] != "bus"]
    if not rows:
        sys.exit(f"{OUT_PATH}이 없습니다. 먼저 전체를 받거나(--limit 없이) 팀이 올린 파일을 받아 주세요.")
    stops = read_bus_stops()
    done = {apartment_key(r) for r in rows}
    apartments = [a for a in read_apartments(conn.cursor()) if apartment_key(a) in done]
    collected = max(stop[3] for stop in stops)
    values = []
    for apartment in apartments:
        base = {"gu": apartment["gu"], "dong": apartment["dong"], "jibun": apartment["jibun"], "name": apartment["name"]}
        values.append({**base, **nearest_bus(apartment, stops), "collected_on": collected})
    near = sum(1 for v in values if v["place_name"])
    print(f"버스정류장: 정류장 {len(stops):,}곳(수집일 {collected}), 아파트 {len(values):,}곳 가운데 1km 안에 있는 곳 {near:,}곳")
    if dry_run:
        return
    rows = sort_rows(rows + values)
    write_out(rows)
    print(f"저장: {OUT_PATH} ({len(rows):,}줄)")
    print_load(load_into_db(conn, rows, dry_run=False), dry_run=False)


def sort_rows(rows):
    """아파트 순서는 그대로 두고, 아파트마다 버스정류장 줄을 그 아파트의 줄 끝에 모은다"""
    order = {}
    for r in rows:
        order.setdefault(apartment_key(r), len(order))
    return sorted(rows, key=lambda r: (order[apartment_key(r)], r["kind"] == "bus"))


def main():
    ap = argparse.ArgumentParser(description="주변 시설을 카카오 로컬 API로 찾아 apartment_facilities에 넣는다")
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--from-file")
    ap.add_argument("--add-bus", action="store_true")
    ap.add_argument("--make-bus-stops")
    args = ap.parse_args()

    if args.make_bus_stops:
        make_bus_stops(args.make_bus_stops)  # DB와 카카오를 쓰지 않는다
        return

    from backend.database import connect
    conn = connect()
    try:
        if args.from_file:
            rows = read_out(args.from_file)
            if not rows:
                sys.exit(f"파일이 없거나 비었습니다: {args.from_file}")
            print(f"파일 {args.from_file}: {len(rows):,}줄")
            print_load(load_into_db(conn, rows, args.dry_run), args.dry_run)
            load_bus_stops_table(conn, args.dry_run)
            return
        if args.add_bus:
            run_add_bus(conn, args.dry_run)  # 카카오를 부르지 않으므로 키가 없어도 된다
            load_bus_stops_table(conn, args.dry_run)
            return
        if args.dry_run:
            run_collect(conn, None, args.limit, args.force, dry_run=True)
            return
        key = load_key()
        if args.check:
            run_check(conn, key)
            return
        run_collect(conn, key, args.limit, args.force, dry_run=False)
    finally:
        conn.close()


if __name__ == "__main__":
    main()
