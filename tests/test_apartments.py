"""아파트 탐색. A-02 구와 동의 목록."""
from datetime import date

import pytest

from backend import models


def _apartment(id, gu, dong, name, lat=None, lng=None, priced=True):
    apt = models.Apartment(id=id, name=name, gu=gu, dong=dong, jibun=str(id), latitude=lat, longitude=lng)
    if priced:
        apt.prices.append(models.ApartmentPrice(
            area_band=84, exclusive_area="84.9400", avg_price=300_000_000, min_price=290_000_000,
            max_price=310_000_000, trade_count=3, period_start=date(2025, 10, 1), period_end=date(2026, 9, 30),
        ))
    return apt


@pytest.fixture
def apartments(db):
    """서구 치평동 2곳(좌표 있음), 서구 광천동 1곳(좌표 없음), 북구 운암동 1곳,
    평균가가 없는 남구 봉선동 1곳과 서구 치평동 1곳."""
    db.add_all([
        _apartment(1, "서구", "치평동", "가아파트", "35.1500000", "126.8500000"),
        _apartment(2, "서구", "치평동", "나아파트", "35.1480000", "126.8400000"),
        _apartment(3, "서구", "광천동", "다아파트"),
        _apartment(4, "북구", "운암동", "라아파트", "35.1800000", "126.8800000"),
        _apartment(5, "남구", "봉선동", "마아파트", "35.1300000", "126.9000000", priced=False),
        _apartment(6, "서구", "치평동", "바아파트", "35.0000000", "126.0000000", priced=False),
    ])
    db.commit()


def test_only_regions_with_prices(client, apartments):
    regions = client.get("/api/regions").json()["regions"]
    assert [r["gu"] for r in regions] == ["북구", "서구"]  # 평균가가 없는 남구는 나오지 않는다


def test_gu_and_dong_in_korean_order(client, apartments):
    seo = client.get("/api/regions").json()["regions"][1]
    assert [d["dong"] for d in seo["dongs"]] == ["광천동", "치평동"]


def test_apartment_count_counts_priced_apartments(client, apartments):
    seo = client.get("/api/regions").json()["regions"][1]
    chipyeong = seo["dongs"][1]
    assert chipyeong["apartment_count"] == 2  # 평균가가 없는 바아파트는 세지 않는다


def test_location_is_average_of_apartments(client, apartments):
    seo = client.get("/api/regions").json()["regions"][1]
    chipyeong = seo["dongs"][1]
    assert chipyeong["latitude"] == pytest.approx(35.149)
    assert chipyeong["longitude"] == pytest.approx(126.845)
    # 구의 위치는 좌표가 있는 아파트(가, 나)의 평균. 좌표가 없는 다아파트와 평균가가 없는 바아파트는 빠진다
    assert seo["latitude"] == pytest.approx(35.149)


def test_location_is_null_without_coordinates(client, apartments):
    seo = client.get("/api/regions").json()["regions"][1]
    gwangcheon = seo["dongs"][0]
    assert gwangcheon["latitude"] is None
    assert gwangcheon["longitude"] is None


def test_empty_db_gives_empty_list(client):
    assert client.get("/api/regions").json() == {"regions": []}


# ------------------------------------------------------------------
# A-05 아파트 찾기
# ------------------------------------------------------------------
def _priced(id, dong, name, bands, lat=None, lng=None, built_year=None):
    """bands: [(면적대, 평균가), ...]"""
    apt = models.Apartment(id=id, name=name, gu="서구", dong=dong, jibun=str(id), latitude=lat, longitude=lng,
                           built_year=built_year)
    for band, price in bands:
        apt.prices.append(models.ApartmentPrice(
            area_band=band, exclusive_area=f"{band}.9400", supply_area=f"{band + 27}.00", avg_price=price,
            min_price=price, max_price=price, trade_count=5,
            period_start=date(2025, 10, 1), period_end=date(2026, 9, 30),
        ))
    return apt


@pytest.fixture
def chipyeong(db, products):
    """서구 치평동. 예시 조건(보유 5,000만, 월 100만, 5년, 첫째 상품 30년)으로 구분이 정해져 있다."""
    db.add_all([
        _priced(11, "치평동", "가아파트", [(114, 390_000_000), (84, 300_000_000)], "35.1490000", "126.8450000", 2005),
        _priced(12, "치평동", "나아파트", [(59, 150_000_000)], built_year=1995),  # 좌표 없음
        _priced(13, "치평동", "다아파트", [(84, 450_000_000)], "35.1500000", "126.8500000", 2015),
        _priced(14, "치평동", "라아파트", [(84, 700_000_000)], "35.1510000", "126.8510000", 2020),
        _priced(15, "치평동", "마아파트", [(84, 360_000_000)], "35.1520000", "126.8520000"),  # 준공 연도 모름
        _priced(16, "광천동", "바아파트", [(84, 200_000_000)]),
        _priced(17, "치평동", "사아파트", []),  # 평균가가 없다
    ])
    db.commit()


