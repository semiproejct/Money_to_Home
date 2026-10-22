"""광주 5개 구 경계 자료 (frontend/data/boundaries.geojson)의 검사. FR-MAP-28, T-MAP-26

data/build_boundaries.py가 만든 두 파일(boundaries.geojson, boundaries_bdong.geojson)을 지도 화면(js/boundary.js)이 그대로 읽는다.
화면이 기대하는 모양인지, 좌표가 광주 5개 구 안에 있는지, 바깥 경계가 구를 합친 넓이와 맞는지 본다.
geopandas 없이 표준 라이브러리로만 본다 (서버를 켜는 데는 geopandas가 필요 없다).
파일이 아직 없으면 건너뛴다.
"""
import json
import math
from pathlib import Path

import pytest

PATH = Path(__file__).resolve().parent.parent / "frontend" / "data" / "boundaries.geojson"
BDONG_PATH = PATH.with_name("boundaries_bdong.geojson")  # 법정동. 없으면 법정동 검사는 빈 목록으로 지나간다
GU_NAMES = {"동구", "서구", "남구", "북구", "광산구"}
# 광주 5개 구를 넉넉히 감싼 사각형. 무등산 쪽 동구 끝이 경도 127.0을 조금 넘을 수 있어 여유를 둔다
BOUNDS = {"lat": (34.95, 35.35), "lng": (126.55, 127.1)}

pytestmark = pytest.mark.skipif(not PATH.exists(), reason="경계 자료가 아직 없다 (python data/build_boundaries.py)")


@pytest.fixture(scope="module")
def collection():
    data = json.loads(PATH.read_text(encoding="utf-8"))
    if BDONG_PATH.exists():
        data["features"] += json.loads(BDONG_PATH.read_text(encoding="utf-8"))["features"]
    return data


def layer(collection, name):
    return [f for f in collection["features"] if f["properties"]["layer"] == name]


def polygons(geometry):
    return [geometry["coordinates"]] if geometry["type"] == "Polygon" else geometry["coordinates"]


def ring_area_km2(ring):
    """위도·경도 고리의 넓이 (㎢). 작은 지역이라 평면으로 근사한다. 비교에만 쓴다."""
    lat0 = math.radians(sum(p[1] for p in ring) / len(ring))
    kx, ky = 111.320 * math.cos(lat0), 110.574  # 경도·위도 1도의 km
    total = 0.0
    for (x1, y1), (x2, y2) in zip(ring, ring[1:]):
        total += (x1 * kx) * (y2 * ky) - (x2 * kx) * (y1 * ky)
    return abs(total) / 2


def area_km2(geometry):
    return sum(ring_area_km2(p[0]) - sum(ring_area_km2(h) for h in p[1:]) for p in polygons(geometry))


def test_모양(collection):
    assert collection["type"] == "FeatureCollection"
    assert len(layer(collection, "outline")) == 1
    assert {f["properties"]["gu"] for f in layer(collection, "gu")} == GU_NAMES
    assert len(layer(collection, "gu")) == 5
    for f in collection["features"]:
        assert f["geometry"]["type"] in ("Polygon", "MultiPolygon")


def test_구마다_행정동이_있다(collection):
    counts = {}
    for f in layer(collection, "hdong"):
        assert f["properties"]["gu"] in GU_NAMES
        assert f["properties"]["name"]
        counts[f["properties"]["gu"]] = counts.get(f["properties"]["gu"], 0) + 1
    assert set(counts) == GU_NAMES


def test_법정동은_구와_이름이_겹치지_않는다(collection):
    keys = [(f["properties"]["gu"], f["properties"]["dong"]) for f in layer(collection, "bdong")]
    assert all(gu in GU_NAMES and dong for gu, dong in keys)
    assert len(keys) == len(set(keys))


def test_고리가_닫혀_있고_좌표가_광주_5개_구_안이다(collection):
    for f in collection["features"]:
        for polygon in polygons(f["geometry"]):
            for ring in polygon:
                assert len(ring) >= 4
                assert ring[0] == ring[-1]
                for lng, lat in ring:
                    assert BOUNDS["lat"][0] <= lat <= BOUNDS["lat"][1]
                    assert BOUNDS["lng"][0] <= lng <= BOUNDS["lng"][1]


def test_바깥_경계는_구를_합친_넓이와_같고_구멍이_없다(collection):
    outline = layer(collection, "outline")[0]["geometry"]
    assert all(len(p) == 1 for p in polygons(outline)), "바깥 경계 안에 구멍이 있다"
    gu_total = sum(area_km2(f["geometry"]) for f in layer(collection, "gu"))
    assert abs(area_km2(outline) - gu_total) / gu_total < 0.005
    # 광주 5개 구는 약 501㎢다. 자료를 잘못 고르면(시도 전체 등) 크게 어긋난다
    assert 450 < area_km2(outline) < 550
