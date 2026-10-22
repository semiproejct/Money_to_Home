"""국토교통부 아파트 매매 실거래가 API로 광주시 5개 구의 거래를 수집한다. 담당: 김목산

먼저 --test로 시험 호출을 해서 응답 항목을 확인한다 (roles.md 3.3-1, 요구사항 R-03).
되면 전체를 수집하고, 안 되면 data/의 실거래가 공개시스템 CSV를 그대로 쓴다.

준비물
  .env 파일에 인증키:  DATA_GO_KR_KEY=발급받은_일반인증키(Decoding)
  공공데이터포털에서 "국토교통부_아파트 매매 실거래가 상세 자료" 활용 신청

사용법 (프로젝트 폴더에서)
  python data/collect_trades.py --test
  python data/collect_trades.py
  python data/collect_trades.py --only 12240-202609 12300-202608

  --test        서구의 지난달 거래 한 페이지만 불러 응답 항목을 보여 준다. 저장하지 않는다.
  --codes 파일  행정표준코드관리시스템(code.go.kr)의 "법정동코드 전체자료.txt"에서
                5개 구의 지역 코드를 찾아 쓴다. 코드가 다시 바뀌었을 때 준다.
  --code 구=코드  지역 코드를 직접 준다. 여러 개를 줄 수 있다. 예: --code 서구=12240
                --codes보다 먼저 쓴다. 둘 다 없으면 아래 GU_CODES(광주 5개 구 코드)를 쓴다.
                코드가 다시 바뀌었을 때만 쓴다. 평소에는 둘 다 주지 않는다.
  --end YYYYMM  수집할 마지막 계약 연월. 빼면 실행한 달의 전월 (FR-DATA-01)
  --months N    --end부터 거슬러 올라가 몇 달을 받을지. 기본 12
  --only ...    이 구 코드와 계약 연월만 다시 받는다. 실패한 것만 다시 받을 때 쓴다.
  --out 폴더    결과를 저장할 폴더. 기본 data/collected
  --force       이미 받은 구와 계약 연월도 다시 받는다.

결과
  <폴더>/<구코드>_<계약연월>.csv  구와 계약 연월 하나에 파일 하나. 다 받은 것만 저장한다.
                                  열 이름은 실거래가 공개시스템 CSV와 같고, 단지일련번호와 해제여부가 더 있다.
  <폴더>/failed.csv               실패한 구와 계약 연월, 이유 (FR-DATA-08)
  <폴더>/collected_at.txt         마지막으로 받은 날. load_trades.py가 수집 기준일로 남긴다 (FR-DATA-05)

규칙
  - 응답의 결과 코드가 정상이 아니거나, 받은 건수가 전체 건수와 다르면 저장하지 않는다 (FR-DATA-07, 08).
  - 인증키는 화면과 파일에 출력하지 않는다.
  - 받은 값은 고치지 않고 그대로 저장한다. 바꾸는 일은 적재 스크립트(load_trades.py)가 한다.
      거래금액(만원): "28,000"처럼 쉼표가 있는 만원 단위 글자다. 적재할 때 쉼표를 빼고 10,000을 곱해
                      원 단위로 넣는다 (280000000, DB 설계서 5.1).
      단지일련번호:   "29140-301"처럼 앞자리가 옛 지역 코드인 채로 온다. 단지에 한 번 붙인 번호를 바꾸지 않은
                      것이라 틀린 값이 아니다. 고치거나 앞자리를 지역 코드로 쓰지 않고, 받은 그대로
                      apartments.complex_code에 넣어 같은 아파트를 묶는 열쇠로 쓴다.
  - 잘못된 거래를 빼는 일도 적재 스크립트가 한다 (FR-DATA-10).
"""
import argparse
import csv
import json
import os
import sys
import time
import urllib.parse
import xml.etree.ElementTree as ET
from datetime import date

import requests