EXAMPLE = {
    "current_assets": 50_000_000, "monthly_saving": 1_000_000, "target_years": 5,
    "loan_choice": "product", "loan_product_id": 1, "repayment_years": 30,
}


def _search(client, where=None, filters=None, sort=None, **changes):
    body = {"conditions": {**EXAMPLE, **changes}, "where": {"gu": "서구", "dong": "치평동"} if where is None else where}
    if filters is not None:
        body["filters"] = filters
    if sort is not None:
        body["sort"] = sort
    return client.post("/api/apartments/search", json=body)


def test_target_price_and_own_funds(client, chipyeong):
    body = _search(client).json()
    assert body["target_price"] == 366_666_666
    assert body["own_funds"] == 110_000_000


def test_order_is_category_then_closeness_to_target(client, chipyeong):
    body = _search(client).json()
    # 지금 가능(나) → 기간 내 가능(마 3.6억이 가 3억보다 목표 3.67억에 가깝다) → 자금 부족(다 4.5억, 라 7억)
    assert [a["id"] for a in body["apartments"]] == [12, 15, 11, 13, 14]
    assert [a["category"] for a in body["apartments"]] == ["now", "within", "within", "lack", "lack"]


def test_counts_are_per_apartment(client, chipyeong):
    body = _search(client).json()
    assert body["counts"] == {"now": 1, "within": 2, "lack": 2, "total": 5}
    assert body["counts"]["total"] == len(body["apartments"])  # 평균가가 없는 사아파트는 빠진다


def test_areas_cheapest_first_with_example_values(client, chipyeong):
    ga = next(a for a in _search(client).json()["apartments"] if a["id"] == 11)
    assert [area["area_band"] for area in ga["areas"]] == [84, 114]
    first, second = ga["areas"]
    assert first == {
        "area_band": 84, "exclusive_area": 84.94, "supply_area": 111.0, "avg_price": 300_000_000, "trade_count": 5,
        "category": "within", "shortage": -20_000_000, "loan_amount": 210_000_000, "over_price_cap": False,
    }
    assert (second["category"], second["shortage"], second["loan_amount"]) == ("lack", 7_000_000, 273_000_000)
    assert ga["category"] == "within"  # 첫째 면적의 구분


def test_apartment_without_coordinates_is_kept(client, chipyeong):
    na = next(a for a in _search(client).json()["apartments"] if a["id"] == 12)
    assert na["latitude"] is None and na["longitude"] is None
    assert na["households"] is None


def test_over_price_cap(client, chipyeong):
    ra = next(a for a in _search(client).json()["apartments"] if a["id"] == 14)
    assert ra["areas"][0]["over_price_cap"] is True  # 7억 > 첫째 상품 상한 6억
    ra2 = next(a for a in _search(client, loan_product_id=2, repayment_years=30).json()["apartments"] if a["id"] == 14)
    assert ra2["areas"][0]["over_price_cap"] is False  # 둘째 상품은 상한이 없다


def test_now_has_no_within(client, chipyeong):
    body = _search(client, target_years=0).json()
    assert body["own_funds"] == 50_000_000
    assert body["counts"]["within"] == 0
    assert all(a["category"] != "within" for a in body["apartments"])


def test_without_loan(client, chipyeong):
    body = _search(client, loan_choice="none", loan_product_id=None, repayment_years=None).json()
    assert body["target_price"] == body["own_funds"] == 110_000_000
    assert all(area["loan_amount"] == 0 and area["over_price_cap"] is False
               for a in body["apartments"] for area in a["areas"])


def test_whole_gu_without_dong(client, chipyeong):
    body = _search(client, where={"gu": "서구"}).json()
    assert body["counts"]["total"] == 6  # 광천동 바아파트까지


def test_unknown_dong_gives_empty_list(client, chipyeong):
    res = _search(client, where={"gu": "서구", "dong": "없는동"})
    assert res.status_code == 200
    assert res.json()["apartments"] == []
    assert res.json()["counts"] == {"now": 0, "within": 0, "lack": 0, "total": 0}


@pytest.mark.parametrize("changes, field, detail", [
    ({"loan_product_id": 999}, "loan_product_id", "대출 상품과 상환 기간을 골라 주세요."),
    ({"repayment_years": 25}, "repayment_years", "상환 기간을 다시 골라 주세요."),
    ({"target_years": 7}, "target_years", "목표 기간을 다시 골라 주세요."),
    ({"current_assets": -1}, "current_assets", "0 이상의 숫자만 입력할 수 있습니다."),
])
def test_invalid_conditions(client, chipyeong, changes, field, detail):
    res = _search(client, **changes)
    assert res.status_code == 422
    assert res.json() == {"detail": detail, "field": field}


@pytest.mark.parametrize("changes", [
    {"loan_choice": "none"},                                   # 대출 없이인데 상품이 있다
    {"loan_product_id": None},                                 # 상품인데 번호가 없다
    {"repayment_years": None},                                 # 상품인데 기간이 없다
    {"loan_choice": "none", "loan_product_id": None},          # 대출 없이인데 기간이 남았다
])
def test_loan_combination_is_rejected(client, chipyeong, changes):
    res = _search(client, **changes)
    assert res.status_code == 422
    assert res.json() == {"detail": "대출 상품과 상환 기간을 골라 주세요.", "field": "loan_product_id"}


