"""아파트의 세대수를 건축물대장에서 받아 apartments.households에 넣는다. 담당: 김목산

DB 설계서 5장의 9번(세대수를 붙인다), 요구사항 FR-DATA-13, FR-APT-15.
아파트는 data/load_trades.py가 먼저 DB에 넣어 두어야 한다.
화면과 서버는 건축물대장을 부르지 않고 이 스크립트가 넣은 세대수만 읽는다 (NFR-08).

준비물
  1. .env 파일에 공공데이터포털 인증키:  DATA_GO_KR_KEY=일반인증키(Decoding)
     공공데이터포털에서 "국토교통부_건축HUB_건축물대장정보 서비스"를 활용신청해 두어야 한다.
  2. 법정동코드 파일: 행정표준코드관리시스템(code.go.kr) → 법정동코드 전체자료를 내려받아 압축을 푼 txt.
     기본 자리는 data/법정동코드 전체자료.txt 이다. 다른 곳이면 --codes로 알려 준다. Git에 올리지 않는다.
  .env의 DB 계정으로 접속한다 (backend.database.connect).

사용법 (프로젝트 폴더에서, 가상 환경을 켠 뒤)
  python data/load_households.py --check            시험. 아파트 1곳을 새 코드와 옛 코드로 물어본다. 파일과 DB를 바꾸지 않는다
  python data/load_households.py --dry-run          몇 곳을 몇 번 부를지만 보여 준다. API를 부르지 않고 DB를 바꾸지 않는다
  python data/load_households.py --limit 5          5곳만 받아 data/households.csv에 적고 DB에 넣는다 (구마다 고르게)
  python data/load_households.py                    남은 아파트 전부를 받아 적고 DB에 넣는다
  python data/load_households.py --from-file data/households.csv
                                                    API를 부르지 않고 파일의 세대수를 DB에 넣는다 (나머지 세 명)
  python data/load_households.py --from-file data/households.csv --dry-run
                                                    파일을 넣으면 몇 곳이 바뀌는지만 보여 준다

  --codes 경로   법정동코드 파일 (기본: data/법정동코드 전체자료.txt)
  --code-set     new(전남광주통합특별시의 코드, 기본) 또는 old(광주광역시의 옛 코드). --check 결과를 보고 되는 쪽을 쓴다.
  --force        data/households.csv에 이미 받은 번지도 다시 받는다. 평소에는 받지 않은 번지만 받는다.

세대수를 정하는 방법 (번지마다)
  1. 표제부(getBrTitleInfo)에서 주용도가 공동주택이거나 기타용도에 '아파트'가 든 동의 세대수를 더한다. 그 번지에 있는 동만 나온다.
  2. 표제부가 없으면 총괄표제부(getBrRecapTitleInfo)의 세대수를 쓴다.
     총괄표제부가 표제부 합보다 크면 쓰지 않는다. 총괄표제부는 대지 전체라서, 번지가 여럿인 대지(벽산블루밍메가씨티 1·2·3단지)에서는
     다른 번지의 단지까지 더한 값이 나온다. 총괄표제부가 표제부 합 이하이면(상가 세대 등을 뺀 값) 총괄표제부를 쓴다.
  3. 한 번지에 우리 아파트가 둘 이상이면(라인효친1·2처럼) 건물명이 그 아파트 이름과 맞는 것만 쓴다.
     맞는 것이 없으면 비운다. 남의 세대수를 붙이지 않는다.
  세대수가 0이거나 찾지 못하면 비운다(NULL). 세대수를 지어내지 않는다.
  4. 대장으로 비어 버린 곳 가운데 웹 자료로 확인한 곳은 data/households_manual.csv의 값으로 채운다 (출처 URL을 함께 적어 둔다).
     대장에 값이 있는 곳은 덮지 않는다. override 칸이 yes인 줄만 대장 값을 덮는다
     (대장 값이 한 번지의 여러 단지 합으로 나온 곳. 문흥동 971-1 현대 643 = 1차 282 + 2차 360).
     DB에 넣을 때마다 이 파일을 함께 읽는다.

넣는 곳
  apartments.households      넣을 때마다 전부 비우고 파일의 값으로 다시 붙인다 (DB 설계서 5장 9번)
  data_collections           dataset 'households', 기준일은 받은 날. 마지막 줄과 기준일·줄 수가 같으면 더하지 않는다

남기는 파일
  data/households.csv        받은 결과 (구, 동, 지번, 아파트명, 세대수, 구한 방법, 총괄표제부 합, 표제부 합, 받은 날).
                             전체를 받은 뒤 저장소에 올려 팀이 나눠 쓴다. 두 합을 남겨 두어 API를 다시 부르지 않고도 고른 까닭을 볼 수 있다.
                             아파트를 받을 때마다 한 줄씩 적으므로, 중간에 멈춰도 다시 돌리면 남은 것부터 받는다.
  data/households_manual.csv 사람이 웹 자료로 확인해 적은 세대수와 출처 (구, 동, 지번, 아파트명, 세대수, 덮어쓰기, 확실성, 출처, 메모, 확인한 날).
                             이 스크립트는 읽기만 한다.

규칙
  - 키는 .env에서 읽는다. 화면과 파일에 출력하지 않고, 오류 문장에 섞여 나와도 가린다.
  - 호출 사이에 0.2초 쉰다. 하루 호출 한도에 걸리거나 키가 틀리면 그때까지 받은 것을 남기고 멈춘다.
"""
import argparse
import csv
import os
import re
import sys
import time
from datetime import date
from pathlib import Path

