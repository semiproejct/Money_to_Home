"""실거래 CSV를 읽어 apartments, trades, apartment_prices 표를 채운다. 담당: 김목산

DB 설계서 5장의 4 ~ 6번(아파트, 거래, 면적대별 평균가)과 10번(수집 기준일)을 한다.
좌표(7번)는 data/geocode.py(안세환), 공급면적(8번)은 다음 단계에서 붙인다.

읽는 파일 (둘 다 같은 열 이름이다)
  - collect_trades.py가 받은 파일:     data/collected/ 폴더
  - 실거래가 공개시스템에서 받은 CSV:   data/아파트_실거래가_정렬.csv 같은 파일. 위쪽 안내문은 건너뛴다.

사용법 (프로젝트 폴더에서, .env의 DB 계정으로 접속한다)
  python data/load_trades.py data/collected --dry-run
  python data/load_trades.py data/collected
  python data/load_trades.py data/아파트_실거래가_정렬.csv

  --dry-run      DB에 넣지 않고 읽은 결과의 건수만 보여 준다.
  --end YYYYMM   평균을 낼 마지막 계약 연월. 빼면 읽은 파일의 마지막 계약 연월
  --base-date YYYY-MM-DD   수집 기준일(자료를 받은 날). 빼면 폴더의 collected_at.txt를 쓴다.

수집 기준일 (FR-DATA-05, DB 설계서 3.7)
  data_collections에 trades 줄을 하나 남긴다 (받은 곳, 기준일, 넣은 거래 수). A-13이 가장 최근 줄을 보여 준다.
  기준일은 거래를 "받은 날"이다. collect_trades.py가 폴더에 적어 둔 collected_at.txt를 읽는다.
  공개시스템 CSV처럼 그 파일이 없으면 --base-date로 내려받은 날을 준다. 둘 다 없으면 기준일을 남기지 않고 알린다.

평균을 내는 기간 (CLAUDE.md, FR-DATA-01)
  수집과 평균의 기간이 같다. 수집 기간은 수집을 실행한 달의 전월까지 12개월이다.
  그래서 읽은 파일의 마지막 계약 연월까지 12개월로 평균을 낸다. 적재를 언제 돌려도 수집 기간과 같다.
  예: 10월에 수집한 data/collected (2025-10 ~ 2026-09) -> 2025-10-01 ~ 2026-09-30.
  공개시스템 CSV처럼 마지막 달이 덜 찬 파일을 넣을 때는 --end로 마지막 연월을 준다.
  이 기간 밖의 거래도 trades에는 넣지만 평균에는 쓰지 않는다. 화면에는 "최근 1년 실거래 평균"이라고 적는다.

바꾸는 규칙 (DB 설계서 3.4 ~ 3.6, 5.1)
  - 시군구 "전남광주통합특별시 서구 치평동"을 띄어쓰기로 나눠 둘째를 구, 셋째를 동으로 쓴다. 광주 5개 구만 넣는다.
  - 거래금액(만원) "28,000"은 쉼표를 빼고 10,000을 곱해 원 단위로 넣는다 (280000000).
  - 계약년월과 계약일을 이어 붙여 날짜로 바꾼다.
  - 해제사유발생일에 값이 있으면 해제된 거래다. 저장하되 평균에서 뺀다.
  - 거래 금액, 전용면적, 계약일 중 하나라도 없거나 숫자로 바꿀 수 없는 거래는 넣지 않고 건수를 출력한다 (FR-DATA-10).
  - 같은 아파트는 구, 동, 지번, 아파트명이 모두 같은 것이다.
  - 단지일련번호(collect_trades.py가 받은 파일에만 있다)는 고치지 않고 받은 그대로 complex_code에 넣는다.
    "29140-301"처럼 앞자리가 옛 지역 코드여도 틀린 값이 아니다.
    한 아파트에 번호가 둘 이상이거나 한 번호가 두 아파트에 붙으면, 주소와 이름으로 한 곳으로 묶고 번호는 비운다.
    (예: 서구 치평동 1171-4 금호쌍용은 번호가 29140-28과 29140-32 둘이라 한 곳으로 넣고 번호를 비운다)
  - 준공 연도와 도로명은 그 아파트의 거래에 가장 많이 나온 값을 쓴다. 도로명 "-"는 빈 값이다.

다시 실행하면
  - apartments: 있으면 고치고 없으면 넣는다. 좌표, 세대수, 이미 있는 단지 일련번호는 지우지 않는다.
  - trades: 파일에 든 구와 계약 연월의 거래를 모두 지우고 다시 넣는다 (FR-DATA-09).
  - apartment_prices: DB의 거래 중 평균 기간에 든 것으로 다시 계산해 고친다. 그 기간에 거래가 없는 조합은 지운다.
    공급면적은 건드리지 않는다.
  - data_collections: 실행할 때마다 줄을 하나 더한다 (DB 설계서 5장의 10번). 화면은 가장 최근 줄만 쓴다.
  - 전체를 한 번에 저장한다. 중간에 오류가 나면 아무것도 바뀌지 않는다.
"""
import argparse
import glob
import os
import sys
from collections import Counter
from datetime import date, timedelta
from decimal import Decimal, InvalidOperation
from pathlib import Path

