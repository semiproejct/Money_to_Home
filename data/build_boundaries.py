"""광주 5개 구의 경계 자료를 만든다 (FR-MAP-28, T-MAP-26). 한 번 돌리는 스크립트다.

만드는 파일 (WGS84, EPSG:4326). 지도 화면(js/boundary.js)이 그대로 읽는다.
  frontend/data/boundaries.geojson       지도를 열 때 받는다 (약 190KB)
    layer "outline" : 광주 5개 구를 하나로 합친 바깥 경계 1개. 구 사이의 경계선은 없다
    layer "gu"      : 구 경계 5개 (properties.gu)
    layer "hdong"   : 행정동 경계 (properties.gu, name). 가까이 볼 때 연한 회색 선으로만 그린다
  frontend/data/boundaries_bdong.geojson 지도가 뜬 뒤에 뒤에서 받는다 (약 550KB). 처음 화면을 늦추지 않게 나눴다
    layer "bdong"   : 법정동 경계 (properties.gu, dong). 지역 선택에서 동을 골랐을 때 칠한다

서비스의 동(apartments.dong)은 실거래가 자료의 법정동이다. admdongkor는 행정동이라 이름과 모양이 다르다.
그래서 고른 동을 칠하는 데는 브이월드의 법정동 경계를 쓰고, 행정동은 선으로만 그린다 (2026-10-15 결정).

자료
  - 구, 행정동: admdongkor (github.com/vuski/admdongkor). 통계청 SGIS 행정동 경계. 판(version)은 기본 20260701.
    light 판(mapshaper로 단순화)을 쓴다. 이웃한 동이 맞닿은 선이 똑같이 단순화되어 있어 합쳐도 틈이 생기지 않는다.
  - 법정동: 브이월드 "법정구역정보" (국가중점데이터, 국토교통부, CC BY). 전국 SHP zip을 data/raw/boundary/ 에 둔다.
    원본은 크고(약 120MB) 다시 받을 수 있어 저장소에 넣지 않는다. 없으면 법정동 없이 만든다 (그때 화면은 동을 골라도 구만 강조한다).
    같은 경계를 담은 "행정구역_읍면동(법정동)"(LSMD_ADM_SECT_UMD)은 라이선스가 CC BY-NC-ND(변경 금지)라 쓰지 않는다.
  - 출처와 기준일은 docs/guides/boundary_data.md에 적는다.

구는 코드가 아니라 이름(동구, 서구, 남구, 북구, 광산구)으로 찾는다. 2026-07-01 통합으로 시도·시군구 코드가 바뀌었고,
자료마다 옛 코드와 새 코드가 섞여 있을 수 있어서다. 법정동은 그 동의 안쪽 점이 어느 구 안에 있는지로 구를 정한다.

실행 (프로젝트 폴더, 가상 환경)
  python -m pip install -r data/requirements-boundary.txt
  python data/build_boundaries.py --dry-run   # 검사만 하고 파일을 쓰지 않는다
  python data/build_boundaries.py             # 만든다
  python data/build_boundaries.py --check-db  # 서비스 DB의 구·동 목록과 법정동 이름을 맞춰 본다 (MariaDB 필요)
"""
import argparse
import json
import sys
import tempfile
import zipfile
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = ROOT / "data" / "raw" / "boundary"
OUT_PATH = ROOT / "frontend" / "data" / "boundaries.geojson"
OUT_BDONG_PATH = ROOT / "frontend" / "data" / "boundaries_bdong.geojson"

GU_NAMES = ["동구", "서구", "남구", "북구", "광산구"]
DEFAULT_VERSION = "20260701"
METRIC_CRS = "EPSG:5179"  # 미터 단위. 합치기, 단순화, 넓이 계산은 여기서 한다
WEB_CRS = "EPSG:4326"  # 카카오맵과 GeoJSON의 좌표
CLOSE_M = 1.0  # 구를 합칠 때 생길 수 있는 실틈을 메우는 거리 (m). 바깥 모양은 거의 바뀌지 않는다
BDONG_SIMPLIFY_M = 3.0  # 법정동은 필지 단위로 아주 자세하다. 지도에서 보이지 않는 3m 아래의 굴곡을 줄인다
MIN_PART_M2 = 500  # 구 경계로 자른 뒤 남는 이보다 작은 조각은 버린다 (자료 사이의 어긋남에서 생긴 부스러기)
SMALL_ISLAND_M2 = 1_000_000  # 바깥 경계에 이보다 작은 섬이 있으면 알린다 (1㎢)
DIGITS = 6  # 좌표의 소수 자리. 0.000001도는 약 0.1m