import requests

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

BASE_URL = "https://apis.data.go.kr/1613000/BldRgstHubService"
SIDO_NAMES = {"new": "전남광주통합특별시", "old": "광주광역시"}
TARGET_GU = ["동구", "서구", "남구", "북구", "광산구"]

ROWS_PER_PAGE = 100
SLEEP_SECONDS = 0.2
MAX_RETRY = 3
TIMEOUT_SECONDS = 30

CODES_PATH = BASE_DIR / "data" / "법정동코드 전체자료.txt"
OUT_PATH = BASE_DIR / "data" / "households.csv"
MANUAL_PATH = BASE_DIR / "data" / "households_manual.csv"
OUT_COLS = ["gu", "dong", "jibun", "name", "households", "method", "recap_households", "title_households", "collected_on"]
SOURCE = "건축물대장 (국토교통부 건축HUB)"


class StopAll(Exception):
    """키가 틀렸거나 하루 호출 한도에 걸려 더 물어도 소용없을 때."""


# ------------------------------------------------------------------
# 1. 키와 코드
# ------------------------------------------------------------------
def load_key():
    """.env의 DATA_GO_KR_KEY. backend.config를 불러오면 .env 전체가 환경 변수로 올라온다."""
    import backend.config  # noqa: F401
    key = os.environ.get("DATA_GO_KR_KEY", "").strip()
    if not key:
        sys.exit(".env 파일에 DATA_GO_KR_KEY=인증키 를 넣어 주세요. 프로젝트 폴더에서 실행했는지도 확인해 주세요.")
    return key


def hide_key(text, key):
    """오류 문장에 키가 섞여 나오지 않게 가린다."""
    return str(text).replace(key, "***") if key else str(text)


def load_codes(path):
    """법정동코드 파일에서 (시도, 구, 동) → (시군구코드 5자리, 법정동코드 5자리) 표를 만든다.

    파일은 탭으로 나뉜 '법정동코드  법정동명  폐지여부' 세 칸이다. 내려받은 파일은 cp949인 경우가 많다.
    폐지된 코드도 남긴다. 옛 코드(--code-set old)는 폐지로 적혀 있을 수 있다.
    """
    if not Path(path).exists():
        sys.exit(f"법정동코드 파일이 없습니다: {path}\n"
                 "code.go.kr에서 '법정동코드 전체자료'를 내려받아 압축을 풀고, data/ 폴더에 두거나 --codes로 알려 주세요.")
    for encoding in ("utf-8-sig", "cp949"):
        try:
            lines = Path(path).read_text(encoding=encoding).splitlines()
            break
        except UnicodeDecodeError:
            continue
    else:
        sys.exit(f"법정동코드 파일을 읽지 못했습니다: {path}")
    codes = {}
    for line in lines[1:]:
        cells = [c.strip() for c in line.split("\t")]
        if len(cells) < 2 or not re.fullmatch(r"\d{10}", cells[0]):
            continue
        parts = cells[1].split()
        if len(parts) != 3:  # 시도 구 동 세 단어인 것만 (리가 붙은 것, 구까지인 것은 뺀다)
            continue
        alive = len(cells) < 3 or cells[2] == "존재"
        key = tuple(parts)
        if key not in codes or alive:  # 같은 이름이 여럿이면 존재하는 쪽을 쓴다
            codes[key] = (cells[0][:5], cells[0][5:])
    return codes