import pandas as pd

# backend의 DB 연결(.env의 계정)을 그대로 쓴다.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

TARGET_GU = ["동구", "서구", "남구", "북구", "광산구"]
NEED_COLS = ["시군구", "번지", "단지명", "전용면적(㎡)", "계약년월", "계약일", "거래금액(만원)", "층", "건축년도", "도로명", "해제사유발생일"]


# ------------------------------------------------------------------
# 1. 읽기
# ------------------------------------------------------------------
def find_files(paths):
    files = []
    for path in paths:
        if os.path.isdir(path):
            files += sorted(glob.glob(os.path.join(path, "*.csv")))
        elif os.path.isfile(path):
            files.append(path)
        else:
            sys.exit(f"파일이나 폴더가 없습니다: {path}")
    files = [f for f in files if os.path.basename(f) != "failed.csv"]
    if not files:
        sys.exit("읽을 CSV가 없습니다.")
    return files


def read_trade_csv(path):
    """실거래 CSV를 읽는다. 공개시스템 파일 위쪽의 안내문은 제목 줄을 찾아 건너뛴다."""
    for enc in ("utf-8-sig", "cp949"):
        try:
            with open(path, encoding=enc) as f:
                skip = next((i for i, line in enumerate(f) if "시군구" in line and "단지명" in line), None)
            if skip is None:
                sys.exit(f"제목 줄(시군구, 단지명)을 찾지 못했습니다: {path}")
            df = pd.read_csv(path, encoding=enc, dtype=str, skiprows=skip, keep_default_na=False)
            break
        except UnicodeDecodeError:
            continue
    else:
        sys.exit(f"읽을 수 없는 파일: {path}")
    missing = [c for c in NEED_COLS if c not in df.columns]
    if missing:
        sys.exit(f"필요한 열이 없습니다: {path} {missing}")
    if "단지일련번호" not in df.columns:
        df["단지일련번호"] = ""
    df = df[NEED_COLS + ["단지일련번호"]].copy()
    df["파일"] = os.path.basename(path)
    return df


# ------------------------------------------------------------------
# 2. 정리
# ------------------------------------------------------------------
def to_int(text):
    text = str(text).replace(",", "").strip()
    return int(text) if text.lstrip("-").isdigit() else None


def to_area(text):
    try:
        value = Decimal(str(text).strip()).quantize(Decimal("0.0001"))
    except InvalidOperation:
        return None
    return value if value > 0 else None


def to_date(year_month, day):
    year_month, day = str(year_month).strip(), str(day).strip()
    if len(year_month) != 6 or not year_month.isdigit() or not day.isdigit():
        return None
    try:
        return date(int(year_month[:4]), int(year_month[4:]), int(day))
    except ValueError:
        return None