# 브이월드 SHP에서 법정동 이름이 들어 있을 수 있는 칸. 이 이름이 없으면 값을 보고 찾는다 (법정구역정보는 A0, A1 ... 처럼 이름이 없다)
BDONG_NAME_COLUMNS = ["EMD_NM", "EMD_KOR_NM", "emd_nm", "emd_kor_nm", "EMD_NAME"]
EMD_ENDINGS = ("동", "가", "읍", "면")  # 읍면동 이름의 끝 글자. 광주 5개 구의 법정동은 "동"과 "가"(예: 충장로1가)다


def say(text: str) -> None:
    print(text, flush=True)


def fail(text: str) -> None:
    print(f"[중단] {text}", file=sys.stderr, flush=True)
    sys.exit(1)


def has_hangul(values) -> bool:
    return any(any("가" <= ch <= "힣" for ch in str(v)) for v in values)


# ───────── 1. 행정동과 구 (admdongkor) ─────────

def load_hdong(version: str):
    """광주 5개 구의 행정동. 칸: gu, name, geometry (EPSG:5179)"""
    try:
        import admdongkor as adk
    except ImportError:
        fail("admdongkor가 없습니다. python -m pip install -r data/requirements-boundary.txt")

    versions = [str(v) for v in adk.versions()]
    if version not in versions:
        fail(f"admdongkor에 {version} 판이 없습니다. 마지막 판: {versions[-5:]}")

    gdf = adk.get(version, "emd", crs=METRIC_CRS)  # detail=False가 기본이라 light 판이다
    say(f"admdongkor {version} 행정동 {len(gdf):,}곳을 읽었습니다. 칸: {list(gdf.columns)}")

    # 칸 이름은 판마다 다르다. parquet 판은 sidonm, sggnm, emdnm에 시도, 시군구, 읍면동 이름이 따로 있고,
    # GeoJSON 판은 adm_nm 하나에 "시도 시군구 읍면동"으로 붙어 있다
    last_word = lambda series: series.astype(str).str.split().str[-1]
    if {"sidonm", "sggnm", "emdnm"} <= set(gdf.columns):
        gdf = gdf.assign(sido=gdf["sidonm"].astype(str), gu=last_word(gdf["sggnm"]), name=last_word(gdf["emdnm"]))
    elif "adm_nm" in gdf.columns:
        parts = gdf["adm_nm"].astype(str).str.split()
        gdf = gdf.assign(sido=parts.str[0], gu=parts.str[1], name=parts.str[-1])
    else:
        fail(f"admdongkor 자료에서 시도·시군구·읍면동 이름 칸을 찾지 못했습니다. 칸: {list(gdf.columns)}")
    picked = gdf[gdf["sido"].str.contains("광주") & gdf["gu"].isin(GU_NAMES)].copy()

    sidos = sorted(picked["sido"].unique())
    say(f"광주 5개 구를 찾은 시도 이름: {sidos}")
    if len(sidos) != 1:
        fail(f"광주 5개 구가 한 시도에 있지 않습니다: {sidos}")
    missing = [gu for gu in GU_NAMES if gu not in set(picked["gu"])]
    if missing:
        fail(f"admdongkor 자료에서 찾지 못한 구: {missing}")

    for gu in GU_NAMES:
        say(f"  {gu}: 행정동 {int((picked['gu'] == gu).sum())}곳")
    picked["geometry"] = picked.geometry.make_valid()
    return picked[["gu", "name", "geometry"]]


def make_gu_and_outline(hdong):
    """구 경계 5개와 5개 구를 합친 바깥 경계. 행정동을 구마다 합친 뒤(dissolve), 다시 전체를 합친다(union)."""
    from shapely.ops import unary_union

    gu = hdong.dissolve(by="gu").reset_index()[["gu", "geometry"]]
    # 실틈을 메운다: 1m 넓혔다가 1m 줄인다. 맞닿은 선 사이에 틈이 있으면 사라지고, 바깥 모양은 거의 그대로다
    gu["geometry"] = gu.geometry.buffer(CLOSE_M).buffer(-CLOSE_M).make_valid()
    outline = unary_union(list(gu.geometry)).buffer(CLOSE_M).buffer(-CLOSE_M)
    return gu, outline


