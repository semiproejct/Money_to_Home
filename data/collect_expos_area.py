"""실거래에 나온 광주시 아파트의 번지만 골라 건축물대장 전유공용면적을 API로 수집한다.

준비물
  1. .env 파일에 인증키:  DATA_GO_KR_KEY=발급받은_일반인증키(Decoding)
  2. 실거래가 공개시스템에서 받은 아파트 매매 CSV
  3. 행정표준코드관리시스템(code.go.kr)에서 받은 "법정동코드 전체자료.txt"

사용법
  python collect_expos_area.py --trades 실거래.csv --codes "법정동코드 전체자료.txt" --dry-run
  python collect_expos_area.py --trades 실거래.csv --codes "법정동코드 전체자료.txt" --out expos

  --dry-run   조회할 번지의 수만 확인하고 API를 부르지 않는다.
  --limit N   이번 실행에서 번지 N곳만 조회한다. (처음에 3~5로 시험)
  --out 폴더  결과를 저장할 폴더. 다시 실행하면 끝난 번지는 건너뛴다.

결과
  <폴더>/expos_area.csv   build_supply_area.py가 읽는 형식 (동별 내려받기 파일과 같은 열 이름)
  <폴더>/done.txt         조회를 마친 번지
  <폴더>/failed.csv       실패한 번지와 이유
"""
import argparse
import csv
import os
import sys
import time

import pandas as pd
import requests

URL = "https://apis.data.go.kr/1613000/BldRgstHubService/getBrExposPubuseAreaInfo"
TARGET_GU = ["동구", "서구", "남구", "북구", "광산구"]
ROWS_PER_PAGE = 100
SLEEP_SECONDS = 0.2          # 호출 사이의 간격
MAX_RETRY = 3

# API 응답 항목 -> build_supply_area.py가 쓰는 열 이름
FIELD_MAP = {
    "platPlc": "대지위치",
    "sigunguCd": "시군구코드",
    "bjdongCd": "법정동코드",
    "bun": "번",
    "ji": "지",
    "mgmBldrgstPk": "관리건축물대장PK",
    "newPlatPlc": "도로명대지위치",
    "bldNm": "건물명",
    "dongNm": "동명칭",
    "hoNm": "호명칭",
    "exposPubuseGbCdNm": "전유공용구분코드명",
    "mainAtchGbCdNm": "주부속구분코드명",
    "mainPurpsCdNm": "주용도코드명",
    "etcPurps": "기타용도",
    "area": "면적(㎡)",
}
OUT_COLS = list(FIELD_MAP.values())


class DailyLimitReached(Exception):
    pass


def load_key():
    key = os.environ.get("DATA_GO_KR_KEY")
    if not key and os.path.exists(".env"):
        for line in open(".env", encoding="utf-8"):
            if line.strip().startswith("DATA_GO_KR_KEY="):
                key = line.split("=", 1)[1].strip().strip('"').strip("'")
    if not key:
        sys.exit(".env 파일에 DATA_GO_KR_KEY=인증키 를 넣어 주세요.")
    return key


def read_csv_any(path, **kw):
    for enc in ("utf-8-sig", "cp949"):
        try:
            return pd.read_csv(path, encoding=enc, dtype=str, **kw)
        except UnicodeDecodeError:
            continue
    sys.exit(f"읽을 수 없는 파일: {path}")


def load_trades(path):
    """실거래 CSV에서 광주시 5개 구의 아파트 번지 목록을 만든다."""
    # 실거래가 공개시스템 파일은 위쪽에 안내문이 있다. 제목 줄을 찾아 그 아래부터 읽는다.
    skip = 0
    for enc in ("utf-8-sig", "cp949"):
        try:
            with open(path, encoding=enc) as f:
                for i, line in enumerate(f):
                    if "시군구" in line and "단지명" in line:
                        skip = i
                        break
            break
        except UnicodeDecodeError:
            continue
    df = read_csv_any(path, skiprows=skip)
    df["구"] = df["시군구"].str.split().str[1]
    df = df[df["구"].isin(TARGET_GU)]
    lots = df.drop_duplicates(["시군구", "번지", "단지명"])[["시군구", "번지", "본번", "부번", "단지명"]].copy()
    lots["산"] = lots["번지"].fillna("").str.strip().str.startswith("산")
    return lots.reset_index(drop=True)


def load_codes(path):
    """법정동코드 전체자료에서 '법정동명 -> (시군구코드, 법정동코드)' 표를 만든다."""
    df = read_csv_any(path, sep="\t")
    df.columns = [c.strip() for c in df.columns]
    if "폐지여부" in df.columns:
        df = df[df["폐지여부"].str.strip() == "존재"]
    code = df["법정동코드"].str.strip()
    name = df["법정동명"].str.split().str.join(" ")
    return {n: (c[:5], c[5:]) for n, c in zip(name, code)}


