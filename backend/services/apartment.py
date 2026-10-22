"""아파트 탐색에 쓰는 DB 함수. 담당: 김목산

routers/apartments.py가 부른다. 저장은 하지 않는다 (읽기만 한다).
요청에 든 값만 쓴다. 로그인 정보와 profiles 표를 읽지 않는다 (NFR-18).
"""
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from backend.errors import ApiError
from backend.models import Apartment, ApartmentPrice, DataCollection, Trade
from backend.services import calc, loan_product

MSG_CHOOSE_LOAN = "대출 상품과 상환 기간을 골라 주세요."
MSG_CHOOSE_YEARS = "상환 기간을 다시 골라 주세요."
MSG_NO_APARTMENT = "아파트를 찾을 수 없습니다."  # A-06, A-07과 같은 문장
SIMILAR_COUNT = 6  # A-24 한 번에 보여 주는 비슷한 아파트 수 (2026-10-18, 예전에는 3)
CATEGORY_ORDER = {calc.NOW: 0, calc.WITHIN: 1, calc.LACK: 2}


def _coord(value) -> float | None:
    """좌표 평균(DECIMAL)을 float로. 좌표가 있는 아파트가 없으면 None."""
    return None if value is None else round(float(value), 7)


def regions(db: Session) -> list[dict]:
    """A-02 구와 동의 목록.

    - 평균가가 있는 아파트가 한 곳이라도 있는 구와 동만 낸다.
    - apartment_count는 그 동에서 평균가가 있는 아파트의 수다.
    - 위치는 그 구나 동에 있는 아파트 좌표의 평균이다. 좌표가 있는 아파트가 없으면 None (API 명세서 A-02).
    - 구와 동은 가나다순이다.
    """
    priced = select(ApartmentPrice.apartment_id).distinct()
    rows = db.execute(
        select(
            Apartment.gu,
            Apartment.dong,
            func.count(Apartment.id),
            func.avg(Apartment.latitude),
            func.avg(Apartment.longitude),
        )
        .where(Apartment.id.in_(priced))
        .group_by(Apartment.gu, Apartment.dong)
    ).all()
    gu_rows = db.execute(
        select(Apartment.gu, func.avg(Apartment.latitude), func.avg(Apartment.longitude))
        .where(Apartment.id.in_(priced))
        .group_by(Apartment.gu)
    ).all()

    result = {
        gu: {"gu": gu, "latitude": _coord(lat), "longitude": _coord(lng), "dongs": []}
        for gu, lat, lng in sorted(gu_rows, key=lambda r: r[0])
    }
    for gu, dong, count, lat, lng in sorted(rows, key=lambda r: (r[0], r[1])):
        result[gu]["dongs"].append(
            {"dong": dong, "apartment_count": count, "latitude": _coord(lat), "longitude": _coord(lng)}
        )
    return list(result.values())


def _product_for(db: Session, conditions) -> dict | None:
    """조건의 대출 상품을 계산 모듈에 넘길 모양으로. 대출 없이 계산이면 None.

    API 명세서 2.2의 조합(product면 상품과 기간이 다 있고, none이면 둘 다 없다)이 아니거나,
    없는 상품이면 "대출 상품과 상환 기간을 골라 주세요."(field loan_product_id),
    그 상품에 없는 상환 기간이면 "상환 기간을 다시 골라 주세요."(field repayment_years). 모두 422 (명세서 5장).
    """
    has_product = conditions.loan_product_id is not None and conditions.repayment_years is not None
    has_nothing = conditions.loan_product_id is None and conditions.repayment_years is None
    if conditions.loan_choice == "none":
        if not has_nothing:
            raise ApiError(422, MSG_CHOOSE_LOAN, "loan_product_id")
        return None
    if not has_product:
        raise ApiError(422, MSG_CHOOSE_LOAN, "loan_product_id")
    product = loan_product.find_by_id(db, conditions.loan_product_id)
    if product is None:
        raise ApiError(422, MSG_CHOOSE_LOAN, "loan_product_id")
    if conditions.repayment_years not in product.repayment_years_list:
        raise ApiError(422, MSG_CHOOSE_YEARS, "repayment_years")
    return loan_product.for_calc(product)