def parse_jibun(jibun):
    """'506-8' → (0, 506, 8), '산1-9' → (1, 1, 9), '1869' → (0, 1869, 0). 숫자가 아니면 None"""
    m = re.fullmatch(r"(산)?\s*(\d+)(?:-(\d+))?", jibun.strip())
    if not m:
        return None
    return (1 if m.group(1) else 0, int(m.group(2)), int(m.group(3) or 0))


# ------------------------------------------------------------------
# 2. 건축물대장 API
# ------------------------------------------------------------------
def fetch(key, operation, lot):
    """한 번지의 대장을 모두 받는다 (여러 쪽이면 이어서). lot: {sigungu, bjdong, plat, bun, ji}"""
    rows, page = [], 1
    while True:
        params = {
            "serviceKey": key, "sigunguCd": lot["sigungu"], "bjdongCd": lot["bjdong"],
            "platGbCd": str(lot["plat"]), "bun": f"{lot['bun']:04d}", "ji": f"{lot['ji']:04d}",
            "numOfRows": ROWS_PER_PAGE, "pageNo": page, "_type": "json",
        }
        items, total = fetch_page(key, f"{BASE_URL}/{operation}", params)
        rows.extend(items)
        if not items or len(rows) >= total:
            return rows
        page += 1
        time.sleep(SLEEP_SECONDS)


def fetch_page(key, url, params):
    last_error = ""
    for attempt in range(1, MAX_RETRY + 1):
        try:
            res = requests.get(url, params=params, timeout=TIMEOUT_SECONDS)
            text = res.text
            # 한도 초과와 키 오류는 XML로 오는 경우가 있다
            if "LIMITED_NUMBER_OF_SERVICE_REQUESTS_EXCEEDS" in text:
                raise StopAll("하루 호출 한도에 도달했습니다. 내일 같은 명령으로 다시 실행하면 남은 것부터 받습니다.")
            if "SERVICE_KEY_IS_NOT_REGISTERED" in text or "SERVICE KEY IS NOT REGISTERED" in text:
                raise StopAll("인증키가 등록되지 않았습니다. 건축HUB 건축물대장정보 서비스의 활용신청 상태와 키(Decoding)를 확인해 주세요.")
            if res.status_code in (401, 403):
                raise StopAll(f"인증키가 거부되었습니다 ({res.status_code}). 활용신청 상태와 키(Decoding)를 확인해 주세요.")
            res.raise_for_status()
            body = res.json()["response"]
            code = str(body["header"]["resultCode"])
            if code not in ("00", "0"):
                raise RuntimeError(f"resultCode {code}: {body['header'].get('resultMsg')}")
            items = body["body"].get("items") or {}
            items = items.get("item", []) if isinstance(items, dict) else []
            if isinstance(items, dict):  # 한 건이면 목록이 아니라 하나로 온다
                items = [items]
            return items, int(body["body"].get("totalCount") or 0)
        except StopAll:
            raise
        except Exception as e:  # 네트워크 오류, 형식 오류
            last_error = hide_key(f"{type(e).__name__}: {e}", key)
            time.sleep(2 * attempt)
    raise RuntimeError(last_error)


def to_int(value):
    try:
        return int(str(value).strip() or 0)
    except ValueError:
        return 0


