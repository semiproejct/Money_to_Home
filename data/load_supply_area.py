"""구별 대장대조 CSV의 공급면적을 apartment_prices에 붙인다. 담당: 김목산

DB 설계서 5장 8번, 3.6. 요구사항 FR-DATA-12, T-DATA-14.
load_trades.py로 아파트와 평균가를 넣은 뒤에 실행한다.

읽는 파일
  data/아파트_실거래가_<구>대장대조.csv  거래 한 줄마다 공급면적과 구한 방법(비고)이 붙은 파일

사용법 (프로젝트 폴더에서)
  python data/load_supply_area.py --dry-run
  python data/load_supply_area.py
  python data/load_supply_area.py data/아파트_실거래가_서구대장대조.csv   (파일을 직접 줄 때)

  --dry-run   DB를 바꾸지 않고 몇 줄에 붙는지만 보여 준다.

규칙
  - 아파트는 구, 동, 지번, 아파트명으로 찾는다. 이름이 달라 못 찾으면, 그 지번에 아파트가 한 곳뿐일 때만 지번으로 찾는다.
  - 면적대(전용면적의 소수점 아래를 버린 값)마다 거래에 가장 많이 나온 공급면적을 넣는다 (DB 설계서 3.6).
    같은 수로 나온 값이 둘 이상이면 큰 값을 쓴다 (CSV 비고의 "큰 값 통일"과 같은 기준).
  - 구한 방법은 비고의 문구를 아래 이름으로 바꿔 넣는다. 문구가 없거나 공급면적이 비면 둘 다 비운다.
  - 공급면적이 대표 전용면적보다 크지 않으면 넣지 않고 출력한다 (표의 CHECK 제약).
  - 다시 실행하면 전부 비운 뒤 다시 붙인다. 한 번에 저장하므로 오류가 나면 아무것도 바뀌지 않는다.
  - load_trades.py를 다시 돌려 새 면적대가 생기면 이 스크립트도 다시 돌린다.
"""
import argparse
import glob
import os
import sys
from collections import Counter
from decimal import Decimal, InvalidOperation
from pathlib import Path

import pandas as pd

# backend의 DB 연결(.env의 계정)을 그대로 쓴다.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

TARGET_GU = ["동구", "서구", "남구", "북구", "광산구"]
DEFAULT_GLOB = os.path.join("data", "아파트_실거래가_*대장대조*.csv")

# 비고의 둘째 문구 -> supply_area_method (DB 설계서 3.6)
METHODS = {
    "대장 주거공용 합산 추정": "ledger_sum",
    "식별 가능한 주거공용만 합산 추정(미분류 항목 제외)": "ledger_partial",
    "대장 공용용도 해석 추정": "ledger_inferred",
    "동일 주소·유사 전용면적 다른 세대 공용면적 차용 추정": "borrowed",
    "기존 공급면적 유지·정수 올림(원출처 재검증 안 함)": "legacy",
}


def read_ledger_csv(path):
    """대장대조 CSV를 읽는다. 위쪽 안내문은 제목 줄을 찾아 건너뛴다."""
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
    missing = [c for c in ("시군구", "번지", "단지명", "전용면적(㎡)", "공급면적(㎡)", "비고") if c not in df.columns]
    if missing:
        sys.exit(f"필요한 열이 없습니다: {path} {missing}")
    return df


def method_of(note):
    """비고 "추정치; 대장 주거공용 합산 추정; ..."에서 구한 방법의 이름을 찾는다. 없으면 None."""
    parts = [p.strip() for p in str(note).split(";")]
    return METHODS.get(parts[1]) if len(parts) > 1 else None


def to_decimal(text):
    try:
        value = Decimal(str(text).strip())
    except InvalidOperation:
        return None
    return value if value > 0 else None


def collect_supply(files):
    """(구, 동, 지번, 이름, 면적대) -> (가장 많이 나온 공급면적, 그 공급면적의 방법)"""
    counts = {}
    for path in files:
        df = read_ledger_csv(path)
        parts = df["시군구"].str.split()
        df = df.assign(gu=parts.str[1], dong=parts.str[2])
        for r in df[df["gu"].isin(TARGET_GU)].to_dict("records"):
            area, supply, method = to_decimal(r["전용면적(㎡)"]), to_decimal(r["공급면적(㎡)"]), method_of(r["비고"])
            if area is None or supply is None or method is None:
                continue
            key = (r["gu"], r["dong"], str(r["번지"]).strip(), str(r["단지명"]).strip(), int(area))
            counts.setdefault(key, []).append((supply, method))
    result = {}
    for key, values in counts.items():
        # 가장 많이 나온 공급면적을 고르고, 그 공급면적에 가장 많이 붙은 방법을 쓴다.
        # 같은 수로 나온 값이 둘 이상이면 큰 값을 쓴다 (CSV 비고의 "큰 값 통일"과 같은 기준). 방법도 같은 수면 이름순.
        supply = max(Counter(v for v, _ in values).items(), key=lambda kv: (kv[1], kv[0]))[0]
        method = max(Counter(m for v, m in values if v == supply).items(), key=lambda kv: (kv[1], kv[0]))[0]
        result[key] = (supply, method)
    return result