def most_common(values):
    """가장 많이 나온 값. 빈 값은 세지 않는다. 같은 수면 먼저 나온 값."""
    values = [v for v in values if v not in (None, "")]
    return Counter(values).most_common(1)[0][0] if values else None


def clean(raw):
    """광주 5개 구의 거래만 남기고 DB에 넣을 모양으로 바꾼다. (거래 목록, 뺀 건수와 이유)를 돌려준다."""
    parts = raw["시군구"].str.split()
    raw = raw.assign(gu=parts.str[1], dong=parts.str[2])
    outside = int((~raw["gu"].isin(TARGET_GU)).sum())
    raw = raw[raw["gu"].isin(TARGET_GU)]

    trades, dropped = [], Counter()
    for r in raw.to_dict("records"):
        price_manwon = to_int(r["거래금액(만원)"])
        area = to_area(r["전용면적(㎡)"])
        contract_date = to_date(r["계약년월"], r["계약일"])
        jibun = str(r["번지"]).strip()
        name = str(r["단지명"]).strip()
        if price_manwon is None or price_manwon <= 0:
            dropped["거래 금액이 없거나 숫자가 아님"] += 1
        elif area is None:
            dropped["전용면적이 없거나 숫자가 아님"] += 1
        elif contract_date is None:
            dropped["계약일이 없거나 날짜가 아님"] += 1
        elif not jibun or not name or not isinstance(r["dong"], str):
            dropped["지번, 아파트명, 동 중 빈 값"] += 1
        else:
            canceled = str(r["해제사유발생일"]).strip()
            road = str(r["도로명"]).strip()
            trades.append({
                "gu": r["gu"],
                "dong": r["dong"],
                "jibun": jibun,
                "name": name,
                "complex_code": str(r["단지일련번호"]).strip() or None,   # 받은 그대로. 고치지 않는다
                "built_year": to_int(r["건축년도"]),
                "road_address": road if road and road != "-" else None,
                "contract_date": contract_date,
                "exclusive_area": area,
                "price": price_manwon * 10000,          # 만원 -> 원
                "floor": to_int(r["층"]),
                "is_canceled": 0 if canceled in ("", "-") else 1,
                "file": r["파일"],
            })
    return trades, outside, dropped


def build_apartments(trades):
    """거래를 아파트별로 묶는다 (구, 동, 지번, 아파트명).

    단지 일련번호가 어긋나는 아파트는 한 곳으로 합치고 번호를 비운다 (DB 설계서 3.4 "확인 전에는 비운다").
      - 한 아파트에 번호가 둘 이상: 국토부는 둘로 보지만 주소와 이름이 같아 한 곳으로 넣는다.
      - 한 번호가 두 아파트에: 두 아파트 모두 번호를 비운다.
    번호를 고치거나 지어내지 않는다. 비운 아파트는 출력한다.
    """
    groups = {}
    for t in trades:
        groups.setdefault((t["gu"], t["dong"], t["jibun"], t["name"]), []).append(t)

    codes_of = {key: sorted({t["complex_code"] for t in rows if t["complex_code"]}) for key, rows in groups.items()}
    owners = {}
    for key, codes in codes_of.items():
        for code in codes:
            owners.setdefault(code, []).append(key)

    notes, apartments = [], []
    for key, rows in groups.items():
        codes = codes_of[key]
        code = codes[0] if len(codes) == 1 else None
        if len(codes) > 1:
            notes.append(f"한 아파트에 번호가 여럿이라 합침: {' '.join(key)} {codes}")
        elif code and len(owners[code]) > 1:
            notes.append(f"한 번호가 여러 아파트에 있어 비움: {' '.join(key)} {code}")
            code = None
        apartments.append({
            "gu": key[0], "dong": key[1], "jibun": key[2], "name": key[3],
            "complex_code": code,
            "built_year": most_common([t["built_year"] for t in rows]),
            "road_address": most_common([t["road_address"] for t in rows]),
        })
    if notes:
        print(f"단지 일련번호를 비운 아파트 {len(notes)}곳 (주소와 이름으로 묶어 넣는다)")
        for note in notes:
            print("  " + note)
    return apartments