def test_unknown_loan_choice_uses_spec_message(client, chipyeong):
    res = _search(client, loan_choice="maybe")
    assert res.status_code == 422
    assert res.json() == {"detail": "대출 상품과 상환 기간을 골라 주세요.", "field": "loan_choice"}


# ------------------------------------------------------------------
# A-05 조건 (filters, 2차)
# ------------------------------------------------------------------
def _ids(client, filters):
    return [a["id"] for a in _search(client, filters=filters).json()["apartments"]]


def test_empty_or_null_filters_change_nothing(client, chipyeong):
    assert _ids(client, {}) == _ids(client, {"area_min": None, "price_max": None}) == [12, 15, 11, 13, 14]


def test_area_filter_keeps_matching_areas_only(client, chipyeong):
    body = _search(client, filters={"area_min": 100, "area_max": 114}).json()
    assert [a["id"] for a in body["apartments"]] == [11]  # 114㎡가 있는 가아파트만
    ga = body["apartments"][0]
    assert [area["area_band"] for area in ga["areas"]] == [114]
    assert ga["category"] == "lack"  # 남은 면적(3.9억)의 구분
    assert body["counts"] == {"now": 0, "within": 0, "lack": 1, "total": 1}


def test_area_filter_includes_both_ends(client, chipyeong):
    assert _ids(client, {"area_min": 59, "area_max": 59}) == [12]


def test_price_filter(client, chipyeong):
    # 3억 ~ 4.5억: 마(3.6억), 가(3억, 3.9억), 다(4.5억). 나(1.5억)와 라(7억)는 빠진다
    assert _ids(client, {"price_min": 300_000_000, "price_max": 450_000_000}) == [15, 11, 13]


def test_built_year_filter_drops_unknown_year(client, chipyeong):
    assert _ids(client, {"built_year_min": 2000, "built_year_max": 2015}) == [11, 13]  # 마는 준공 연도를 모른다
    assert _ids(client, {"built_year_max": 2000}) == [12]


def test_filters_together_can_give_empty_list(client, chipyeong):
    res = _search(client, filters={"area_min": 59, "area_max": 59, "built_year_min": 2000})
    assert res.status_code == 200
    assert res.json()["counts"]["total"] == 0


@pytest.mark.parametrize("filters", [
    {"area_min": 85, "area_max": 84},
    {"price_min": 300_000_001, "price_max": 300_000_000},
    {"built_year_min": 2021, "built_year_max": 2020},
])
def test_min_greater_than_max_is_rejected(client, chipyeong, filters):
    res = _search(client, filters=filters)
    assert res.status_code == 422
    assert res.json() == {"detail": "조건의 최소와 최대를 다시 확인해 주세요.", "field": "filters"}


@pytest.mark.parametrize("filters, field, detail", [
    ({"price_min": 1.5}, "price_min", "소수는 입력할 수 없습니다. 만 원 단위의 정수로 입력해 주세요."),
    ({"area_max": "84"}, "area_max", "숫자만 입력할 수 있습니다."),
    ({"built_year_min": True}, "built_year_min", "숫자만 입력할 수 있습니다."),
])
def test_filter_values_must_be_integers(client, chipyeong, filters, field, detail):
    res = _search(client, filters=filters)
    assert res.status_code == 422
    assert res.json() == {"detail": detail, "field": field}


# ------------------------------------------------------------------
# A-05 정렬 (sort, 2차)
# ------------------------------------------------------------------
def _sorted_ids(client, sort, **kw):
    return [a["id"] for a in _search(client, sort=sort, **kw).json()["apartments"]]


def test_sort_category_is_default(client, chipyeong):
    assert _sorted_ids(client, "category") == _sorted_ids(client, None) == [12, 15, 11, 13, 14]


def test_sort_price_asc_by_first_area(client, chipyeong):
    # 첫째 면적의 평균가: 나 1.5억, 가 3억(84㎡), 마 3.6억, 다 4.5억, 라 7억
    assert _sorted_ids(client, "price_asc") == [12, 11, 15, 13, 14]


def test_sort_price_desc(client, chipyeong):
    assert _sorted_ids(client, "price_desc") == [14, 13, 15, 11, 12]


def test_sort_keeps_areas_and_counts(client, chipyeong):
    by_category = _search(client).json()
    by_price = _search(client, sort="price_desc").json()
    assert by_price["counts"] == by_category["counts"]
    ga = next(a for a in by_price["apartments"] if a["id"] == 11)
    assert [area["area_band"] for area in ga["areas"]] == [84, 114]  # 면적은 그대로 평균가 낮은 순


def test_sort_with_filters_uses_remaining_first_area(client, chipyeong):
    # 3.1억 이상만 남기면 가아파트의 첫째 면적은 114㎡(3.9억)가 되어 마(3.6억) 뒤로 간다
    assert _sorted_ids(client, "price_asc", filters={"price_min": 310_000_000}) == [15, 11, 13, 14]