def norm_name(text):
    """이름 맞춰 보기용. 빈칸, 괄호 안, '아파트', 영문 대소문자 차이를 없앤다"""
    text = re.sub(r"\(.*?\)", "", str(text or "")).lower()
    return re.sub(r"\s+|아파트", "", text)


def norm_building(text):
    """건물명 끝의 동 번호를 뗀다. '현대 2동', '현대아파트 제201동' → '현대'. 동 번호가 단지 번호(현대2)와 섞이지 않게"""
    text = re.sub(r"(제)?\s*[0-9]+\s*동\s*$", "", str(text or ""))
    return norm_name(text)


def assign_shared(names, items):
    """한 번지에 단지가 여럿일 때 대장의 줄마다 이름이 가장 잘 맞는 단지 하나에 준다.

    같음 > 단지 이름이 건물명에 들어 있음(긴 이름이 앞) > 건물명이 단지 이름에 들어 있음.
    가장 잘 맞는 단지가 둘이면 어느 쪽에도 주지 않는다.
    """
    picked = {name: [] for name in names}
    for item in items:
        b = norm_building(item.get("bldNm"))
        if not b:
            continue
        scores = []
        for name in names:
            a = norm_name(name)
            if not a:
                continue
            if a == b:
                scores.append(((3, len(a)), name))
            elif a in b:
                scores.append(((2, len(a)), name))
            elif b in a:
                scores.append(((1, -len(a)), name))
        if not scores:
            continue
        scores.sort(reverse=True)
        if len(scores) > 1 and scores[0][0] == scores[1][0]:
            continue
        picked[scores[0][1]].append(item)
    return picked


def is_housing(item):
    """표제부의 동 하나가 아파트(공동주택)인가"""
    return "공동주택" in str(item.get("mainPurpsCdNm") or "") or "아파트" in str(item.get("etcPurps") or "")


def decide(names, recap, title):
    """한 번지의 대장으로 그 번지에 있는 우리 아파트마다 (세대수, 구한 방법, 총괄표제부 합, 표제부 합)을 정한다.

    names: 그 번지의 우리 아파트 이름들. recap: 총괄표제부 목록. title: 표제부 목록.
    한 번지에 아파트가 하나면 그 번지 전체, 둘 이상이면 건물명이 맞는 것만 쓴다.
    표제부 합을 먼저 쓰고, 총괄표제부는 표제부가 없거나 표제부 합 이하일 때만 쓴다 (맨 위 설명의 1, 2).
    """
    recap = [r for r in recap if to_int(r.get("hhldCnt")) > 0]
    title = [t for t in title if is_housing(t) and to_int(t.get("hhldCnt")) > 0]
    result = {}
    shared_recap = assign_shared(names, recap) if len(names) > 1 else None
    shared_title = assign_shared(names, title) if len(names) > 1 else None
    for name in names:
        if len(names) == 1:
            pick_recap, pick_title = recap, title
        else:
            pick_recap, pick_title = shared_recap[name], shared_title[name]
        recap_sum = sum(to_int(r["hhldCnt"]) for r in pick_recap) or None
        title_sum = sum(to_int(t["hhldCnt"]) for t in pick_title) or None
        if recap_sum and (title_sum is None or recap_sum <= title_sum):
            result[name] = (recap_sum, "recap", recap_sum, title_sum)
        elif title_sum:
            # 총괄표제부가 없거나, 표제부 합보다 커서 다른 번지까지 더한 값일 때
            result[name] = (title_sum, "title", recap_sum, title_sum)
        elif len(names) > 1 and (recap or title):
            result[name] = (None, "shared_unmatched", None, None)  # 한 번지의 여러 단지를 가르지 못함
        else:
            result[name] = (None, "not_found", None, None)
    return result


# ------------------------------------------------------------------
# 3. DB와 파일
# ------------------------------------------------------------------
def read_apartments(cur):
    cur.execute("SELECT id, gu, dong, jibun, name, households FROM apartments ORDER BY id")
    return list(cur.fetchall())