def attach_codes(lots, codes):
    names = lots["시군구"].str.split().str.join(" ")
    lots["시군구코드"] = [codes.get(n, (None, None))[0] for n in names]
    lots["법정동코드"] = [codes.get(n, (None, None))[1] for n in names]
    missing = lots[lots["시군구코드"].isna()]["시군구"].unique()
    if len(missing):
        print(f"코드를 찾지 못한 동 {len(missing)}곳 (법정동코드 파일의 이름과 다름): {list(missing)[:5]}")
    return lots[lots["시군구코드"].notna()].copy()


def fetch_page(key, lot, page):
    params = {
        "serviceKey": key,
        "sigunguCd": lot["시군구코드"],
        "bjdongCd": lot["법정동코드"],
        "platGbCd": "1" if lot["산"] else "0",
        "bun": str(lot["본번"]).zfill(4),
        "ji": str(lot["부번"]).zfill(4),
        "numOfRows": ROWS_PER_PAGE,
        "pageNo": page,
        "_type": "json",
    }
    last_error = ""
    for attempt in range(1, MAX_RETRY + 1):
        try:
            res = requests.get(URL, params=params, timeout=30)
            text = res.text
            # 한도 초과와 키 오류는 XML로 돌아오는 경우가 있다.
            if "LIMITED_NUMBER_OF_SERVICE_REQUESTS_EXCEEDS" in text:
                raise DailyLimitReached()
            if "SERVICE_KEY_IS_NOT_REGISTERED" in text or "SERVICE KEY IS NOT REGISTERED" in text:
                sys.exit("인증키가 등록되지 않았습니다. 활용 신청 상태와 키(Decoding)를 확인해 주세요.")
            res.raise_for_status()
            body = res.json()["response"]
            code = str(body["header"]["resultCode"])
            if code not in ("00", "0"):
                raise RuntimeError(f"resultCode {code}: {body['header'].get('resultMsg')}")
            items = body["body"].get("items") or {}
            items = items.get("item", []) if isinstance(items, dict) else []
            if isinstance(items, dict):      # 한 건이면 목록이 아니라 하나로 온다.
                items = [items]
            return items, int(body["body"].get("totalCount", 0))
        except DailyLimitReached:
            raise
        except Exception as e:               # 네트워크 오류, 형식 오류
            last_error = f"{type(e).__name__}: {e}"
            time.sleep(2 * attempt)
    raise RuntimeError(last_error)


def fetch_lot(key, lot):
    rows, page = [], 1
    while True:
        items, total = fetch_page(key, lot, page)
        rows.extend(items)
        if not items or len(rows) >= total:
            return rows
        page += 1
        time.sleep(SLEEP_SECONDS)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--trades", required=True)
    ap.add_argument("--codes", required=True)
    ap.add_argument("--out", default="expos")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    lots = attach_codes(load_trades(args.trades), load_codes(args.codes))
    lots["key"] = lots["시군구코드"] + "-" + lots["법정동코드"] + "-" + lots["본번"].str.zfill(4) + "-" + lots["부번"].str.zfill(4)
    lots = lots.drop_duplicates("key")
    print(f"조회할 번지 {len(lots):,}곳")
    print(lots.groupby(lots["시군구"].str.split().str[1]).size().to_string())
    if args.dry_run:
        return

    key = load_key()
    os.makedirs(args.out, exist_ok=True)
    out_path = os.path.join(args.out, "expos_area.csv")
    done_path = os.path.join(args.out, "done.txt")
    fail_path = os.path.join(args.out, "failed.csv")
    done = set(open(done_path, encoding="utf-8").read().split()) if os.path.exists(done_path) else set()
    todo = lots[~lots["key"].isin(done)]
    if args.limit:
        todo = todo.head(args.limit)
    print(f"이미 끝난 번지 {len(done):,}곳, 이번에 조회할 번지 {len(todo):,}곳")

    new_file = not os.path.exists(out_path)
    with open(out_path, "a", newline="", encoding="utf-8-sig") as f_out, \
         open(done_path, "a", encoding="utf-8") as f_done, \
         open(fail_path, "a", newline="", encoding="utf-8-sig") as f_fail:
        writer = csv.DictWriter(f_out, fieldnames=OUT_COLS)
        if new_file:
            writer.writeheader()
        fail = csv.writer(f_fail)
        for n, (_, lot) in enumerate(todo.iterrows(), 1):
            try:
                rows = fetch_lot(key, lot)
            except DailyLimitReached:
                print("하루 호출 한도에 도달했습니다. 내일 같은 명령으로 다시 실행하면 이어서 받습니다.")
                break
            except Exception as e:
                fail.writerow([lot["key"], lot["시군구"], lot["번지"], lot["단지명"], str(e)])
                print(f"[{n}/{len(todo)}] 실패: {lot['단지명']} ({e})")
                continue
            for item in rows:
                writer.writerow({ko: item.get(en, "") for en, ko in FIELD_MAP.items()})
            f_out.flush()
            f_done.write(lot["key"] + "\n")
            f_done.flush()
            print(f"[{n}/{len(todo)}] {lot['단지명']}: {len(rows):,}줄")
            time.sleep(SLEEP_SECONDS)
    print(f"저장: {out_path}")


if __name__ == "__main__":
    main()