def test_sort_newest_puts_unknown_year_last(client, chipyeong):
    # 라 2020, 다 2015, 가 2005, 나 1995, 마 모름
    assert _sorted_ids(client, "newest") == [14, 13, 11, 12, 15]


def test_sort_area_desc_by_first_area(client, chipyeong):
    # 첫째 면적: 가 · 다 · 라 · 마 84㎡, 나 59㎡. 같으면 번호 순
    assert _sorted_ids(client, "area_desc") == [11, 13, 14, 15, 12]


def test_sort_households_desc_puts_unknown_last(client, db, chipyeong):
    db.get(models.Apartment, 13).households = 300
    db.get(models.Apartment, 11).households = 120
    db.commit()
    assert _sorted_ids(client, "households_desc") == [13, 11, 12, 14, 15]


def test_where_all_finds_every_gu(client, chipyeong):
    ids = {a["id"] for a in _search(client, where={"all": True}).json()["apartments"]}
    assert ids == {11, 12, 13, 14, 15, 16}


def test_where_all_with_gu_is_rejected(client, chipyeong):
    assert _search(client, where={"all": True, "gu": "서구"}).status_code == 422


# ------------------------------------------------------------------
# A-05 · A-12 응답 기억 (backend/services/response_cache.py, 2026-10-20)
# ------------------------------------------------------------------
def test_cache_returns_same_answer_until_new_data(client, db, chipyeong):
    from backend.services import response_cache
    response_cache.enabled = True
    first = _search(client).json()
    db.get(models.Apartment, 13).households = 999  # 적재 기록 없이 바꾸면 기억해 둔 응답이 그대로 나온다
    db.commit()
    assert _search(client).json() == first
    db.add(models.DataCollection(dataset="households", source="test", base_date=date(2026, 10, 20), row_count=1))
    db.commit()  # 새로 넣은 기록이 생기면 다시 계산한다
    again = _search(client).json()
    assert next(a for a in again["apartments"] if a["id"] == 13)["households"] == 999


def test_cache_keeps_requests_apart(client, chipyeong):
    from backend.services import response_cache
    response_cache.enabled = True
    assert _sorted_ids(client, "price_asc") == [12, 11, 15, 13, 14]
    assert _sorted_ids(client, "price_desc") == [14, 13, 15, 11, 12]  # 정렬이 다르면 다른 응답
    assert _search(client, monthly_saving=0).json()["target_price"] != _search(client).json()["target_price"]


def test_cache_does_not_keep_errors(client, chipyeong):
    from backend.services import response_cache
    response_cache.enabled = True
    assert _search(client, sort="name").status_code == 422
    assert _search(client, sort="name").status_code == 422


def test_unknown_sort_is_rejected(client, chipyeong):
    res = _search(client, sort="name")
    assert res.status_code == 422
    assert res.json()["field"] == "sort"


# ------------------------------------------------------------------
# A-05 이름 검색 (where.keyword, 2차)
# ------------------------------------------------------------------
@pytest.fixture
def named(db, chipyeong):
    """치평동 다섯 곳과 광천동 한 곳에 더해, 북구에 이름이 비슷한 두 곳."""
    hoban = _priced(21, "운암동", "호반가아파트", [(84, 250_000_000)])
    hoban.gu = "북구"
    percent = _priced(22, "운암동", "100%아파트", [(59, 120_000_000)])
    percent.gu = "북구"
    db.add_all([hoban, percent])
    db.commit()


def _keyword(client, keyword, **kw):
    return _search(client, where={"keyword": keyword}, **kw)


def test_keyword_searches_all_gu(client, named):
    body = _keyword(client, "가아파트").json()
    assert sorted((a["gu"], a["name"]) for a in body["apartments"]) == [("북구", "호반가아파트"), ("서구", "가아파트")]


def test_keyword_strips_spaces_and_keeps_rules(client, named):
    body = _keyword(client, "  아파트 ").json()
    assert body["counts"]["total"] == 8  # 평균가가 없는 사아파트는 빠진다
    order = [a["category"] for a in body["apartments"]]
    assert order == sorted(order, key=["now", "within", "lack"].index)  # 구분순


def test_keyword_percent_is_plain_text(client, named):
    assert [a["id"] for a in _keyword(client, "%").json()["apartments"]] == [22]
    assert _keyword(client, "_").json()["apartments"] == []


def test_keyword_with_filters_and_sort(client, named):
    ids = [a["id"] for a in _keyword(client, "아파트", filters={"area_max": 59}, sort="price_desc").json()["apartments"]]
    assert ids == [12, 22]  # 59㎡만: 나 1.5억, 100% 1.2억


def test_keyword_no_result_is_empty_list(client, named):
    res = _keyword(client, "없는이름")
    assert res.status_code == 200
    assert res.json()["counts"] == {"now": 0, "within": 0, "lack": 0, "total": 0}