def _in_range(value, low, high) -> bool:
    """low ~ high 안에 있는지 (양 끝 포함). None인 쪽은 조건이 없다."""
    return (low is None or value >= low) and (high is None or value <= high)


def _basis(db: Session, conditions) -> dict:
    """조건으로 정해지는 값. 상품, 현재 보유자산, 목표 기간, 자기자금(C-03), 목표 가능 가격(C-08)."""
    product = _product_for(db, conditions)
    current = conditions.current_assets
    years = conditions.target_years
    own = calc.own_funds(current, calc.accumulated_saving(conditions.monthly_saving, years))
    return {"product": product, "current": current, "years": years, "own": own,
            "target": calc.target_price(own, product)}


def _with_built_year(query, filters):
    """준공 연도 조건. 조건이 있으면 준공 연도를 모르는 아파트는 빠진다."""
    if filters is not None and filters.built_year_min is not None:
        query = query.where(Apartment.built_year >= filters.built_year_min)
    if filters is not None and filters.built_year_max is not None:
        query = query.where(Apartment.built_year <= filters.built_year_max)
    return query


def _item(apt, filters, basis) -> dict | None:
    """아파트 한 곳의 A-05 모양. 조건에 맞는 면적이 없으면 None.

    면적대와 평균가 조건은 면적마다 본다. areas는 평균가가 낮은 순이고, 아파트의 구분은 첫째 면적의 구분이다.
    """
    product, current, years, own = basis["product"], basis["current"], basis["years"], basis["own"]
    cap = product["max_house_price"] if product else None
    areas = []
    for price in sorted(apt.prices, key=lambda p: (p.avg_price, p.area_band)):
        if filters is not None and not (
            _in_range(price.area_band, filters.area_min, filters.area_max)
            and _in_range(price.avg_price, filters.price_min, filters.price_max)
        ):
            continue
        loan = calc.loan_amount(price.avg_price, product)
        areas.append({
            "area_band": price.area_band,
            "exclusive_area": float(price.exclusive_area),
            "supply_area": None if price.supply_area is None else float(price.supply_area),
            "avg_price": price.avg_price,
            "trade_count": price.trade_count,
            "category": calc.category(current, own, loan, price.avg_price, years),
            "shortage": calc.shortage(price.avg_price, own, loan),
            "loan_amount": loan,
            "over_price_cap": cap is not None and price.avg_price > cap,
        })
    if not areas:
        return None
    return {
        "id": apt.id,
        "name": apt.name,
        "gu": apt.gu,
        "dong": apt.dong,
        "latitude": _coord(apt.latitude),
        "longitude": _coord(apt.longitude),
        "built_year": apt.built_year,
        "households": apt.households,
        "category": areas[0]["category"],
        "areas": areas,
    }


def _counts(categories) -> dict:
    """구분별 아파트 수와 전체 수."""
    counts = {key: 0 for key in CATEGORY_ORDER}
    for category in categories:
        counts[category] += 1
    counts["total"] = sum(counts.values())
    return counts