def check_overlap(trades):
    """같은 구와 계약 연월이 두 파일에서 오면 거래가 두 번 들어가므로 멈춘다."""
    sources = {}
    for t in trades:
        sources.setdefault((t["gu"], t["contract_date"].strftime("%Y%m")), set()).add(t["file"])
    overlap = {k: v for k, v in sources.items() if len(v) > 1}
    if overlap:
        print("\n같은 구와 계약 연월이 여러 파일에 있습니다. 한쪽 파일만 주세요.")
        for (gu, ym), files in sorted(overlap.items())[:10]:
            print(f"  {gu} {ym}: {sorted(files)}")
        sys.exit(1)
    return sorted(sources)


# ------------------------------------------------------------------
# 3. 평균가 계산 (DB 설계서 3.6)
# ------------------------------------------------------------------
def average_period(end_month):
    """end_month(YYYYMM)까지 12개월의 (첫날, 마지막 날)."""
    year, month = int(end_month[:4]), int(end_month[4:])
    start_year, start_month = (year - 1, month + 1) if month < 12 else (year, 1)
    last = month_range(end_month)[1] - timedelta(days=1)
    return date(start_year, start_month, 1), last


def build_prices(rows, period):
    """거래(apartment_id, exclusive_area, price, contract_date, is_canceled)로 면적대별 평균가를 만든다.

    period(첫날, 마지막 날) 안의 거래만 쓴다. 면적대는 전용면적의 소수점 아래를 버린 값.
    해제된 거래는 뺀다. 평균의 원 미만은 반올림한다. 대표 전용면적은 그 면적대의 거래에 가장 많이 나온 값.
    """
    start, end = period
    groups = {}
    for apartment_id, area, price, contract_date, is_canceled in rows:
        if is_canceled or not (start <= contract_date <= end):
            continue
        area = Decimal(area)
        groups.setdefault((apartment_id, int(area)), []).append((area, int(price), contract_date))

    prices = []
    for (apartment_id, band), items in groups.items():
        values = [p for _, p, _ in items]
        n, total = len(values), sum(values)
        dates = [d for _, _, d in items]
        prices.append({
            "apartment_id": apartment_id,
            "area_band": band,
            "exclusive_area": most_common([a for a, _, _ in items]),
            "avg_price": (2 * total + n) // (2 * n),      # 원 미만 반올림
            "min_price": min(values),
            "max_price": max(values),
            "trade_count": n,
            "period_start": min(dates),
            "period_end": max(dates),
        })
    return prices


# ------------------------------------------------------------------
# 4. DB에 넣기
# ------------------------------------------------------------------
def save_apartments(cur, apartments):
    cur.executemany(
        """
        INSERT INTO apartments (complex_code, name, gu, dong, jibun, road_address, built_year)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE
            complex_code = COALESCE(VALUES(complex_code), complex_code),
            road_address = VALUES(road_address),
            built_year = VALUES(built_year)
        """,
        [(a["complex_code"], a["name"], a["gu"], a["dong"], a["jibun"], a["road_address"], a["built_year"]) for a in apartments],
    )
    cur.execute("SELECT id, gu, dong, jibun, name FROM apartments")
    return {(r["gu"], r["dong"], r["jibun"], r["name"]): r["id"] for r in cur.fetchall()}


def month_range(year_month):
    year, month = int(year_month[:4]), int(year_month[4:])
    start = date(year, month, 1)
    end = date(year + 1, 1, 1) if month == 12 else date(year, month + 1, 1)
    return start, end