@pytest.mark.parametrize("where, field, detail", [
    ({"keyword": "   "}, "keyword", "입력한 값을 다시 확인해 주세요."),
    ({"keyword": "호반", "gu": "서구"}, "where", "입력한 값을 다시 확인해 주세요."),
    ({"keyword": "호반", "dong": "치평동"}, "where", "입력한 값을 다시 확인해 주세요."),
    ({}, "where", "필요한 값이 빠졌습니다."),
    ({"dong": "치평동"}, "where", "필요한 값이 빠졌습니다."),
    ({"keyword": 3}, "keyword", "입력한 값을 다시 확인해 주세요."),
])
def test_invalid_where(client, named, where, field, detail):
    res = _search(client, where=where)
    assert res.status_code == 422
    assert res.json() == {"detail": detail, "field": field}


# ------------------------------------------------------------------
# A-13 수집 기준일
# ------------------------------------------------------------------
def test_data_status_without_records_is_null(client):
    assert client.get("/api/data-status").json() == {"trades_base_date": None, "households_base_date": None}


def test_data_status_gives_latest_date_per_dataset(client, db):
    db.add_all([
        models.DataCollection(dataset="trades", source="실거래가 API", base_date=date(2026, 10, 12), row_count=16000),
        models.DataCollection(dataset="trades", source="실거래가 공개시스템 CSV", base_date=date(2026, 10, 7), row_count=16919),
        models.DataCollection(dataset="households", source="건축물대장", base_date=date(2026, 8, 31), row_count=1000),
        models.DataCollection(dataset="coordinates", source="카카오", base_date=date(2026, 10, 13), row_count=1055),
    ])
    db.commit()
    # 자료마다 가장 최근에 남긴 줄의 기준일 (DB 설계서 3.7). 좌표의 기준일은 보여 주지 않는다
    assert client.get("/api/data-status").json() == {"trades_base_date": "2026-10-07", "households_base_date": "2026-08-31"}


# A-12 구별·동별 개수 (2차)
# ------------------------------------------------------------------
@pytest.fixture
def two_gu(db, chipyeong):
    """서구(치평동 다섯 곳, 광천동 한 곳)에 더해 북구 운암동 한 곳 (예시 조건으로 지금 가능)."""
    unam = _priced(31, "운암동", "운암아파트", [(59, 100_000_000)], "35.1800000", "126.8800000", 2010)
    unam.gu = "북구"
    db.add(unam)
    db.commit()


def _summary(client, level, gu=None, filters=None, **changes):
    body = {"conditions": {**EXAMPLE, **changes}, "level": level}
    if gu is not None:
        body["gu"] = gu
    if filters is not None:
        body["filters"] = filters
    return client.post("/api/regions/summary", json=body)


def test_summary_by_dong(client, two_gu):
    body = _summary(client, "dong", gu="서구").json()
    assert body["target_price"] == 366_666_666
    assert body["level"] == "dong"
    gwangcheon, chipyeong = body["regions"]  # 가나다순
    assert (chipyeong["gu"], chipyeong["dong"]) == ("서구", "치평동")
    # 나 지금, 마·가 기간 내, 다·라 부족. 평균가가 없는 사아파트는 세지 않는다
    assert chipyeong["counts"] == {"now": 1, "within": 2, "lack": 2, "total": 5}
    assert chipyeong["target_count"] == 3
    # 좌표가 있는 가·다·라·마의 평균. 좌표가 없는 나는 위치에 들어가지 않는다
    assert chipyeong["latitude"] == pytest.approx(35.1505)
    assert chipyeong["longitude"] == pytest.approx(126.8495)
    assert gwangcheon["counts"] == {"now": 0, "within": 1, "lack": 0, "total": 1}
    assert gwangcheon["latitude"] is None and gwangcheon["longitude"] is None


def test_summary_dong_without_gu_gives_all_dongs(client, two_gu):
    regions = _summary(client, "dong").json()["regions"]
    assert [(r["gu"], r["dong"]) for r in regions] == [("북구", "운암동"), ("서구", "광천동"), ("서구", "치평동")]


def test_summary_by_gu(client, two_gu):
    body = _summary(client, "gu", gu="서구").json()  # level이 gu면 gu는 쓰지 않는다
    assert [(r["gu"], r["dong"]) for r in body["regions"]] == [("북구", None), ("서구", None)]
    seo = body["regions"][1]
    assert seo["counts"] == {"now": 1, "within": 3, "lack": 2, "total": 6}
    assert seo["target_count"] == 4


def test_summary_counts_match_search(client, two_gu):
    dongs = _summary(client, "dong", gu="서구", target_years=0).json()["regions"]
    searched = _search(client, where={"gu": "서구"}, target_years=0).json()["counts"]
    for key in ("now", "within", "lack", "total"):
        assert sum(r["counts"][key] for r in dongs) == searched[key]


def test_summary_keeps_zero_regions_with_filters(client, two_gu):
    regions = _summary(client, "dong", gu="서구", filters={"area_min": 100}).json()["regions"]
    gwangcheon, chipyeong = regions
    assert chipyeong["counts"] == {"now": 0, "within": 0, "lack": 1, "total": 1}  # 가아파트 114㎡만
    assert chipyeong["target_count"] == 0
    assert gwangcheon["counts"]["total"] == 0  # 0곳이어도 빼지 않는다 (화면은 점선)
    assert gwangcheon["latitude"] is None