def polygons_of(geom):
    if geom.geom_type == "Polygon":
        return [geom]
    if geom.geom_type == "MultiPolygon":
        return list(geom.geoms)
    if geom.geom_type == "GeometryCollection":
        return [g for part in geom.geoms for g in polygons_of(part)]
    return []


def check_outline(gu, outline, hdong) -> list[str]:
    """바깥 경계를 원본과 견준다. 문제가 있으면 문장 목록을 돌려준다 (비어 있으면 통과)."""
    problems = []
    parts = polygons_of(outline)
    holes = [ring for poly in parts for ring in poly.interiors]
    hdong_area = hdong.geometry.area.sum()
    gu_area = gu.geometry.area.sum()
    out_area = outline.area

    say("바깥 경계 검사")
    say(f"  유효한 도형: {outline.is_valid}")
    say(f"  조각 수: {len(parts)} (넓이 큰 순: {', '.join(f'{p.area / 1e6:.2f}㎢' for p in sorted(parts, key=lambda p: -p.area)[:5])})")
    say(f"  안쪽 구멍 수: {len(holes)}")
    say(f"  넓이: 행정동 합 {hdong_area / 1e6:.3f}㎢, 구 합 {gu_area / 1e6:.3f}㎢, 바깥 경계 {out_area / 1e6:.3f}㎢")

    if not outline.is_valid:
        problems.append("바깥 경계가 유효한 도형이 아닙니다 (자기 교차 등).")
    if holes:
        from shapely.geometry import Polygon

        hole_areas = sorted((Polygon(ring).area for ring in holes), reverse=True)
        problems.append(f"바깥 경계 안에 구멍이 {len(holes)}개 있습니다 (큰 순 {', '.join(f'{a:.0f}㎡' for a in hole_areas[:5])}).")
    small = [p for p in parts if p.area < SMALL_ISLAND_M2]
    if small:
        problems.append(f"바깥 경계에 1㎢보다 작은 섬이 {len(small)}개 있습니다.")
    if abs(gu_area - out_area) / out_area > 0.001:
        problems.append("구 넓이의 합과 바깥 경계의 넓이가 0.1% 넘게 다릅니다 (겹침이나 틈).")
    if abs(hdong_area - out_area) / out_area > 0.001:
        problems.append("행정동 넓이의 합과 바깥 경계의 넓이가 0.1% 넘게 다릅니다.")
    for row in gu.itertuples():
        if not row.geometry.is_valid:
            problems.append(f"{row.gu} 경계가 유효한 도형이 아닙니다.")
    return problems


# ───────── 2. 법정동 (브이월드 SHP) ─────────

def find_bdong_source() -> Path | None:
    """data/raw/boundary/ 의 zip 또는 shp. 없으면 None"""
    if not RAW_DIR.exists():
        return None
    candidates = sorted(RAW_DIR.glob("*.zip")) + sorted(RAW_DIR.glob("*.shp"))
    if not candidates:
        return None
    if len(candidates) > 1:
        say(f"법정동 원본이 여러 개라 첫째를 씁니다: {[c.name for c in candidates]}")
    return candidates[0]


def has_hangul_text(series) -> bool:
    return has_hangul(series.dropna().head(200))


def find_code_column(gdf):
    """10자리 법정동 코드가 든 칸. 없으면 None"""
    for col in gdf.columns:
        if col == "geometry":
            continue
        values = gdf[col].dropna().astype(str).head(500)
        if len(values) and values.str.fullmatch(r"\d{10}").mean() > 0.9:
            return col
    return None


def find_name_column(gdf, rows):
    """읍면동 이름이 든 칸. 알려진 이름이 없으면, 읍면동 줄(rows)에서 마지막 낱말이 동·가·읍·면으로 끝나는 비율이 가장 높은 칸"""
    known = next((c for c in BDONG_NAME_COLUMNS if c in gdf.columns), None)
    if known:
        return known
    best, best_share = None, 0.0
    for col in gdf.columns:
        if col == "geometry" or not has_hangul_text(gdf[col]):
            continue
        last = gdf.loc[rows, col].dropna().astype(str).str.split().str[-1]
        if last.nunique() < 20:
            continue  # 시도·시군구 이름 칸은 값이 몇 가지뿐이다
        share = last.str.endswith(EMD_ENDINGS).mean()
        if share > best_share:
            best, best_share = col, share
    return best if best_share > 0.8 else None