def search(
    db: Session,
    conditions,
    gu: str | None,
    dong: str | None,
    filters=None,
    sort: str = "category",
    keyword: str | None = None,
    bounds=None,
    everywhere: bool = False,
) -> dict:
    """A-05 아파트 찾기. 계산은 services/calc.py의 함수만 부른다 (NFR-13).

    - 범위: 셋 중 하나
      gu와 dong : 그 구와 동 (dong이 없으면 구 전체)
      bounds    : 지도에 보이는 영역. 위도가 south ~ north, 경도가 west ~ east인 아파트 (양 끝 포함, FR-MAP-01, 22)
      keyword   : 광주 5개 구 전체에서 이름에 그 글자가 든 아파트
      everywhere: 광주 5개 구 전체 (where.all)
    - 평균가가 있는 아파트만 낸다. 좌표가 없는 아파트도 빼지 않는다. 다만 bounds로 찾을 때는 나오지 않는다 (명세서 Q-8).
    - filters: 면적대와 평균가는 면적마다, 준공 연도는 아파트마다 본다 (FR-APT-03, 09, 10).
      조건에 맞는 면적이 하나도 없는 아파트는 빠진다. 준공 연도 조건이 있으면 준공 연도를 모르는 아파트는 빠진다.
    - areas는 조건에 맞는 면적만, 평균가가 낮은 순이고, 아파트의 구분은 첫째 면적의 구분이다.
    - 순서 (sort)
      category  : 지금 가능 → 기간 내 가능 → 자금 부족. 같은 구분 안에서는 평균가가 목표 가능 가격에 가까운 순.
      price_asc : 첫째 면적의 평균가가 낮은 순. price_desc: 높은 순 (FR-APT-06, 와이어프레임 B2).
      area_desc : 첫째 면적의 전용면적이 넓은 순. households_desc: 세대수가 많은 순. newest: 준공 연도가 최근인 순.
                  세대수나 준공 연도를 모르면 맨 뒤 (2026-10-20).
      값이 같으면 아파트 번호 순이다. areas의 순서(평균가 낮은 순)는 sort와 상관없이 같다.
    - counts는 아파트 단위로 센다. 자금이 부족한 아파트도 항상 준다.
    """
    basis = _basis(db, conditions)
    target = basis["target"]

    query = select(Apartment).options(selectinload(Apartment.prices))
    if everywhere:
        pass  # DB에는 광주 5개 구의 아파트만 있다
    elif keyword is not None:
        # %와 _도 글자 그대로 찾는다 (autoescape)
        query = query.where(Apartment.name.contains(keyword, autoescape=True))
    elif bounds is not None:
        # 좌표 칸이 DECIMAL이라 Decimal로 바꿔 비교한다 (경계의 값이 소수 오차로 빠지지 않게).
        # 좌표가 없는 아파트는 BETWEEN에 걸리지 않아 저절로 빠진다
        south, west, north, east = (Decimal(str(v)) for v in (bounds.south, bounds.west, bounds.north, bounds.east))
        query = query.where(Apartment.latitude.between(south, north), Apartment.longitude.between(west, east))
    else:
        query = query.where(Apartment.gu == gu)
        if dong:
            query = query.where(Apartment.dong == dong)
    query = _with_built_year(query, filters)

    items = [item for apt in db.scalars(query).all() if (item := _item(apt, filters, basis)) is not None]

    if sort == "price_asc":
        items.sort(key=lambda a: (a["areas"][0]["avg_price"], a["id"]))
    elif sort == "price_desc":
        items.sort(key=lambda a: (-a["areas"][0]["avg_price"], a["id"]))
    elif sort == "area_desc":
        items.sort(key=lambda a: (-a["areas"][0]["exclusive_area"], a["id"]))
    elif sort == "households_desc":
        items.sort(key=lambda a: (a["households"] is None, -(a["households"] or 0), a["id"]))
    elif sort == "newest":
        items.sort(key=lambda a: (a["built_year"] is None, -(a["built_year"] or 0), a["id"]))
    else:
        items.sort(key=lambda a: (CATEGORY_ORDER[a["category"]], abs(a["areas"][0]["avg_price"] - target), a["id"]))
    counts = _counts(a["category"] for a in items)
    return {"target_price": target, "own_funds": basis["own"], "counts": counts, "apartments": items}