URL = "https://apis.data.go.kr/1613000/RTMSDataSvcAptTradeDev/getRTMSDataSvcAptTradeDev"
SIDO = "전남광주통합특별시"   # 공개시스템 CSV의 시군구 열과 같은 이름을 쓴다.
# 광주 5개 구 코드. 구 이름 -> 지역 코드(LAWD_CD, 법정동코드 앞 5자리).
# 전남광주통합특별시 출범 뒤의 코드다 (옛 광주광역시: 동구 29110, 서구 29140, 남구 29155, 북구 29170, 광산구 29200).
GU_CODES = {
    "동구": "12210",
    "서구": "12240",
    "남구": "12270",
    "북구": "12300",
    "광산구": "12330",
}
ROWS_PER_PAGE = 1000
SLEEP_SECONDS = 0.2          # 호출 사이의 간격
MAX_RETRY = 3
DEFAULT_OUT = os.path.join("data", "collected")
COLLECTED_AT = "collected_at.txt"  # 받은 날(YYYY-MM-DD). load_trades.py가 수집 기준일로 남긴다 (FR-DATA-05)

# 저장할 열. 실거래가 공개시스템 CSV의 열 이름을 따른다 (DB 설계서 5.1).
OUT_COLS = [
    "시군구", "번지", "본번", "부번", "단지명", "전용면적(㎡)", "계약년월", "계약일",
    "거래금액(만원)", "동", "층", "매수자", "매도자", "건축년도", "도로명", "해제사유발생일",
    "거래유형", "중개사소재지", "등기일자", "단지일련번호", "해제여부",
]

# R-03에서 있는지 확인할 응답 항목. 이름은 시험 호출 결과로 확인한다.
CHECK_FIELDS = {
    "aptSeq": "단지 일련번호",
    "buildYear": "건축 연도",
    "cdealType": "해제 여부",
    "cdealDay": "해제사유 발생일",
    "excluUseAr": "전용면적",
    "dealAmount": "거래 금액",
    "jibun": "지번",
    "umdNm": "법정동",
}


class DailyLimitReached(Exception):
    pass


class ApiFailure(Exception):
    pass


def load_key():
    key = os.environ.get("DATA_GO_KR_KEY")
    if not key and os.path.exists(".env"):
        for line in open(".env", encoding="utf-8"):
            if line.strip().startswith("DATA_GO_KR_KEY="):
                key = line.split("=", 1)[1].strip().strip('"').strip("'")
    if not key:
        sys.exit(".env 파일에 DATA_GO_KR_KEY=인증키 를 넣어 주세요. 프로젝트 폴더에서 실행했는지도 확인해 주세요.")
    return key


def hide_key(text, key):
    """오류 문장에 인증키가 섞여 나오지 않게 가린다."""
    return str(text).replace(key, "***").replace(urllib.parse.quote(key, safe=""), "***")


def month_list(end, months):
    """end(YYYYMM)부터 거슬러 올라간 months개의 계약 연월. 오래된 것부터."""
    year, month = int(end[:4]), int(end[4:])
    result = []
    for _ in range(months):
        result.append(f"{year:04d}{month:02d}")
        month -= 1
        if month == 0:
            year, month = year - 1, 12
    return list(reversed(result))


def previous_month(today):
    if today.month == 1:
        return f"{today.year - 1:04d}12"
    return f"{today.year:04d}{today.month - 1:02d}"


def parse_response(text):
    """응답을 읽어 (결과 코드, 결과 메시지, 전체 건수, 거래 목록)을 돌려준다. XML과 JSON을 모두 읽는다."""
    text = text.strip()
    if text.startswith("{"):
        body = json.loads(text)["response"]
        header, content = body["header"], body.get("body") or {}
        items = (content.get("items") or {})
        items = items.get("item", []) if isinstance(items, dict) else []
        if isinstance(items, dict):          # 한 건이면 목록이 아니라 하나로 온다.
            items = [items]
        return str(header.get("resultCode", "")), header.get("resultMsg", ""), int(content.get("totalCount") or 0), items

    root = ET.fromstring(text)
    if root.tag == "OpenAPI_ServiceResponse":
        # 인증키 오류, 호출 한도 초과 같은 게이트웨이 오류는 이 모양으로 온다.
        code = root.findtext(".//returnReasonCode", "")
        msg = root.findtext(".//returnAuthMsg", "") or root.findtext(".//errMsg", "")
        return code, msg, 0, []
    code = root.findtext("./header/resultCode", "")
    msg = root.findtext("./header/resultMsg", "")
    total = int(root.findtext("./body/totalCount") or 0)
    items = [{child.tag: (child.text or "").strip() for child in item} for item in root.iter("item")]
    return code, msg, total, items