def group_lots(apartments, codes, code_set):
    """아파트를 번지(구, 동, 지번)로 묶고 코드를 붙인다. 코드가 없거나 지번이 숫자가 아니면 빠진 쪽으로"""
    sido = SIDO_NAMES[code_set]
    lots, skipped = {}, []
    for a in apartments:
        parsed = parse_jibun(a["jibun"])
        code = codes.get((sido, a["gu"], a["dong"]))
        if a["gu"] not in TARGET_GU or parsed is None or code is None:
            reason = "no_code" if code is None else "bad_jibun"
            skipped.append((a, reason))
            continue
        key = (a["gu"], a["dong"], a["jibun"])
        lot = lots.setdefault(key, {"sigungu": code[0], "bjdong": code[1], "plat": parsed[0],
                                    "bun": parsed[1], "ji": parsed[2], "apartments": []})
        lot["apartments"].append(a)
    return lots, skipped


def read_header(path):
    with open(path, newline="", encoding="utf-8-sig") as f:
        return next(csv.reader(f), [])


def read_out(path):
    if not Path(path).exists():
        return []
    with open(path, newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def spread_by_gu(keys, limit):
    """구마다 돌아가며 하나씩 골라 limit곳을 만든다"""
    by_gu = {}
    for key in keys:
        by_gu.setdefault(key[0], []).append(key)
    picked = []
    while len(picked) < limit and any(by_gu.values()):
        for gu in TARGET_GU:
            if by_gu.get(gu) and len(picked) < limit:
                picked.append(by_gu[gu].pop(0))
    return picked


def apply_manual(rows, manual):
    """대장으로 비어 버린 곳을 웹 자료로 확인한 값으로 채운 새 목록과 (채운 수, 건너뛴 줄)을 돌려준다.

    대장에 값이 있는 곳은 덮지 않는다. override가 yes인 줄만 덮는다. 파일에 없는 아파트는 건너뛴다.
    받은 rows는 바꾸지 않는다.
    """
    index = {(r["gu"], r["dong"], r["jibun"], r["name"]): i for i, r in enumerate(rows)}
    merged = [dict(r) for r in rows]
    filled, skipped = 0, []
    for m in manual:
        key = (m["gu"], m["dong"], m["jibun"], m["name"])
        value = to_int(m.get("households"))
        if key not in index or value <= 0:
            skipped.append((key, "households.csv에 없는 아파트" if key not in index else "세대수가 0 이하"))
            continue
        row = merged[index[key]]
        if to_int(row["households"]) and str(m.get("override") or "").strip().lower() != "yes":
            skipped.append((key, f"대장 값 {row['households']}이 있어 덮지 않음"))
            continue
        row["households"], row["method"] = str(value), "manual"
        filled += 1
    return merged, filled, skipped


def load_into_db(conn, rows, dry_run):
    """파일의 세대수로 apartments.households를 다시 붙인다. 붙인 수와 바뀐 수를 돌려준다.

    data/households_manual.csv가 있으면 비어 버린 곳을 그 값으로 채운다 (apply_manual).
    전부 비운 뒤 다시 붙이므로 몇 번을 돌려도 결과가 같다. dry_run이면 되돌린다.
    """
    rows, manual_filled, manual_skipped = apply_manual(rows, read_out(MANUAL_PATH))
    cur = conn.cursor()
    before = {(a["gu"], a["dong"], a["jibun"], a["name"]): a["households"] for a in read_apartments(cur)}
    wanted = {}
    for r in rows:
        key = (r["gu"], r["dong"], r["jibun"], r["name"])
        value = to_int(r["households"]) or None
        if key in before:
            wanted[key] = value
    missing = sum(1 for r in rows if (r["gu"], r["dong"], r["jibun"], r["name"]) not in before)
    after = {key: wanted.get(key) for key in before}
    changed = sum(1 for key in before if before[key] != after[key])
    filled = sum(1 for v in after.values() if v is not None)

    cur.execute("UPDATE apartments SET households = NULL WHERE households IS NOT NULL")
    cur.executemany(
        "UPDATE apartments SET households = %s WHERE gu = %s AND dong = %s AND jibun = %s AND name = %s",
        [(v, *k) for k, v in wanted.items() if v is not None],
    )
    base = max((r["collected_on"] for r in rows if r.get("collected_on")), default=None)
    added = False
    if base and filled:
        cur.execute("SELECT base_date, row_count FROM data_collections WHERE dataset = 'households' ORDER BY id DESC LIMIT 1")
        last = cur.fetchone()
        if not last or str(last["base_date"]) != base or last["row_count"] != filled:
            cur.execute(
                "INSERT INTO data_collections (dataset, source, base_date, row_count) VALUES ('households', %s, %s, %s)",
                (SOURCE, base, filled),
            )
            added = True
    if dry_run:
        conn.rollback()
    else:
        conn.commit()
    return {"apartments": len(before), "filled": filled, "changed": changed, "not_in_db": missing,
            "collection_added": added, "base_date": base, "manual_filled": manual_filled, "manual_skipped": manual_skipped}


# ------------------------------------------------------------------
# 4. 실행
# ------------------------------------------------------------------
def print_load(result, dry_run):
    word = "넣으면" if dry_run else "넣음"
    print(f"DB {word}: 아파트 {result['apartments']:,}곳 중 세대수 있음 {result['filled']:,}곳, 바뀐 곳 {result['changed']:,}곳")
    if result["manual_filled"] or result["manual_skipped"]:
        print(f"  웹 자료로 채운 곳 {result['manual_filled']:,}곳 (data/households_manual.csv)")
        for key, why in result["manual_skipped"]:
            print(f"    건너뜀: {' '.join(key)} ({why})")
    if result["not_in_db"]:
        print(f"  파일에는 있지만 DB에 없는 아파트 {result['not_in_db']:,}곳 (load_trades.py를 먼저 돌렸는지 확인)")
    if result["base_date"]:
        print(f"  기준일 {result['base_date']}, data_collections {'한 줄 더함' if result['collection_added'] else '그대로 (마지막 줄과 같음)'}"
              + (" (dry-run이라 되돌림)" if dry_run else ""))


def run_check(conn, codes):
    """아파트 1곳을 새 코드와 옛 코드로 물어본다. 파일과 DB를 바꾸지 않는다"""
    key = load_key()
    apartments = read_apartments(conn.cursor())
    for code_set in ("new", "old"):
        lots, _ = group_lots(apartments, codes, code_set)
        if not lots:
            print(f"[{code_set}] 코드를 붙인 번지가 없습니다. 법정동코드 파일에 '{SIDO_NAMES[code_set]} ○○구 ○○동'이 있는지 확인해 주세요.")
            continue
        sample = next(iter(lots.values()))
        a = sample["apartments"][0]
        try:
            recap = fetch(key, "getBrRecapTitleInfo", sample)
            title = fetch(key, "getBrTitleInfo", sample)
        except (StopAll, RuntimeError) as e:
            print(f"[{code_set}] {a['gu']} {a['dong']} {a['jibun']} {a['name']}: 실패 ({hide_key(e, key)})")
            continue
        found = decide([x["name"] for x in sample["apartments"]], recap, title)
        print(f"[{code_set}] {a['gu']} {a['dong']} {a['jibun']} {a['name']} (코드 {sample['sigungu']}-{sample['bjdong']}): "
              f"총괄표제부 {len(recap)}줄, 표제부 {len(title)}줄 → 세대수 {found[a['name']][0]} ({found[a['name']][1]}, "
              f"총괄 {found[a['name']][2]}, 표제부 {found[a['name']][3]})")
    print("세대수가 나온 쪽의 --code-set을 쓰세요. 둘 다 0줄이면 활용신청과 코드 파일을 확인해 주세요.")


def run_collect(conn, codes, code_set, limit, force, dry_run):
    apartments = read_apartments(conn.cursor())
    lots, skipped = group_lots(apartments, codes, code_set)
    done_rows = [] if force else read_out(OUT_PATH)
    done = {(r["gu"], r["dong"], r["jibun"]) for r in done_rows}
    todo = [k for k in lots if k not in done]
    if limit:
        todo = spread_by_gu(todo, limit)

    print(f"아파트 {len(apartments):,}곳 → 번지 {len(lots):,}곳 (한 번지에 두 곳 이상: {sum(len(l['apartments']) > 1 for l in lots.values())}곳)")
    for gu in TARGET_GU:
        print(f"  {gu}: {sum(1 for k in lots if k[0] == gu):,}곳")
    if skipped:
        no_code = sorted({f"{a['gu']} {a['dong']}" for a, why in skipped if why == "no_code"})
        print(f"코드를 붙이지 못해 빠진 아파트 {len(skipped):,}곳"
              + (f" (법정동코드 파일에 없는 동: {', '.join(no_code[:8])}{' …' if len(no_code) > 8 else ''})" if no_code else ""))
    print(f"이미 받은 번지 {len(done):,}곳, 이번에 받을 번지 {len(todo):,}곳 → API 호출 약 {len(todo) * 2:,}번 (총괄표제부, 표제부)")
    if dry_run:
        print("dry-run: API를 부르지 않았고 파일과 DB를 바꾸지 않았습니다.")
        return

    key = load_key()
    today = date.today().isoformat()
    new_file = force or not OUT_PATH.exists()
    if not new_file and set(OUT_COLS) - set(read_header(OUT_PATH)):
        sys.exit(f"{OUT_PATH}는 예전 모양(칸이 모자람)입니다. --force로 처음부터 다시 받아 주세요.")
    stopped = None
    with open(OUT_PATH, "w" if new_file else "a", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=OUT_COLS)
        if new_file:
            writer.writeheader()
        for n, lot_key in enumerate(todo, 1):
            lot = lots[lot_key]
            names = [a["name"] for a in lot["apartments"]]
            try:
                recap = fetch(key, "getBrRecapTitleInfo", lot)
                time.sleep(SLEEP_SECONDS)
                title = fetch(key, "getBrTitleInfo", lot)
            except StopAll as e:
                stopped = str(e)
                break
            except RuntimeError as e:
                print(f"[{n}/{len(todo)}] 실패: {' '.join(lot_key)} ({e}). 다시 돌리면 이 번지부터 받습니다.")
                continue
            found = decide(names, recap, title)
            blank = lambda v: "" if v is None else v
            for a in lot["apartments"]:
                value, method, recap_sum, title_sum = found[a["name"]]
                writer.writerow({"gu": a["gu"], "dong": a["dong"], "jibun": a["jibun"], "name": a["name"],
                                 "households": blank(value), "method": method, "recap_households": blank(recap_sum),
                                 "title_households": blank(title_sum), "collected_on": today})
            f.flush()
            print(f"[{n}/{len(todo)}] {' '.join(lot_key)} " + ", ".join(f"{k} {v[0] if v[0] is not None else '-'}" for k, v in found.items()))
            time.sleep(SLEEP_SECONDS)
    if stopped:
        print(stopped)
    rows = read_out(OUT_PATH)
    print(f"저장: {OUT_PATH} ({len(rows):,}줄)")
    print_load(load_into_db(conn, rows, dry_run=False), dry_run=False)


def main():
    ap = argparse.ArgumentParser(description="건축물대장의 세대수를 apartments.households에 넣는다")
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--from-file")
    ap.add_argument("--codes", default=str(CODES_PATH))
    ap.add_argument("--code-set", choices=["new", "old"], default="new")
    args = ap.parse_args()

    from backend.database import connect
    conn = connect()
    try:
        if args.from_file:
            rows = read_out(args.from_file)
            if not rows:
                sys.exit(f"파일이 없거나 비었습니다: {args.from_file}")
            print(f"파일 {args.from_file}: {len(rows):,}줄 (세대수 있음 {sum(1 for r in rows if to_int(r['households'])):,}줄)")
            print_load(load_into_db(conn, rows, args.dry_run), args.dry_run)
            return
        codes = load_codes(args.codes)
        if args.check:
            run_check(conn, codes)
            return
        run_collect(conn, codes, args.code_set, args.limit, args.force, args.dry_run)
    finally:
        conn.close()


if __name__ == "__main__":
    main()