def regions_summary(db: Session, conditions, level: str, gu: str | None, filters=None) -> dict:
    """A-12 구별·동별 개수. 지도를 넓게 볼 때의 구 표시와 동 표시에 쓴다 (FR-MAP-20, 21, 31).

    - level이 gu면 구마다, dong이면 동마다 하나. dong일 때 gu가 있으면 그 구의 동만, 없으면 5개 구의 모든 동.
      level이 gu일 때 gu는 쓰지 않는다.
    - 구분은 A-05와 같다 (조건에 맞는 면적 가운데 가장 싼 면적의 구분, 명세서 부록 C). 아파트마다 한 번만 센다.
    - target_count는 목표할 수 있는 아파트 수 (지금 + 기간 내).
    - 지역은 A-02와 같다. 평균가가 있는 아파트가 있는 구·동은 모두 내고, 조건 때문에 0곳이어도 빼지 않는다
      (화면은 0곳을 점선으로 그린다). 위치도 A-02처럼 그 지역 아파트 좌표의 평균이라 조건을 바꿔도 움직이지 않는다.
    - 구와 동은 가나다순이다.
    """
    basis = _basis(db, conditions)
    by_gu = level == "gu"
    only_gu = gu if not by_gu else None

    # 지역과 위치: A-02와 같은 SQL로 구한다 (평균가가 있는 아파트 좌표의 평균)
    columns = [Apartment.gu] if by_gu else [Apartment.gu, Apartment.dong]
    place = select(*columns, func.avg(Apartment.latitude), func.avg(Apartment.longitude)).where(
        Apartment.id.in_(select(ApartmentPrice.apartment_id).distinct())
    )
    if only_gu is not None:
        place = place.where(Apartment.gu == only_gu)
    places = {tuple(row[:-2]): (row[-2], row[-1]) for row in db.execute(place.group_by(*columns)).all()}

    # 구분: A-05와 같은 함수(_item)로 아파트마다 매기고 지역별로 센다
    query = _with_built_year(select(Apartment).options(selectinload(Apartment.prices)), filters)
    if only_gu is not None:
        query = query.where(Apartment.gu == only_gu)
    categories: dict[tuple, list] = {key: [] for key in places}
    for apt in db.scalars(query).all():
        item = _item(apt, filters, basis)
        if item is not None:
            categories[(apt.gu,) if by_gu else (apt.gu, apt.dong)].append(item["category"])

    result = []
    for key in sorted(places):
        lat, lng = places[key]
        counts = _counts(categories[key])
        result.append({
            "gu": key[0],
            "dong": None if by_gu else key[1],
            "latitude": _coord(lat),
            "longitude": _coord(lng),
            "target_count": counts[calc.NOW] + counts[calc.WITHIN],
            "counts": counts,
        })
    return {"target_price": basis["target"], "level": level, "regions": result}


def similar(db: Session, apartment_id: int, area_band: int, conditions, offset: int = 0, sort: str = "similar") -> dict:
    """A-24 비슷한 아파트 (FR-APT-17, 3차). 고른 아파트와 지역, 가격(또는 면적, 준공 연도)이 비슷한 아파트를 여섯 곳씩 보여 준다.

    - 기준 가격: 고른 아파트의 고른 면적의 평균가. 없는 아파트나 그 면적의 평균가가 없으면 404.
    - 후보: 같은 구에서 평균가가 있는 아파트 (고른 아파트는 뺀다).
      아파트마다 면적과 상관없이 평균가가 기준 가격에 가장 가까운 면적 하나로 견준다.
      차이가 같으면 싼 면적, 그다음 면적대가 작은 것.
    - 순서 (sort): 모두 같은 동이 먼저, 그다음 같은 구의 다른 동. 그 안에서
        similar: 기준 가격과의 차이가 작은 순. 가격이 가까우면 구분도 대개 같다 (구분은 면적의 평균가로 정해진다)
        area   : 고른 면적의 전용면적과 차이가 작은 순 (아파트마다 전용면적이 가장 가까운 면적 하나로 견준다), 같으면 가격 차이 순
        newest : 준공 연도가 최근인 순 (모르면 뒤), 같으면 가격 차이 순
      마지막은 아파트 번호 순. 새로고침(offset)은 같은 순서로 다음 곳들을 준다 (2026-10-18)
    - offset부터 여섯 곳을 준다. next_offset은 다음 여섯 곳의 시작이고, 끝까지 봤으면 0이다 (처음으로 돌아간다).
      보낸 offset이 후보 수 이상이면 0부터 준다.
    - 구분, 부족자금, 대출금액은 A-05와 같은 함수(_item)로 매긴다.
    """
    basis = _basis(db, conditions)
    base = db.scalars(
        select(ApartmentPrice).where(ApartmentPrice.apartment_id == apartment_id, ApartmentPrice.area_band == area_band)
    ).first()
    if base is None:
        raise ApiError(404, MSG_NO_APARTMENT)
    chosen = db.get(Apartment, apartment_id)
    base_price = base.avg_price
    base_area = float(base.exclusive_area)

    query = (
        select(Apartment)
        .options(selectinload(Apartment.prices))
        .where(Apartment.gu == chosen.gu, Apartment.id != chosen.id)
    )
    candidates = []
    for apt in db.scalars(query).all():
        item = _item(apt, None, basis)
        if item is None:
            continue
        if sort == "area":
            closest = min(item["areas"], key=lambda a: (abs(a["exclusive_area"] - base_area), abs(a["avg_price"] - base_price), a["area_band"]))
        else:
            closest = min(item["areas"], key=lambda a: (abs(a["avg_price"] - base_price), a["avg_price"], a["area_band"]))
        item["areas"] = [closest]
        item["category"] = closest["category"]
        price_gap = abs(closest["avg_price"] - base_price)
        if sort == "area":
            order = (abs(closest["exclusive_area"] - base_area), price_gap)
        elif sort == "newest":
            order = (-(apt.built_year or 0) if apt.built_year else float("inf"), price_gap)
        else:
            order = (price_gap,)
        candidates.append(((apt.dong != chosen.dong, *order, apt.id), item))
    candidates.sort(key=lambda c: c[0])

    total = len(candidates)
    start = offset if offset < total else 0
    end = start + SIMILAR_COUNT
    return {
        "base_price": base_price,
        "total": total,
        "offset": start,
        "next_offset": end if end < total else 0,
        "apartments": [c[1] for c in candidates[start:end]],
    }