def fetch_page(key, lawd_cd, deal_ymd, page):
    params = {
        "serviceKey": key,
        "LAWD_CD": lawd_cd,
        "DEAL_YMD": deal_ymd,
        "pageNo": page,
        "numOfRows": ROWS_PER_PAGE,
    }
    last_error = ""
    for attempt in range(1, MAX_RETRY + 1):
        try:
            res = requests.get(URL, params=params, timeout=30)
            text = res.text
            if "LIMITED_NUMBER_OF_SERVICE_REQUESTS_EXCEEDS" in text:
                raise DailyLimitReached()
            if "SERVICE_KEY_IS_NOT_REGISTERED" in text or "SERVICE KEY IS NOT REGISTERED" in text:
                sys.exit("인증키가 등록되지 않았습니다. 활용 신청 상태와 키(Decoding)를 확인해 주세요.")
            res.raise_for_status()
            code, msg, total, items = parse_response(text)
            if code not in ("00", "000"):
                # 정상 응답과 구분해 저장하지 않는다 (FR-DATA-08).
                raise ApiFailure(f"결과 코드 {code}: {msg}")
            return total, items, text
        except (DailyLimitReached, ApiFailure):
            raise
        except Exception as e:               # 네트워크 오류, 형식 오류
            last_error = hide_key(f"{type(e).__name__}: {e}", key)
            time.sleep(2 * attempt)
    raise ApiFailure(last_error)


def fetch_month(key, lawd_cd, deal_ymd):
    """구 하나와 계약 연월 하나의 거래를 페이지를 넘겨 모두 받는다 (FR-DATA-07)."""
    rows, page = [], 1
    while True:
        total, items, _ = fetch_page(key, lawd_cd, deal_ymd, page)
        rows.extend(items)
        if not items or len(rows) >= total:
            break
        page += 1
        time.sleep(SLEEP_SECONDS)
    if len(rows) != total:
        raise ApiFailure(f"받은 건수 {len(rows):,}건이 전체 건수 {total:,}건과 다름")
    return rows


def number_text(value):
    """'0026' 같은 번호를 '26'으로. 비어 있으면 빈 글자."""
    value = (value or "").strip()
    return str(int(value)) if value.isdigit() else value


def to_row(item, gu):
    """API 응답 한 건을 공개시스템 CSV의 한 줄 모양으로 바꾼다."""
    road = (item.get("roadNm") or "").strip()
    road_main = number_text(item.get("roadNmBonbun"))
    road_sub = number_text(item.get("roadNmBubun"))
    if road and road_main and road_main != "0":
        road += f" {road_main}" + (f"-{road_sub}" if road_sub and road_sub != "0" else "")
    return {
        "시군구": f"{SIDO} {gu} {(item.get('umdNm') or '').strip()}",
        "번지": (item.get("jibun") or "").strip(),
        "본번": (item.get("bonbun") or "").strip(),
        "부번": (item.get("bubun") or "").strip(),
        "단지명": (item.get("aptNm") or "").strip(),
        "전용면적(㎡)": (item.get("excluUseAr") or "").strip(),
        "계약년월": f"{(item.get('dealYear') or '').strip()}{(item.get('dealMonth') or '').strip().zfill(2)}",
        "계약일": (item.get("dealDay") or "").strip().zfill(2),
        "거래금액(만원)": (item.get("dealAmount") or "").strip(),   # 쉼표가 있는 만원 단위. 원으로 바꾸는 것은 적재 때
        "동": (item.get("aptDong") or "").strip() or "-",
        "층": (item.get("floor") or "").strip(),
        "매수자": (item.get("buyerGbn") or "").strip(),
        "매도자": (item.get("slerGbn") or "").strip(),
        "건축년도": (item.get("buildYear") or "").strip(),
        "도로명": road or "-",
        "해제사유발생일": (item.get("cdealDay") or "").strip() or "-",
        "거래유형": (item.get("dealingGbn") or "").strip(),
        "중개사소재지": (item.get("estateAgentSggNm") or "").strip() or "-",
        "등기일자": (item.get("rgstDate") or "").strip() or "-",
        "단지일련번호": (item.get("aptSeq") or "").strip(),       # 앞자리가 옛 지역 코드여도 고치지 않는다
        "해제여부": (item.get("cdealType") or "").strip(),
    }


