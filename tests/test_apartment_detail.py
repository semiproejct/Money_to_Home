"""아파트 한 곳. A-06 GET /api/apartments/{id}"""
from datetime import date

import pytest

from backend import models


def _price(band, exclusive, supply, avg, low, high, count):
    return models.ApartmentPrice(
        area_band=band, exclusive_area=exclusive, supply_area=supply, avg_price=avg, min_price=low,
        max_price=high, trade_count=count, period_start=date(2025, 10, 1), period_end=date(2026, 9, 30),
    )


@pytest.fixture
def apartments(db):
    """가아파트: 면적 둘(비싼 쪽을 먼저 넣는다), 좌표·도로명·준공 연도 있음.
    나아파트: 좌표, 도로명, 준공 연도, 공급면적이 없음. 세대수 500.
    세대수 자료의 기준일 기록 두 줄."""
    ga = models.Apartment(
        id=12, name="가아파트", gu="서구", dong="치평동", jibun="1200", road_address="상무중앙로 1",
        built_year=2005, latitude="35.1490000", longitude="126.8450000",
    )
    ga.prices.append(_price(114, "114.9000", "145.00", 420_000_000, 400_000_000, 440_000_000, 6))
    ga.prices.append(_price(84, "84.9400", "111.00", 300_000_000, 270_000_000, 330_000_000, 14))
    na = models.Apartment(id=13, name="나아파트", gu="서구", dong="치평동", jibun="산1-9", households=500)
    na.prices.append(_price(59, "59.9000", None, 150_000_000, 150_000_000, 150_000_000, 1))
    db.add_all([
        ga,
        na,
        models.DataCollection(dataset="households", source="광주 5개 구 아파트 현황", base_date=date(2026, 5, 31)),
        models.DataCollection(dataset="households", source="광주 5개 구 아파트 현황", base_date=date(2026, 8, 31)),
        models.DataCollection(dataset="trades", source="실거래가 API", base_date=date(2026, 10, 7)),
    ])
    db.commit()


def test_apartment_with_areas_cheapest_first(client, apartments):
    res = client.get("/api/apartments/12")
    assert res.status_code == 200
    body = res.json()
    assert body == {
        "id": 12, "name": "가아파트", "gu": "서구", "dong": "치평동", "jibun": "1200",
        "road_address": "상무중앙로 1", "built_year": 2005, "latitude": 35.149, "longitude": 126.845,
        "households": None, "households_base_date": None,
        "areas": [
            {"area_band": 84, "exclusive_area": 84.94, "supply_area": 111.0, "avg_price": 300_000_000,
             "min_price": 270_000_000, "max_price": 330_000_000, "trade_count": 14,
             "period_start": "2025-10-01", "period_end": "2026-09-30"},
            {"area_band": 114, "exclusive_area": 114.9, "supply_area": 145.0, "avg_price": 420_000_000,
             "min_price": 400_000_000, "max_price": 440_000_000, "trade_count": 6,
             "period_start": "2025-10-01", "period_end": "2026-09-30"},
        ],
        "facilities": [], "facilities_base_date": None,
    }


def test_unknown_values_are_null(client, apartments):
    body = client.get("/api/apartments/13").json()
    assert body["road_address"] is None
    assert body["built_year"] is None
    assert body["latitude"] is None and body["longitude"] is None
    assert body["areas"][0]["supply_area"] is None


def test_households_with_latest_base_date(client, apartments):
    body = client.get("/api/apartments/13").json()
    assert body["households"] == 500
    assert body["households_base_date"] == "2026-08-31"  # 세대수 자료의 가장 최근 기준일


def test_households_unknown_has_no_base_date(client, apartments):
    assert client.get("/api/apartments/12").json()["households_base_date"] is None


def test_unknown_id_is_404(client, apartments):
    res = client.get("/api/apartments/999")
    assert res.status_code == 404
    assert res.json() == {"detail": "아파트를 찾을 수 없습니다."}


def test_id_must_be_number(client, apartments):
    res = client.get("/api/apartments/abc")
    assert res.status_code == 422
    assert res.json()["detail"] == "숫자만 입력할 수 있습니다."


def test_search_still_works(client, apartments):
    # 같은 /api/apartments 아래의 A-05(POST /search)가 A-06과 겹치지 않는다
    res = client.get("/api/apartments/search")
    assert res.status_code == 422  # "search"는 번호가 아니다. A-05는 POST다


# ------------------------------------------------------------------
# 주변 시설 (FR-MAP-23). data/load_facilities.py가 미리 넣은 apartment_facilities를 그대로 준다
# ------------------------------------------------------------------
def _facility(kind, name, distance, count, radius=1000, exit_no=None, lat=None, lng=None):
    return models.ApartmentFacility(
        apartment_id=12, kind=kind, place_name=name, distance=distance, exit_no=exit_no, place_count=count, radius=radius,
        latitude=lat, longitude=lng,
    )


@pytest.fixture
def facilities(db, apartments):
    """가아파트에만 시설. 일부러 화면 순서와 다르게 넣는다. 기준일 기록 두 줄"""
    db.add_all([
        _facility("bus", "치평동 정류장", 90, 6, lat="35.1471000", lng="126.8440000"),
        _facility("university", "광주여자대학교", 1752, 2, radius=5000),
        _facility("mart", None, None, 0),
        _facility("subway", "김대중컨벤션센터역 광주1호선", 330, 2, exit_no=5, lat="35.1466500", lng="126.8414200"),
        _facility("school", "전남고등학교", 130, 4),
        models.DataCollection(dataset="facilities", source="카카오 로컬 API (장소 검색)", base_date=date(2026, 10, 1)),
        models.DataCollection(dataset="facilities", source="카카오 로컬 API (장소 검색)", base_date=date(2026, 10, 19)),
    ])
    db.commit()


def test_facilities_in_screen_order(client, facilities):
    body = client.get("/api/apartments/12").json()
    assert [f["kind"] for f in body["facilities"]] == ["subway", "school", "mart", "university", "bus"]  # 버스정류장은 맨 뒤
    assert body["facilities"][0] == {
        "kind": "subway", "place_name": "김대중컨벤션센터역 광주1호선", "distance": 330, "exit_no": 5,
        "place_count": 2, "radius": 1000, "latitude": 35.14665, "longitude": 126.84142,  # 지하철은 출구의 좌표
    }
    # 반경 안에 없으면 이름과 거리가 null ("근처에 없음")
    assert body["facilities"][2] == {"kind": "mart", "place_name": None, "distance": None, "exit_no": None,
                                     "place_count": 0, "radius": 1000, "latitude": None, "longitude": None}
    assert body["facilities_base_date"] == "2026-10-19"


def test_no_facilities_has_no_base_date(client, facilities):
    body = client.get("/api/apartments/13").json()
    assert body["facilities"] == []
    assert body["facilities_base_date"] is None