def _latest_base_date(db: Session, dataset: str):
    """그 자료의 가장 최근에 남긴 줄의 기준일. 남긴 줄이 없으면 None."""
    return db.scalar(
        select(DataCollection.base_date)
        .where(DataCollection.dataset == dataset)
        .order_by(DataCollection.id.desc())
        .limit(1)
    )


def data_status(db: Session) -> dict:
    """A-13 수집 기준일. 자료 종류마다 가장 최근에 남긴 줄의 기준일 (DB 설계서 3.7, FR-DATA-05).

    실거래는 data/load_trades.py가 넣을 때 남긴다. 세대수는 아직 넣는 스크립트가 없어 None이다.
    """
    return {
        "trades_base_date": _latest_base_date(db, "trades"),
        "households_base_date": _latest_base_date(db, "households"),
    }


def price_history(db: Session, apartment_id: int, area_band: int) -> dict:
    """A-27 실거래 기록과 같은 동 비교 (시나리오 탭의 그래프, 2026-10-18). 계산하지 않고 DB의 값을 그대로 준다.

    - 고른 아파트의 그 면적대 평균가(apartment_prices)가 없으면 404.
    - trades: 평균가에 들어간 기간(period_start ~ period_end) 안의 그 면적대 거래. 해제된 거래도 넣는다 (화면이 따로 표시).
      면적대는 전용면적의 소수점 아래를 버린 값이다 (data/load_trades.py와 같다).
    - neighbors: 같은 구·동에서 같은 면적대의 평균가가 있는 아파트. 평균가가 싼 순, 같으면 번호 순.
    """
    price = db.scalars(
        select(ApartmentPrice).where(ApartmentPrice.apartment_id == apartment_id, ApartmentPrice.area_band == area_band)
    ).first()
    if price is None:
        raise ApiError(404, MSG_NO_APARTMENT)
    chosen = db.get(Apartment, apartment_id)

    rows = db.scalars(
        select(Trade)
        .where(
            Trade.apartment_id == apartment_id,
            Trade.contract_date >= price.period_start,
            Trade.contract_date <= price.period_end,
        )
        .order_by(Trade.contract_date, Trade.id)
    ).all()
    trades = [
        {"contract_date": t.contract_date, "price": t.price, "floor": t.floor, "is_canceled": bool(t.is_canceled)}
        for t in rows
        if int(t.exclusive_area) == area_band
    ]

    neighbors = db.execute(
        select(Apartment.id, Apartment.name, ApartmentPrice.avg_price)
        .join(ApartmentPrice, ApartmentPrice.apartment_id == Apartment.id)
        .where(Apartment.gu == chosen.gu, Apartment.dong == chosen.dong, ApartmentPrice.area_band == area_band)
        .order_by(ApartmentPrice.avg_price, Apartment.id)
    ).all()
    return {
        "apartment_id": apartment_id,
        "area_band": area_band,
        "avg_price": price.avg_price,
        "period_start": price.period_start,
        "period_end": price.period_end,
        "trades": trades,
        "neighbors": [
            {"id": n.id, "name": n.name, "avg_price": n.avg_price, "is_self": n.id == apartment_id} for n in neighbors
        ],
    }