def test_summary_built_year_filter(client, two_gu):
    regions = _summary(client, "gu", filters={"built_year_min": 2006}).json()["regions"]
    assert [r["counts"]["total"] for r in regions] == [1, 2]  # 북구 운암(2010), 서구 다(2015)·라(2020)


@pytest.mark.parametrize("body, field, detail", [
    ({"level": "city"}, "level", "입력한 값을 다시 확인해 주세요."),
    ({}, "level", "필요한 값이 빠졌습니다."),
    ({"level": "dong", "filters": {"price_min": 2, "price_max": 1}}, "filters", "조건의 최소와 최대를 다시 확인해 주세요."),
    ({"level": "gu", "conditions": {**EXAMPLE, "target_years": 7}}, "target_years", "목표 기간을 다시 골라 주세요."),
    ({"level": "gu", "conditions": {**EXAMPLE, "loan_product_id": 999}}, "loan_product_id", "대출 상품과 상환 기간을 골라 주세요."),
])
def test_summary_invalid(client, two_gu, body, field, detail):
    res = client.post("/api/regions/summary", json={"conditions": EXAMPLE, **body})
    assert res.status_code == 422
    assert res.json() == {"detail": detail, "field": field}


def test_summary_empty_db(client, products):
    assert _summary(client, "gu").json()["regions"] == []


# ------------------------------------------------------------------
# A-05 지도 영역 (where.bounds, 2차)
# ------------------------------------------------------------------
def _bounds(client, south, west, north, east, **kw):
    return _search(client, where={"bounds": {"south": south, "west": west, "north": north, "east": east}}, **kw)


def test_bounds_keeps_apartments_inside(client, chipyeong):
    body = _bounds(client, 35.1495, 126.849, 35.1515, 126.8515).json()
    assert [a["id"] for a in body["apartments"]] == [13, 14]  # 다(35.150, 126.850), 라(35.151, 126.851)
    assert body["counts"] == {"now": 0, "within": 0, "lack": 2, "total": 2}


def test_bounds_includes_edges(client, chipyeong):
    # 가(35.149, 126.845)와 다(35.150, 126.850)가 영역의 모서리에 있다
    assert [a["id"] for a in _bounds(client, 35.149, 126.845, 35.15, 126.85).json()["apartments"]] == [11, 13]


def test_bounds_drops_apartments_without_coordinates(client, chipyeong):
    ids = [a["id"] for a in _bounds(client, 35, 126, 36, 127).json()["apartments"]]
    assert ids == [15, 11, 13, 14]  # 좌표가 없는 나(치평동), 바(광천동)는 나오지 않는다 (명세서 Q-8)


def test_bounds_with_filters_and_sort(client, chipyeong):
    ids = [a["id"] for a in _bounds(client, 35, 126, 36, 127, filters={"price_max": 450_000_000}, sort="price_asc").json()["apartments"]]
    assert ids == [11, 15, 13]  # 가 3억, 마 3.6억, 다 4.5억. 라(7억)는 빠진다


def test_bounds_outside_gives_empty_list(client, chipyeong):
    res = _bounds(client, 37.5, 127.0, 37.6, 127.1)
    assert res.status_code == 200
    assert res.json()["counts"]["total"] == 0


@pytest.mark.parametrize("where, field, detail", [
    ({"bounds": {"south": 35.16, "west": 126.83, "north": 35.14, "east": 126.86}}, "bounds", "지도 영역을 다시 확인해 주세요."),
    ({"bounds": {"south": 35.14, "west": 126.86, "north": 35.16, "east": 126.83}}, "bounds", "지도 영역을 다시 확인해 주세요."),
    ({"bounds": {"south": 35.15, "west": 126.83, "north": 35.15, "east": 126.86}}, "bounds", "지도 영역을 다시 확인해 주세요."),
    ({"bounds": {"south": 35.14, "west": 126.83, "north": 35.16}}, "east", "필요한 값이 빠졌습니다."),
    ({"bounds": {"south": "35.14", "west": 126.83, "north": 35.16, "east": 126.86}}, "south", "숫자만 입력할 수 있습니다."),
    ({"bounds": {"south": 35.14, "west": True, "north": 35.16, "east": 126.86}}, "west", "숫자만 입력할 수 있습니다."),
    ({"bounds": {"south": 35.14, "west": 126.83, "north": 35.16, "east": 126.86}, "gu": "서구"}, "where", "입력한 값을 다시 확인해 주세요."),
    ({"bounds": {"south": 35.14, "west": 126.83, "north": 35.16, "east": 126.86}, "keyword": "호반"}, "where", "입력한 값을 다시 확인해 주세요."),
    ({"bounds": {"south": 35.14, "west": 126.83, "north": 35.16, "east": 126.86}, "dong": "치평동"}, "where", "입력한 값을 다시 확인해 주세요."),
])
def test_invalid_bounds(client, chipyeong, where, field, detail):
    res = _search(client, where=where)
    assert res.status_code == 422
    assert res.json() == {"detail": detail, "field": field}