def match(supply, apartments):
    """CSV의 아파트를 DB의 아파트 번호로 바꾼다. (apartment_id, 면적대) -> (공급면적, 방법)"""
    by_name = {(a["gu"], a["dong"], a["jibun"], a["name"]): a["id"] for a in apartments}
    by_jibun = {}
    for a in apartments:
        by_jibun.setdefault((a["gu"], a["dong"], a["jibun"]), []).append(a["id"])

    result, by_jibun_used, missing = {}, set(), set()
    for (gu, dong, jibun, name, band), value in supply.items():
        apartment_id = by_name.get((gu, dong, jibun, name))
        if apartment_id is None:
            ids = by_jibun.get((gu, dong, jibun), [])
            if len(ids) == 1:
                apartment_id = ids[0]
                by_jibun_used.add((gu, dong, jibun, name))
            else:
                missing.add((gu, dong, jibun, name))
                continue
        result[(apartment_id, band)] = value
    return result, by_jibun_used, missing


def main():
    ap = argparse.ArgumentParser(description="공급면적을 apartment_prices에 붙인다")
    ap.add_argument("paths", nargs="*", help="대장대조 CSV. 빼면 data/아파트_실거래가_*대장대조*.csv")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    files = []
    for path in args.paths or [DEFAULT_GLOB]:
        found = sorted(glob.glob(path)) if any(ch in path for ch in "*?[") else [path]
        files += [f for f in found if os.path.isfile(f)]
    if not files:
        sys.exit("읽을 대장대조 CSV가 없습니다.")
    supply = collect_supply(files)
    print(f"읽은 파일 {len(files)}개, 공급면적이 있는 아파트·면적대 {len(supply):,}개")

    from backend.database import connect
    conn = connect()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT id, gu, dong, jibun, name FROM apartments")
            apartments = cur.fetchall()
            cur.execute("SELECT id, apartment_id, area_band, exclusive_area FROM apartment_prices")
            prices = cur.fetchall()
            if not prices:
                sys.exit("apartment_prices가 비어 있습니다. load_trades.py를 먼저 실행해 주세요.")

            matched, by_jibun_used, missing = match(supply, apartments)
            updates, too_small = [], []
            for p in prices:
                value = matched.get((p["apartment_id"], p["area_band"]))
                if value is None:
                    continue
                area, method = value
                if area <= Decimal(p["exclusive_area"]):
                    too_small.append((p["apartment_id"], p["area_band"], p["exclusive_area"], area))
                    continue
                updates.append((area, method, p["id"]))

            methods = Counter(u[1] for u in updates)
            print(f"이름이 달라 지번으로 찾은 아파트 {len(by_jibun_used):,}곳, 찾지 못한 아파트 {len(missing):,}곳")
            for gu, dong, jibun, name in sorted(missing)[:10]:
                print(f"  찾지 못함: {gu} {dong} {jibun} {name}")
            for apartment_id, band, rep, area in too_small[:10]:
                print(f"  공급면적이 전용면적보다 작아 뺌: 아파트 {apartment_id} 면적대 {band} (전용 {rep}, 공급 {area})")
            print(f"면적대별 평균가 {len(prices):,}줄 중 공급면적을 붙일 줄 {len(updates):,}줄 "
                  f"({len(updates) / len(prices):.0%}), 비울 줄 {len(prices) - len(updates):,}줄")
            print("  구한 방법: " + ", ".join(f"{m} {n:,}" for m, n in sorted(methods.items())))

            if args.dry_run:
                print("--dry-run이라 DB를 바꾸지 않았습니다.")
                return
            cur.execute("UPDATE apartment_prices SET supply_area = NULL, supply_area_method = NULL")
            cur.executemany("UPDATE apartment_prices SET supply_area = %s, supply_area_method = %s WHERE id = %s", updates)
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
    print("\nDB에 붙였습니다.")


if __name__ == "__main__":
    main()
