"""전유공용면적 CSV 여러 개를 읽어 아파트의 평형별 공급면적을 한 파일로 만든다.

사용법:
    python build_supply_area.py <CSV가 들어 있는 폴더> [결과 파일 이름]

폴더 안의 모든 .csv 파일(동별로 내려받은 전유공용면적 파일)을 합쳐서 계산한다.
"""
import glob
import os
import sys

import pandas as pd

# 필요한 열만 읽는다.
USE_COLS = [
    "대지위치", "시군구코드", "법정동코드", "번", "지", "관리건축물대장PK",
    "도로명대지위치", "건물명", "전유공용구분코드명", "주용도코드명", "기타용도", "면적(㎡)",
]

# 공급면적에서 빼는 공용 공간 (기타공용)
EXCLUDE = ["주차", "관리", "경비", "경로", "보육", "주민", "기계", "전기", "펌프", "발전",
           "MDF", "창고", "재활용", "대피", "지하실", "변소", "노인", "집회", "휘트니스",
           "독서", "다목적"]
# 공급면적에 넣는 공용 공간 (주거공용)
INCLUDE = ["계단", "복도", "벽체", "E/V", "E.V", "EV", "에레베타", "승강", "현관", "통로",
           "Core", "코어", "홀"]

MAX_EXCLUSIVE_AREA = 300      # 이보다 크면 한 세대로 보지 않는다.
MAX_EXCLUSIVE_RATIO = 85      # 전용률이 이보다 높으면 공용면적이 덜 등재된 것으로 본다.


def classify(usage):
    usage = str(usage)
    if any(k in usage for k in EXCLUDE):
        return "기타공용"
    if any(k in usage for k in INCLUDE):
        return "주거공용"
    return "미분류"


def read_all(folder):
    frames = []
    for path in sorted(glob.glob(os.path.join(folder, "*.csv"))):
        for enc in ("utf-8-sig", "cp949"):
            try:
                df = pd.read_csv(path, encoding=enc, dtype=str, usecols=USE_COLS)
                break
            except UnicodeDecodeError:
                continue
            except ValueError:          # 형식이 다른 CSV는 건너뛴다.
                df = None
                break
        if df is None:
            print(f"건너뜀 (형식이 다름): {os.path.basename(path)}")
            continue
        frames.append(df)
        print(f"읽음: {os.path.basename(path)}  {len(df):,}줄")
    if not frames:
        sys.exit("읽을 수 있는 CSV가 없습니다.")
    # 같은 동을 두 번 받았을 때를 대비해 완전히 같은 줄은 한 번만 남긴다.
    return pd.concat(frames, ignore_index=True).drop_duplicates()


def build(df):
    df["area"] = pd.to_numeric(df["면적(㎡)"], errors="coerce").fillna(0)

    # 전유 부분의 용도가 아파트인 세대만 남긴다.
    excl = df[df["전유공용구분코드명"] == "전유"]
    apt_pk = excl.loc[excl["주용도코드명"] == "아파트", "관리건축물대장PK"].unique()
    apt = df[df["관리건축물대장PK"].isin(apt_pk)]

    units = (
        apt[apt["전유공용구분코드명"] == "전유"]
        .groupby("관리건축물대장PK")
        .agg(아파트명=("건물명", "first"), 지번주소=("대지위치", "first"),
             도로명주소=("도로명대지위치", "first"), 시군구코드=("시군구코드", "first"),
             법정동코드=("법정동코드", "first"), 번=("번", "first"), 지=("지", "first"),
             전용=("area", "sum"))
        .reset_index()
    )

    common = apt[apt["전유공용구분코드명"] == "공용"].copy()
    common["분류"] = common["기타용도"].map(classify)
    by_kind = common.pivot_table(index="관리건축물대장PK", columns="분류", values="area",
                                 aggfunc="sum", fill_value=0).reset_index()
    units = units.merge(by_kind, on="관리건축물대장PK", how="left")
    for col in ("주거공용", "기타공용", "미분류"):
        if col not in units:
            units[col] = 0.0
        units[col] = units[col].fillna(0)
    units["공급"] = units["전용"] + units["주거공용"]
    units["전용"] = units["전용"].round(2)

    keys = ["시군구코드", "법정동코드", "번", "지", "지번주소", "도로명주소", "아파트명", "전용"]
    types = (
        units.groupby(keys, dropna=False)
        .agg(세대수=("공급", "size"), 주거공용=("주거공용", "median"), 공급=("공급", "median"),
             공급최소=("공급", "min"), 공급최대=("공급", "max"), 미분류=("미분류", "median"))
        .reset_index()
    )
    types["전용률"] = (types["전용"] / types["공급"] * 100).round(1)

    def note(r):
        if r["전용"] > MAX_EXCLUSIVE_AREA:
            return "한 세대로 보기 어려움"
        if r["주거공용"] == 0:
            return "주거공용을 구분할 수 없음"
        if r["전용률"] > MAX_EXCLUSIVE_RATIO:
            return "전용률이 높음"
        if r["공급최대"] - r["공급최소"] > 0.5:
            return "세대별 값이 다름"
        return ""

    types["확인 필요"] = types.apply(note, axis=1)
    types["공급면적 사용 가능"] = types["확인 필요"].eq("").map({True: "Y", False: "N"})

    out = pd.DataFrame({
        "시군구코드": types["시군구코드"], "법정동코드": types["법정동코드"],
        "번": types["번"], "지": types["지"],
        "아파트명": types["아파트명"], "지번주소": types["지번주소"], "도로명주소": types["도로명주소"],
        "전용면적(㎡)": types["전용"],
        "주거공용면적(㎡)": types["주거공용"].round(2),
        "공급면적(㎡)": types["공급"].round(2),
        "전용면적(평)": (types["전용"] / 3.3058).round(1),
        "공급면적(평)": (types["공급"] / 3.3058).round(1),
        "전용률(%)": types["전용률"],
        "세대수": types["세대수"],
        "분류하지 못한 공용면적(㎡)": types["미분류"].round(2),
        "공급면적 사용 가능": types["공급면적 사용 가능"],
        "확인 필요": types["확인 필요"],
    })
    return out.sort_values(["지번주소", "아파트명", "전용면적(㎡)"])


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    folder = sys.argv[1]
    out_path = sys.argv[2] if len(sys.argv) > 2 else "아파트_공급면적.csv"
    result = build(read_all(folder))
    result.to_csv(out_path, index=False, encoding="utf-8-sig")
    ok = (result["공급면적 사용 가능"] == "Y").sum()
    print(f"\n평형 {len(result):,}개 저장: {out_path}")
    print(f"공급면적 사용 가능 {ok:,}개, 확인 필요 {len(result) - ok:,}개")


if __name__ == "__main__":
    main()