def save_month(path, rows, gu):
    """다 받은 것만 저장한다. 임시 파일에 쓴 뒤 이름을 바꿔, 중간에 멈춰도 반쪽 파일이 남지 않게 한다."""
    tmp = path + ".tmp"
    with open(tmp, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=OUT_COLS)
        writer.writeheader()
        for item in rows:
            writer.writerow(to_row(item, gu))
    os.replace(tmp, path)


def read_text_any(path):
    for enc in ("utf-8-sig", "cp949"):
        try:
            with open(path, encoding=enc) as f:
                return f.read()
        except UnicodeDecodeError:
            continue
    sys.exit(f"읽을 수 없는 파일: {path}")


def codes_from_file(path):
    """법정동코드 전체자료(탭으로 나뉜 글자 파일)에서 5개 구의 지역 코드를 찾는다.

    "전남광주통합특별시 서구"처럼 시도와 구 이름으로 시작하고 폐지되지 않은 줄의 앞 5자리를 쓴다.
    """
    if not os.path.exists(path):
        sys.exit(f"파일이 없습니다: {path}")
    found = {gu: set() for gu in GU_CODES}
    for line in read_text_any(path).splitlines()[1:]:
        parts = [p.strip() for p in line.split("\t")]
        if len(parts) < 2 or not parts[0].isdigit():
            continue
        code, name = parts[0], " ".join(parts[1].split())
        if len(parts) >= 3 and parts[2] and parts[2] != "존재":
            continue
        for gu in GU_CODES:
            if name == f"{SIDO} {gu}" or name.startswith(f"{SIDO} {gu} "):
                found[gu].add(code[:5])
    codes = {}
    for gu, values in found.items():
        if len(values) != 1:
            sys.exit(f"{SIDO} {gu}의 지역 코드를 하나로 정하지 못했습니다 (찾은 코드: {sorted(values) or '없음'}). "
                     f"--code {gu}=코드 로 직접 주세요.")
        codes[gu] = values.pop()
    return codes


def resolve_gu_codes(codes_path, code_args):
    """쓸 지역 코드를 정한다. --code > --codes > GU_CODES 순서."""
    codes = codes_from_file(codes_path) if codes_path else dict(GU_CODES)
    for pair in code_args or []:
        gu, _, code = pair.partition("=")
        gu, code = gu.strip(), code.strip()
        if gu not in GU_CODES or len(code) != 5 or not code.isdigit():
            sys.exit(f"--code 값을 다시 확인해 주세요: {pair} (예: 서구=12345, 구는 {', '.join(GU_CODES)})")
        codes[gu] = code
    if len(set(codes.values())) != len(codes):
        sys.exit(f"지역 코드가 겹칩니다: {codes}")
    source = "직접 준 코드" if code_args else ("법정동코드 파일" if codes_path else "광주 5개 구 코드(GU_CODES)")
    print(f"지역 코드 ({source}): " + ", ".join(f"{gu} {code}" for gu, code in codes.items()))
    return codes


def run_test(key, gu_codes):
    """시험 호출. 서구의 지난달 거래 한 페이지를 불러 응답 항목을 보여 준다. 저장하지 않는다."""
    gu, lawd_cd = "서구", gu_codes["서구"]
    deal_ymd = previous_month(date.today())
    print(f"시험 호출: {gu}({lawd_cd}), 계약 연월 {deal_ymd}")
    try:
        total, items, text = fetch_page(key, lawd_cd, deal_ymd, 1)
    except DailyLimitReached:
        sys.exit("하루 호출 한도에 도달했습니다. 내일 다시 시험해 주세요.")
    except ApiFailure as e:
        sys.exit(f"실패: {e}")

    print(f"결과: 정상. 전체 {total:,}건, 이번 페이지 {len(items):,}건")
    if total > len(items):
        print(f"  전체 건수가 더 많습니다. 전체 수집 때는 다음 페이지를 이어 불러 {total:,}건을 모두 받습니다.")
    if not items:
        print("거래가 0건입니다. 지역 코드가 맞는지(--codes, --code), 계약 연월에 거래가 있는지 확인해 주세요.")
        return
    fields = sorted({k for item in items for k in item})
    print(f"\n응답 항목 {len(fields)}개: {', '.join(fields)}")
    print("\nR-03 확인")
    for name, meaning in CHECK_FIELDS.items():
        filled = sum(1 for item in items if (item.get(name) or "").strip())
        state = f"있음 (값이 있는 거래 {filled:,}/{len(items):,}건)" if name in fields else "없음"
        print(f"  {meaning:<10} {name:<12} {state}")
    print("\n첫 거래를 공개시스템 CSV 모양으로 바꾼 결과")
    for col, value in to_row(items[0], gu).items():
        print(f"  {col}: {value}")