# ------------------------------------------------------------------
# A-24 비슷한 아파트 (3차)
# ------------------------------------------------------------------
@pytest.fixture
def similar_set(db, products):
    """고른 아파트는 21번 치평동 84㎡ 3억. 같은 동 5곳, 같은 구 다른 동 5곳, 다른 구 1곳, 평균가 없는 곳 1곳.
    한 번에 6곳이라 후보 10곳은 6곳 + 4곳으로 나뉜다."""
    north = _priced(28, "운암동", "북구아파트", [(84, 300_000_000)])
    north.gu = "북구"
    db.add_all([
        _priced(21, "치평동", "고른아파트", [(59, 220_000_000), (84, 300_000_000)]),
        _priced(22, "치평동", "가까운면적", [(84, 310_000_000), (114, 400_000_000)], built_year=2020),  # 차이 1,000만 (84㎡)
        _priced(23, "치평동", "작은평형", [(59, 280_000_000)], built_year=2010),  # 차이 2,000만
        _priced(24, "치평동", "같은가격", [(84, 300_000_000)]),  # 차이 0, 준공 연도 모름
        _priced(25, "치평동", "비싼곳", [(114, 500_000_000)], built_year=2015),  # 차이 2억
        _priced(33, "치평동", "같은면적비쌈", [(84, 400_000_000)], built_year=2022),  # 면적은 같고 차이 1억
        _priced(26, "광천동", "옆동1", [(84, 301_000_000)], built_year=2018),  # 차이 100만
        _priced(27, "쌍촌동", "옆동2", [(84, 299_000_000)]),  # 차이 100만
        _priced(30, "광천동", "옆동3", [(84, 305_000_000)]),  # 차이 500만
        _priced(31, "쌍촌동", "옆동4", [(84, 290_000_000)]),  # 차이 1,000만
        _priced(32, "광천동", "옆동5", [(84, 330_000_000)]),  # 차이 3,000만
        north,
        models.Apartment(id=29, name="평균가없음", gu="서구", dong="치평동", jibun="29"),
    ])
    db.commit()


def _similar(client, apartment_id=21, area_band=84, **body):
    return client.post(f"/api/apartments/{apartment_id}/similar",
                       json={"conditions": EXAMPLE, "area_band": area_band, **body})


def test_similar_same_dong_first_then_closest_price(client, similar_set):
    res = _similar(client).json()
    assert res["base_price"] == 300_000_000
    assert res["total"] == 10  # 고른 곳, 북구, 평균가 없는 곳은 빠진다
    # 같은 동(24, 22, 23, 33, 25)을 가격 차이 순으로 먼저, 그다음 같은 구의 다른 동
    assert [a["id"] for a in res["apartments"]] == [24, 22, 23, 33, 25, 26]
    assert (res["offset"], res["next_offset"]) == (0, 6)


def test_similar_refresh_goes_to_next_then_wraps(client, similar_set):
    second = _similar(client, offset=6).json()
    # 다른 동의 나머지. 차이가 같으면(26, 27 모두 100만) 번호 순
    assert [a["id"] for a in second["apartments"]] == [27, 30, 31, 32]
    assert second["next_offset"] == 0  # 끝까지 봤으면 처음 여섯 곳으로
    assert [a["id"] for a in _similar(client, offset=10).json()["apartments"]] == [24, 22, 23, 33, 25, 26]


def test_similar_sort_area(client, similar_set):
    # 같은 동 먼저, 그 안에서 고른 84㎡와 전용면적이 가까운 순 (84 → 59 → 114), 같으면 가격 차이 순 (24 → 22 → 33)
    res = _similar(client, sort="area").json()
    assert [a["id"] for a in res["apartments"]] == [24, 22, 33, 23, 25, 26]
    assert [a["id"] for a in _similar(client, sort="area", offset=6).json()["apartments"]] == [27, 30, 31, 32]


def test_similar_sort_area_picks_closest_area(client, similar_set):
    # 22는 84㎡와 114㎡가 있다. 면적순이면 가격이 아니라 면적이 가까운 84㎡로 견준다
    item = next(a for a in _similar(client, sort="area").json()["apartments"] if a["id"] == 22)
    assert [a["area_band"] for a in item["areas"]] == [84]


def test_similar_sort_newest(client, similar_set):
    # 같은 동 먼저, 준공 연도가 최근인 순 (2022, 2020, 2015, 2010, 모름), 그다음 다른 동 (2018, 그리고 모르는 곳은 가격 차이 순)
    res = _similar(client, sort="newest").json()
    assert [a["id"] for a in res["apartments"]] == [33, 22, 25, 23, 24, 26]
    assert [a["id"] for a in _similar(client, sort="newest", offset=6).json()["apartments"]] == [27, 30, 31, 32]