def read_shp(path: Path):
    """SHP를 읽어 읍면동 줄만 남긴다. 칸: dong, geometry.

    GDAL(pyogrio, fiona) 없이 pyshp로 읽는다. Windows에서 GDAL DLL을 불러오지 못하는 PC가 있어서다.
    브이월드 SHP는 글자가 cp949인데 .cpg(인코딩 표시) 파일이 없을 때가 있다. utf-8로 읽지 못하면 cp949로 읽는다.
    """
    import geopandas as gpd
    import pandas as pd
    import shapefile  # pyshp
    from pyproj import CRS
    from shapely.geometry import shape

    def read(encoding):
        with shapefile.Reader(str(path), encoding=encoding) as reader:
            fields = [f[0] for f in reader.fields[1:]]  # 첫째는 지움 표시 칸이다
            rows, geoms = [], []
            for item in reader.iterShapeRecords():
                rows.append(list(item.record))
                geoms.append(shape(item.shape.__geo_interface__) if item.shape.points else None)
        return pd.DataFrame(rows, columns=fields), geoms

    try:
        table, geoms = read("utf-8")
        readable = any(has_hangul_text(table[c]) for c in table.columns)
    except Exception:  # pyshp는 글자를 읽지 못하면 UnicodeDecodeError가 아니라 자기 오류(dbfFileException)를 낸다
        readable = False
    if not readable:
        table, geoms = read("cp949")

    prj = path.with_suffix(".prj")
    crs = CRS.from_wkt(prj.read_text(encoding="utf-8", errors="ignore")) if prj.exists() else None
    gdf = gpd.GeoDataFrame(table, geometry=geoms, crs=crs)
    gdf = gdf[gdf.geometry.notna()]
    say(f"  {path.name}: {len(gdf):,}줄, 좌표계 {crs.to_epsg() if crs else '없음'}")
    say(f"  칸과 첫 줄 값: {dict(gdf.drop(columns='geometry').head(1).iloc[0].astype(str))}")

    # 시군구·읍면동·리가 섞여 있으면 법정동 코드(10자리: 시군구 5 + 읍면동 3 + 리 2)로 읍면동 줄만 고른다
    code_col = find_code_column(gdf)
    if code_col:
        code = gdf[code_col].astype(str)
        rows = code.str.fullmatch(r"\d{10}") & (code.str[5:8] != "000") & (code.str[8:10] == "00")
        say(f"  법정동 코드 칸 {code_col}: 읍면동 줄 {int(rows.sum()):,}개")
    else:
        rows = pd.Series(True, index=gdf.index)  # 모두
    name_col = find_name_column(gdf, rows)
    if name_col is None:
        fail(f"법정동 이름 칸을 찾지 못했습니다. 칸: {list(gdf.columns)}. BDONG_NAME_COLUMNS에 더해 주세요.")
    say(f"  법정동 이름 칸: {name_col}")
    picked = gdf.loc[rows].copy()
    picked["dong"] = picked[name_col].astype(str).str.split().str[-1]
    picked = picked[picked["dong"].str.endswith(EMD_ENDINGS)]
    return gpd.GeoDataFrame(picked[["dong", "geometry"]], geometry="geometry", crs=gdf.crs)


def extract_shps(zip_path: Path, folder: Path) -> list[Path]:
    """zip에서 읽을 .shp를 풀어 경로를 돌려준다.
    법정구역정보는 zip 안에 다시 zip이 있다: (EMD) 읍면동, (LIO) 리, (SIG) 시군구. 읍면동(EMD)만 연다.
    시도마다 .shp가 나뉘어 있으면 광주가 든 것만, 아니면 모두 푼다."""
    with zipfile.ZipFile(zip_path) as archive:
        names = archive.namelist()
        shps = [n for n in names if n.lower().endswith(".shp")]
        if not shps:
            inner = [n for n in names if n.lower().endswith(".zip")]
            emd = [n for n in inner if "EMD" in n.upper()] or inner
            found = []
            for name in emd:
                archive.extract(name, folder)
                found += extract_shps(folder / name, folder / Path(name).stem)
            return found
        shps = [n for n in shps if "광주" in n] or shps
        for shp in shps:
            stem = shp[: -len(".shp")]
            for member in names:
                if member.startswith(stem + "."):
                    archive.extract(member, folder)
        return [folder / shp for shp in shps]