def save_trades(cur, trades, ids, gu_months):
    """파일에 든 구와 계약 연월의 거래를 지우고 다시 넣는다 (FR-DATA-09)."""
    deleted = 0
    for gu, year_month in gu_months:
        start, end = month_range(year_month)
        deleted += cur.execute(
            """
            DELETE t FROM trades t
              JOIN apartments a ON a.id = t.apartment_id
             WHERE a.gu = %s AND t.contract_date >= %s AND t.contract_date < %s
            """,
            (gu, start, end),
        )
    cur.executemany(
        """
        INSERT INTO trades (apartment_id, contract_date, exclusive_area, price, floor, is_canceled)
        VALUES (%s, %s, %s, %s, %s, %s)
        """,
        [(ids[(t["gu"], t["dong"], t["jibun"], t["name"])], t["contract_date"], t["exclusive_area"],
          t["price"], t["floor"], t["is_canceled"]) for t in trades],
    )
    return deleted


def save_prices(cur, period):
    """DB의 거래 중 평균 기간에 든 것으로 평균가를 다시 계산해 고친다. 그 기간에 거래가 없는 조합은 지운다."""
    cur.execute("SELECT apartment_id, exclusive_area, price, contract_date, is_canceled FROM trades")
    rows = [(r["apartment_id"], r["exclusive_area"], r["price"], r["contract_date"], r["is_canceled"]) for r in cur.fetchall()]
    prices = build_prices(rows, period)
    cur.executemany(
        """
        INSERT INTO apartment_prices
            (apartment_id, area_band, exclusive_area, avg_price, min_price, max_price, trade_count, period_start, period_end)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE
            exclusive_area = VALUES(exclusive_area),
            avg_price = VALUES(avg_price),
            min_price = VALUES(min_price),
            max_price = VALUES(max_price),
            trade_count = VALUES(trade_count),
            period_start = VALUES(period_start),
            period_end = VALUES(period_end)
        """,
        [(p["apartment_id"], p["area_band"], p["exclusive_area"], p["avg_price"], p["min_price"], p["max_price"],
          p["trade_count"], p["period_start"], p["period_end"]) for p in prices],
    )
    keep = {(p["apartment_id"], p["area_band"]) for p in prices}
    cur.execute("SELECT id, apartment_id, area_band FROM apartment_prices")
    stale = [(r["id"],) for r in cur.fetchall() if (r["apartment_id"], r["area_band"]) not in keep]
    if stale:
        cur.executemany("DELETE FROM apartment_prices WHERE id = %s", stale)
    return len(prices), len(stale)


COLLECTED_AT = "collected_at.txt"  # collect_trades.py가 적는 받은 날
SOURCE_API = "실거래가 API"
SOURCE_CSV = "실거래가 공개시스템 CSV"


def find_base_date(paths, given):
    """수집 기준일과 받은 곳. --base-date가 있으면 그것, 없으면 collected_at.txt. 둘 다 없으면 (None, None).

    collected_at.txt는 준 폴더 안, 파일을 줬으면 그 파일이 든 폴더에서 찾는다. 있으면 API로 받은 자료다.
    """
    markers = {os.path.join(p if os.path.isdir(p) else os.path.dirname(p), COLLECTED_AT) for p in paths}
    markers = sorted(m for m in markers if os.path.isfile(m))
    if given:
        try:
            base = date.fromisoformat(given)
        except ValueError:
            sys.exit("--base-date는 YYYY-MM-DD 모양으로 적어 주세요. 예: 2026-10-12")
        return base, SOURCE_API if markers else SOURCE_CSV
    dates = []
    for marker in markers:
        with open(marker, encoding="utf-8") as f:
            try:
                dates.append(date.fromisoformat(f.read().strip()))
            except ValueError:
                sys.exit(f"{marker}의 날짜를 읽을 수 없습니다. YYYY-MM-DD 한 줄이어야 합니다.")
    if not dates:
        return None, None
    return max(dates), SOURCE_API