def test_similar_uses_closest_area(client, similar_set):
    near = _similar(client).json()["apartments"][1]
    assert near["id"] == 22
    assert [a["area_band"] for a in near["areas"]] == [84]  # 4억인 114㎡가 아니라 3억 1,000만인 84㎡
    assert near["category"] == near["areas"][0]["category"]


def test_similar_base_is_chosen_area(client, similar_set):
    # 59㎡(2억 2,000만)를 고르면 같은 동에서 2억 8,000만(23)이 가장 가깝다
    res = _similar(client, area_band=59).json()
    assert res["base_price"] == 220_000_000
    assert res["apartments"][0]["id"] == 23


def test_similar_category_matches_search(client, similar_set):
    item = _similar(client).json()["apartments"][0]
    found = next(a for a in _search(client).json()["apartments"] if a["id"] == item["id"])
    assert item["areas"][0] == found["areas"][0]


@pytest.mark.parametrize("apartment_id, area_band", [(999, 84), (21, 114), (29, 84)])
def test_similar_unknown_apartment_or_area(client, similar_set, apartment_id, area_band):
    res = _similar(client, apartment_id, area_band)
    assert res.status_code == 404
    assert res.json()["detail"] == "아파트를 찾을 수 없습니다."


@pytest.mark.parametrize("body, field, detail", [
    ({"offset": -1}, "offset", "입력한 값을 다시 확인해 주세요."),
    ({"sort": "distance"}, "sort", "입력한 값을 다시 확인해 주세요."),
    ({"offset": 1.5}, "offset", "소수는 입력할 수 없습니다. 만 원 단위의 정수로 입력해 주세요."),
    ({"area_band": "84"}, "area_band", "숫자만 입력할 수 있습니다."),
    ({"conditions": {**EXAMPLE, "loan_product_id": 999}}, "loan_product_id", "대출 상품과 상환 기간을 골라 주세요."),
])
def test_similar_invalid(client, similar_set, body, field, detail):
    res = client.post("/api/apartments/21/similar", json={"conditions": EXAMPLE, "area_band": 84, **body})
    assert res.status_code == 422
    assert res.json() == {"detail": detail, "field": field}


def test_similar_alone_in_gu(client, similar_set):
    res = _similar(client, 28).json()  # 북구에는 이 아파트뿐이다
    assert res == {"base_price": 300_000_000, "total": 0, "offset": 0, "next_offset": 0, "apartments": []}


# ------------------------------------------------------------------
# A-27 실거래 기록과 같은 동 비교 (시나리오 탭 그래프)
# ------------------------------------------------------------------
@pytest.fixture
def history_set(db):
    """41번 치평동 84㎡: 평균가 기간 안 거래 3건(해제 1건), 기간 밖 1건, 다른 면적 1건. 같은 동 84㎡ 2곳, 다른 동 1곳."""
    me = _priced(41, "치평동", "고른곳", [(84, 300_000_000)])
    db.add_all([
        me,
        _priced(42, "치평동", "싼곳", [(84, 250_000_000)]),
        _priced(43, "치평동", "비싼곳", [(84, 400_000_000), (59, 200_000_000)]),
        _priced(44, "치평동", "작은곳만", [(59, 180_000_000)]),
        _priced(45, "광천동", "옆동", [(84, 100_000_000)]),
    ])
    db.add_all([
        models.Trade(apartment_id=41, contract_date=date(2025, 11, 3), exclusive_area="84.9400", price=290_000_000, floor=3),
        models.Trade(apartment_id=41, contract_date=date(2026, 2, 10), exclusive_area="84.9400", price=310_000_000, floor=12),
        models.Trade(apartment_id=41, contract_date=date(2026, 2, 10), exclusive_area="84.9400", price=310_000_000, floor=12,
                     is_canceled=True),
        models.Trade(apartment_id=41, contract_date=date(2024, 5, 1), exclusive_area="84.9400", price=200_000_000, floor=1),
        models.Trade(apartment_id=41, contract_date=date(2026, 3, 1), exclusive_area="59.9000", price=210_000_000, floor=5),
    ])
    db.commit()


def test_price_history(client, history_set):
    res = client.get("/api/apartments/41/price-history", params={"area_band": 84})
    assert res.status_code == 200
    body = res.json()
    assert (body["avg_price"], body["period_start"], body["period_end"]) == (300_000_000, "2025-10-01", "2026-09-30")
    # 기간 안의 84㎡ 거래만, 계약일 순. 해제된 거래도 들어 있다
    assert [(t["contract_date"], t["price"], t["is_canceled"]) for t in body["trades"]] == [
        ("2025-11-03", 290_000_000, False), ("2026-02-10", 310_000_000, False), ("2026-02-10", 310_000_000, True),
    ]
    # 같은 동 같은 면적대만, 싼 순. 고른 곳 표시
    assert [(n["id"], n["is_self"]) for n in body["neighbors"]] == [(42, False), (41, True), (43, False)]


def test_price_history_unknown(client, history_set):
    assert client.get("/api/apartments/41/price-history", params={"area_band": 59}).status_code == 404
    assert client.get("/api/apartments/999/price-history", params={"area_band": 84}).status_code == 404
