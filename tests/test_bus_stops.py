"""버스정류장. A-28 GET /api/bus-stops"""
import pytest

from backend import models

AREA = {"south": 35.14, "west": 126.84, "north": 35.15, "east": 126.85}


@pytest.fixture
def stops(db):
    """영역 안 두 곳(길 건너편이라 이름이 같다), 영역 밖 한 곳"""
    db.add_all([
        models.BusStop(stop_id="KJB2002", name="전남고", latitude="35.1452000", longitude="126.8461000"),
        models.BusStop(stop_id="KJB2001", name="전남고", latitude="35.1450000", longitude="126.8460000"),
        models.BusStop(stop_id="KJB9000", name="문화전당역", latitude="35.1462450", longitude="126.9189595"),
    ])
    db.commit()


def test_stops_in_area_by_stop_id(client, stops):
    res = client.get("/api/bus-stops", params=AREA)
    assert res.status_code == 200
    assert res.json() == {
        "stops": [
            {"stop_id": "KJB2001", "name": "전남고", "latitude": 35.145, "longitude": 126.846},
            {"stop_id": "KJB2002", "name": "전남고", "latitude": 35.1452, "longitude": 126.8461},
        ]
    }


def test_no_login_needed_and_empty_area(anon_client, stops):
    res = anon_client.get("/api/bus-stops", params={"south": 35.0, "west": 126.0, "north": 35.01, "east": 126.01})
    assert res.status_code == 200
    assert res.json() == {"stops": []}


@pytest.mark.parametrize("area", [
    {**AREA, "south": 35.15, "north": 35.14},  # 남북이 뒤집힘
    {**AREA, "west": 126.85, "east": 126.84},  # 동서가 뒤집힘
    {**AREA, "south": 35.0, "north": 35.2},  # 세로가 0.1도를 넘음
    {**AREA, "west": 126.7, "east": 126.9},  # 가로가 0.1도를 넘음
])
def test_bad_area(client, stops, area):
    res = client.get("/api/bus-stops", params=area)
    assert res.status_code == 422
    assert res.json() == {"detail": "지도 영역을 다시 확인해 주세요.", "field": "bounds"}


def test_missing_value(client, stops):
    res = client.get("/api/bus-stops", params={"south": 35.14, "west": 126.84, "north": 35.15})
    assert res.status_code == 422
    assert res.json()["field"] == "east"