def load_bdong(source: Path, gu):
    """광주 5개 구의 법정동. 칸: gu, dong, geometry (EPSG:5179). 구 경계 안으로 자르고 단순화한다."""
    import geopandas as gpd
    import pandas as pd
    from shapely.geometry import MultiPolygon

    if source.suffix.lower() == ".zip":
        with tempfile.TemporaryDirectory() as tmp:
            shps = extract_shps(source, Path(tmp))
            if not shps:
                fail(f"{source.name} 안에 .shp가 없습니다.")
            say(f"법정동 원본: {source.name} 안의 {[p.name for p in shps]}")
            parts = [read_shp(shp) for shp in shps]
            crs = parts[0].crs
            raw = gpd.GeoDataFrame(pd.concat([p.to_crs(crs) for p in parts], ignore_index=True), geometry="geometry", crs=crs)
    else:
        say(f"법정동 원본: {source.name}")
        raw = read_shp(source)

    if raw.crs is None:
        fail("법정동 SHP에 좌표계(.prj)가 없습니다. 내려받은 zip을 그대로 두세요.")
    say(f"  읍면동 {len(raw):,}개를 읽었습니다.")
    raw = raw.to_crs(METRIC_CRS)
    raw["geometry"] = raw.geometry.make_valid()

    # 어느 구의 동인가: 동의 안쪽 점이 들어 있는 구. 5개 구 밖의 동(전남의 시군)은 여기서 빠진다
    points = raw.assign(geometry=raw.geometry.representative_point())
    joined = gpd.sjoin(points, gu[["gu", "geometry"]], predicate="within", how="inner")
    joined = joined[~joined.index.duplicated()]  # 두 구가 맞닿은 선 위의 점은 한 구에만 넣는다
    picked = raw.loc[joined.index].assign(gu=joined["gu"].values)
    picked = picked.dissolve(by=["gu", "dong"]).reset_index()[["gu", "dong", "geometry"]]

    # 구 경계 안으로 자른다. 자료의 출처가 달라 수십 m 어긋날 수 있어, 칠한 면이 구 경계선을 넘지 않게 한다
    gu_geom = dict(zip(gu["gu"], gu.geometry))
    cleaned = []
    for row in picked.itertuples():
        geom = row.geometry.intersection(gu_geom[row.gu]).simplify(BDONG_SIMPLIFY_M, preserve_topology=True)
        parts = [p for p in polygons_of(geom) if p.area >= MIN_PART_M2]
        if not parts:
            say(f"  [건너뜀] {row.gu} {row.dong}: 구 경계 안에 남는 넓이가 없습니다.")
            continue
        merged = parts[0] if len(parts) == 1 else MultiPolygon(parts)
        cleaned.append({"gu": row.gu, "dong": row.dong, "geometry": merged.buffer(0)})
    result = gpd.GeoDataFrame(cleaned, geometry="geometry", crs=METRIC_CRS)
    for g in GU_NAMES:
        say(f"  {g}: 법정동 {int((result['gu'] == g).sum())}곳")
    return result


def check_db(bdong) -> None:
    """서비스의 구·동(apartments)이 모두 법정동 경계를 갖는지 본다. 경계가 없는 동은 화면에서 구만 강조된다."""
    sys.path.insert(0, str(ROOT))
    from backend.database import connect  # data/ 스크립트는 connect를 쓴다 (CLAUDE.md)

    with connect() as conn, conn.cursor() as cur:
        cur.execute("SELECT DISTINCT gu, dong FROM apartments ORDER BY gu, dong")
        rows = cur.fetchall()
    have = set(zip(bdong["gu"], bdong["dong"])) if bdong is not None else set()
    missing = [f"{r['gu']} {r['dong']}" for r in rows if (r["gu"], r["dong"]) not in have]
    say(f"서비스의 구·동 {len(rows)}개 가운데 법정동 경계가 있는 것 {len(rows) - len(missing)}개")
    if missing:
        say(f"  경계가 없는 동 (화면에서 구만 강조된다): {missing}")