def save_collection(cur, base_date, source, row_count):
    """수집 기준일을 한 줄 남긴다 (DB 설계서 3.7)."""
    cur.execute(
        "INSERT INTO data_collections (dataset, source, base_date, row_count) VALUES (%s, %s, %s, %s)",
        ("trades", source, base_date, row_count),
    )


def main():
    ap = argparse.ArgumentParser(description="실거래 CSV를 DB에 넣는다")
    ap.add_argument("paths", nargs="+", help="CSV 파일이나 폴더")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--end", default=None, help="평균을 낼 마지막 계약 연월 YYYYMM. 빼면 읽은 파일의 마지막 계약 연월")
    ap.add_argument("--base-date", default=None, help="수집 기준일 YYYY-MM-DD. 빼면 폴더의 collected_at.txt")
    args = ap.parse_args()
    if args.end and (len(args.end) != 6 or not args.end.isdigit() or not 1 <= int(args.end[4:]) <= 12):
        sys.exit("--end는 YYYYMM 모양으로 적어 주세요. 예: 202609")

    files = find_files(args.paths)
    raw = pd.concat([read_trade_csv(f) for f in files], ignore_index=True)
    trades, outside, dropped = clean(raw)
    print(f"읽은 파일 {len(files)}개, 거래 {len(raw):,}건")
    print(f"  광주 5개 구 밖이라 뺀 거래 {outside:,}건")
    print(f"  값이 잘못되어 뺀 거래 {sum(dropped.values()):,}건" + "".join(f"\n    {k}: {v:,}건" for k, v in dropped.items()))
    if not trades:
        sys.exit("넣을 거래가 없습니다.")
    gu_months = check_overlap(trades)
    apartments = build_apartments(trades)
    canceled = sum(t["is_canceled"] for t in trades)
    with_code = sum(1 for a in apartments if a["complex_code"])
    months = sorted({ym for _, ym in gu_months})
    period = average_period(args.end or months[-1])
    print(f"넣을 거래 {len(trades):,}건 (해제 {canceled:,}건 포함), 계약 연월 {months[0]} ~ {months[-1]}")
    print(f"아파트 {len(apartments):,}곳 (단지 일련번호 있음 {with_code:,}곳)")
    in_period = sum(1 for t in trades if period[0] <= t["contract_date"] <= period[1])
    print(f"평균 기간 {period[0]} ~ {period[1]} (12개월), 이 기간의 거래 {in_period:,}건")
    base_date, source = find_base_date(args.paths, args.base_date)
    if base_date:
        print(f"수집 기준일 {base_date} ({source})")
    else:
        print(f"수집 기준일을 찾지 못해 남기지 않습니다. 폴더에 {COLLECTED_AT}가 없으면 --base-date로 받은 날을 주세요.")

    if args.dry_run:
        index = {(a["gu"], a["dong"], a["jibun"], a["name"]): i for i, a in enumerate(apartments)}
        rows = [(index[(t["gu"], t["dong"], t["jibun"], t["name"])], t["exclusive_area"], t["price"],
                 t["contract_date"], t["is_canceled"]) for t in trades]
        print(f"면적대별 평균가 {len(build_prices(rows, period)):,}줄 (이 파일의 거래만으로 계산)")
        print("--dry-run이라 DB에 넣지 않았습니다.")
        return

    from backend.database import connect
    conn = connect()
    try:
        with conn.cursor() as cur:
            ids = save_apartments(cur, apartments)
            deleted = save_trades(cur, trades, ids, gu_months)
            price_count, stale = save_prices(cur, period)
            if base_date:
                save_collection(cur, base_date, source, len(trades))
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
    print(f"\nDB에 넣었습니다. 아파트 {len(apartments):,}곳, 거래 {len(trades):,}건 (지운 예전 거래 {deleted:,}건), "
          f"면적대별 평균가 {price_count:,}줄 (지운 조합 {stale:,}줄)"
          + (f", 수집 기준일 {base_date}" if base_date else ""))


if __name__ == "__main__":
    main()