def main():
    ap = argparse.ArgumentParser(description="광주시 아파트 매매 실거래가 수집")
    ap.add_argument("--test", action="store_true")
    ap.add_argument("--end", default=None)
    ap.add_argument("--months", type=int, default=12)
    ap.add_argument("--only", nargs="*", default=None)
    ap.add_argument("--out", default=DEFAULT_OUT)
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--codes", default=None)
    ap.add_argument("--code", nargs="*", default=None)
    args = ap.parse_args()

    gu_codes = resolve_gu_codes(args.codes, args.code)
    key = load_key()
    if args.test:
        run_test(key, gu_codes)
        return

    code_to_gu = {code: gu for gu, code in gu_codes.items()}
    if args.only:
        jobs = []
        for job in args.only:
            lawd_cd, _, deal_ymd = job.partition("-")
            if lawd_cd not in code_to_gu or len(deal_ymd) != 6 or not deal_ymd.isdigit():
                sys.exit(f"--only 값을 다시 확인해 주세요: {job} (예: {gu_codes['서구']}-202609)")
            jobs.append((lawd_cd, deal_ymd))
    else:
        end = args.end or previous_month(date.today())
        if len(end) != 6 or not end.isdigit():
            sys.exit("--end는 YYYYMM 모양으로 적어 주세요. 예: 202609")
        months = month_list(end, args.months)
        jobs = [(code, ym) for code in gu_codes.values() for ym in months]
        print(f"수집 기간: {months[0]} ~ {months[-1]} ({len(months)}개월), 5개 구")

    os.makedirs(args.out, exist_ok=True)
    fail_path = os.path.join(args.out, "failed.csv")
    failed, saved, skipped, total_rows = [], 0, 0, 0
    for n, (lawd_cd, deal_ymd) in enumerate(jobs, 1):
        gu = code_to_gu[lawd_cd]
        path = os.path.join(args.out, f"{lawd_cd}_{deal_ymd}.csv")
        label = f"[{n}/{len(jobs)}] {gu} {deal_ymd}"
        if os.path.exists(path) and not args.force:
            skipped += 1
            print(f"{label}: 이미 받음, 건너뜀")
            continue
        try:
            rows = fetch_month(key, lawd_cd, deal_ymd)
        except DailyLimitReached:
            print("하루 호출 한도에 도달했습니다. 내일 같은 명령으로 다시 실행하면 받은 것은 건너뛰고 이어서 받습니다.")
            break
        except ApiFailure as e:
            failed.append((lawd_cd, deal_ymd, gu, str(e)))
            print(f"{label}: 실패 ({e})")
            continue
        save_month(path, rows, gu)
        saved += 1
        total_rows += len(rows)
        print(f"{label}: {len(rows):,}건")
        time.sleep(SLEEP_SECONDS)

    print(f"\n저장 {saved}개 ({total_rows:,}건), 건너뜀 {skipped}개, 실패 {len(failed)}개. 폴더: {args.out}")
    if saved:
        with open(os.path.join(args.out, COLLECTED_AT), "w", encoding="utf-8") as f:
            f.write(date.today().isoformat() + "\n")
        print(f"받은 날 {date.today().isoformat()}을 {COLLECTED_AT}에 적었습니다.")
    if failed:
        with open(fail_path, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.writer(f)
            writer.writerow(["구코드", "계약연월", "구", "이유"])
            writer.writerows(failed)
        retry = " ".join(f"{c}-{y}" for c, y, _, _ in failed)
        print(f"실패 목록: {fail_path}")
        code_opts = (f' --codes "{args.codes}"' if args.codes else "") + (f" --code {' '.join(args.code)}" if args.code else "")
        print(f"실패한 것만 다시 받기: python data/collect_trades.py{code_opts} --only {retry}")
    elif os.path.exists(fail_path):
        os.remove(fail_path)


if __name__ == "__main__":
    main()