# ───────── 3. 저장 ─────────

def rounded(value):
    if isinstance(value, float):
        return round(value, DIGITS)
    if isinstance(value, (list, tuple)):
        return [rounded(v) for v in value]
    return value


def feature(layer: str, geom, **props) -> dict:
    from shapely.geometry import mapping

    shape = mapping(geom)
    return {
        "type": "Feature",
        "properties": {"layer": layer, **props},
        "geometry": {"type": shape["type"], "coordinates": rounded(shape["coordinates"])},
    }


def to_web(gdf_or_geom, crs=METRIC_CRS):
    import geopandas as gpd

    if isinstance(gdf_or_geom, gpd.GeoDataFrame):
        return gdf_or_geom.to_crs(WEB_CRS)
    return gpd.GeoSeries([gdf_or_geom], crs=crs).to_crs(WEB_CRS).iloc[0]


def build(version: str, bdong_source: Path | None) -> dict:
    return {
        "type": "FeatureCollection",
        # GeoJSON 표준(RFC 7946)이 허용하는 덧붙인 칸. 출처와 만든 때를 남긴다
        "metadata": {
            "generated_at": datetime.now().isoformat(timespec="seconds"),
            "generator": "data/build_boundaries.py",
            "crs": WEB_CRS,
            "gu_hdong_source": f"admdongkor {version} light (vuski/admdongkor, 통계청 SGIS 행정동 경계, CC BY 4.0)",
            "bdong_source": f"브이월드 법정구역정보 (국토교통부, CC BY) {bdong_source.name}" if bdong_source else None,
            "note": "광주 5개 구(동구, 서구, 남구, 북구, 광산구)만 담았다. 바깥 경계는 5개 구를 합친 것이다.",
        },
        "features": [],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="광주 5개 구 경계 자료 만들기")
    parser.add_argument("--version", default=DEFAULT_VERSION, help="admdongkor 판 (기본 20260701)")
    parser.add_argument("--dry-run", action="store_true", help="검사만 하고 파일을 쓰지 않는다")
    parser.add_argument("--check-db", action="store_true", help="서비스 DB의 구·동과 법정동 이름을 맞춰 본다")
    args = parser.parse_args()

    hdong = load_hdong(args.version)
    gu, outline = make_gu_and_outline(hdong)
    problems = check_outline(gu, outline, hdong)

    source = find_bdong_source()
    bdong = None
    if source is None:
        say(f"[알림] {RAW_DIR} 에 법정동 원본이 없어 법정동 없이 만듭니다. 화면은 동을 골라도 구만 강조합니다.")
    else:
        bdong = load_bdong(source, gu)

    if args.check_db:
        check_db(bdong)

    if problems:
        say("[주의] 바깥 경계 검사에서 걸린 것:")
        for text in problems:
            say(f"  - {text}")
    else:
        say("바깥 경계 검사 통과: 유효, 구멍 없음, 작은 섬 없음, 넓이 일치")

    collection = build(args.version, source)
    features = collection["features"]
    features.append(feature("outline", to_web(outline)))
    for row in to_web(gu).itertuples():
        features.append(feature("gu", row.geometry, gu=row.gu))
    for row in to_web(hdong).sort_values(["gu", "name"]).itertuples():
        features.append(feature("hdong", row.geometry, gu=row.gu, name=row.name))
    outputs = [(OUT_PATH, collection)]

    if bdong is not None:
        bdong_collection = build(args.version, source)
        for row in to_web(bdong).sort_values(["gu", "dong"]).itertuples():
            bdong_collection["features"].append(feature("bdong", row.geometry, gu=row.gu, dong=row.dong))
        outputs.append((OUT_BDONG_PATH, bdong_collection))

    for path, data in outputs:
        text = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
        counts = {}
        for f in data["features"]:
            counts[f["properties"]["layer"]] = counts.get(f["properties"]["layer"], 0) + 1
        say(f"{path.name}: {counts}, 크기 {len(text.encode('utf-8')) / 1024:,.0f}KB")
        if not args.dry_run:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text, encoding="utf-8")
            say(f"  썼습니다: {path.relative_to(ROOT)}")
    if args.dry_run:
        say("--dry-run이라 파일을 쓰지 않았습니다.")


if __name__ == "__main__":
    main()
