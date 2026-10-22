// 광주 5개 구의 경계 (P-05 ⑪, FR-MAP-28, T-MAP-26). 2026-10-15 팀장 직무대행 박채은
//
// 자료 (data/build_boundaries.py가 만든다. 출처는 docs/guides/boundary_data.md)
//   data/boundaries.geojson       outline : 5개 구를 하나로 합친 바깥 경계 (덮개의 구멍으로만 쓴다)   gu : 구 경계 5개   hdong : 행정동 경계 (선으로만)
//   data/boundaries_bdong.geojson bdong   : 법정동 경계 (지역 선택에서 동을 골랐을 때 칠한다)
//   법정동은 크다(약 550KB). 처음 화면을 늦추지 않게, 경계를 그린 뒤에 뒤에서 한 번 받는다. 오기 전에 동을 고르면 구를 강조했다가 오면 바꾼다.
// 서비스의 동은 실거래가 자료의 법정동이다. 행정동은 이름이 달라서(농성동 ↔ 농성1동, 농성2동) 선으로만 보여 주고,
// 고른 동은 법정동 경계로 칠한다. 법정동 경계가 없는 동을 고르면 그 구만 강조한다.
//
// 지도 화면(map-view.js)이 쓰는 함수
//   mapBoundary.attach(map, { dongLevel })            지도를 만든 뒤 한 번. 자료를 한 번만 받아 도형을 한 번만 만든다
//     dongLevel : 이 확대 수준부터(더 넓게 보면) 동 표시가 나온다. 행정동 선은 이보다 가까이 볼 때만 그린다
//   선과 면에는 사건(click 등)을 달지 않는다. 사건을 단 도형은 누르기를 가져가서, 그 위에서 지도를 끌 수 없게 된다.
//   그래서 칠한 면 위에서도 지도를 끌고, 누르면 지도를 누른 것이 된다.
//   mapBoundary.select({ gu, dong } | null)            구·동을 골라 옮겼을 때만 그 지역을 강조한다. null이면 강조 없음
//     손으로 지도를 옮기며 볼 때는 강조 없이 경계 선만 보인다 (map-view.js가 null을 준다)
//   mapBoundary.contains(gu, dong, lat, lng)           그 점이 그 지역 경계 안인가. 자료가 없으면 null (부르는 쪽이 정한다)
//     동을 고른 뒤 지도를 끌어 그 동을 벗어났는지 볼 때 쓴다 (map-view.js의 centerInFocus)
//   mapBoundary.bdongReady()                           법정동 경계를 다 받았으면(또는 못 받았으면) 풀리는 Promise
//     새로 고쳐 동이 보관되어 있을 때, 법정동이 온 뒤에 그 동에 다시 맞추는 데 쓴다 (map-view.js의 startKakaoMap)
//   mapBoundary.boundsOf(gu, dong)                     그 지역 경계를 감싼 사각형 { south, west, north, east }. 자료가 없으면 null
//     지역을 고르면 지도가 그 지역 전체가 들어오게 확대 수준을 맞출 때 쓴다 (map-view.js의 regionFit)
//
// 확대 수준별로 그리는 것 (카카오맵: 숫자가 작을수록 가깝다. 이 지도는 1 ~ 9. 단계는 map-view.js의 DONG_MARKER_LEVEL, GU_MARKER_LEVEL)
//   1 ~ 4  (아파트 말풍선)  구 경계, 행정동 연회색 선. 동을 골랐으면 행정동 선 대신 그 동의 경계만
//   5 ~ 6  (동 표시)        구 경계.  행정동 선은 감춘다 (동 표시의 법정동 이름과 섞이지 않게)
//   7 ~ 9  (구 표시)        구 경계
//   고른 구·동의 강조는 확대 수준과 상관없이 select가 정한다
//   경계 밖은 늘 반투명하게 덮는다 (구멍 뚫린 다각형, 화면 설계서 9.3).
//   바깥 경계는 덮개와 같은 색의 불투명한 선으로 긋는다. 덮개가 경계를 살짝 덮는 느낌 (2026-10-20 팀장. 예전에는 긋지 않았다)
//
// 겹치는 순서: 지도 그림 < 경계 선과 면 < 말풍선·동 표시 < 아래 창과 지도 위 창
//   카카오맵은 선과 면(Polyline, Polygon)을 지도 그림 위의 한 층에 SVG로 그리고,
//   말풍선(CustomOverlay)은 그보다 위의 다른 층에 HTML로 그린다. 그래서 zIndex를 어떻게 주어도 선과 면은 말풍선 밑에 있다.
//   여기서 주는 zIndex는 선과 면끼리의 순서다 (덮개 < 칠한 면 < 행정동 선 < 구 선 < 고른 지역의 선).
//
// 색은 map.css의 .map-body에 있는 이름(--boundary-*)을 읽어 쓴다. 이 파일에 색 값을 적지 않는다.

const BOUNDARY_URL = '/data/boundaries.geojson';
const BOUNDARY_BDONG_URL = '/data/boundaries_bdong.geojson';

// 둘레를 넓게 두른 사각형. 경계 밖 덮개의 바깥쪽이다. 지도의 최대 축소(9)에서도 화면을 다 덮는다
const BOUNDARY_WORLD = { south: 33.0, west: 124.5, north: 37.5, east: 129.5 };

// 굵기(px)와 불투명도. 색은 CSS에서 읽는다
const BOUNDARY_STYLE = {
  mask: { fillOpacity: 0.16 },
  // 광주 바깥 테두리: 경계 밖 덮개를 지도 바탕에 얹은 색(map.css --boundary-outline)과 같게, 불투명하게. 덮개가 경계를 살짝 덮는 느낌 (2026-10-20 팀장)
  outline: { strokeWeight: 3, strokeOpacity: 1 },
  gu: { strokeWeight: 2, strokeOpacity: 0.45 }, // 남색 회색 #5b6b8c (map.css) 45% (2026-10-20 팀장)
  hdong: { strokeWeight: 1, strokeOpacity: 0.9 },
  pickedGu: { strokeWeight: 2.5, strokeOpacity: 0.9, fillOpacity: 0.04 },
  pickedDong: { strokeWeight: 2.5, strokeOpacity: 1, fillOpacity: 0.06 }, // 남색 (2026-10-19). 칠을 옅게 해 아래 이름과 길이 보이게
};
const BOUNDARY_Z = { mask: 1, fill: 2, hdong: 3, gu: 4, outline: 5, picked: 6 };

const mapBoundary = (() => {
  let map = null;
  let options = { dongLevel: 6 };
  let data = null; // { outline, gu: Map(gu → 도형), bdong: Map('구 동' → 도형) }
  let shapes = null; // 한 번 만든 카카오 도형들
  let wanted = null; // 강조할 지역. 자료가 오기 전에 select가 불리면 여기 두었다가 그린다
  let resolveBdong = null;
  let bdongLoading = true; // 법정동 경계를 받는 중인가
  const bdongPromise = new Promise((resolve) => { resolveBdong = resolve; }); // 법정동을 받았으면 true, 못 받았으면 false
  let shownLevelBand = null; // 행정동 선을 지금 그리고 있는가 (true/false). 바뀔 때만 setMap을 부른다

  // ───────── 자료 ─────────

  // GeoJSON의 [경도, 위도] → kakao LatLng.
  //   면(Polygon)은 카카오맵이 스스로 닫으므로 고리의 마지막 점(처음과 같은 점)을 넣지 않는다.
  //   선(Polyline)은 닫히지 않으므로 마지막 점까지 넣어 고리를 닫는다.
  const toLatLngs = (ring) => ring.map(([lng, lat]) => new kakao.maps.LatLng(lat, lng));
  const toPath = (ring) => toLatLngs(ring.slice(0, -1));
  const toLine = (ring) => toLatLngs(ring);

  // Polygon이든 MultiPolygon이든 다각형 목록으로. 다각형 하나는 고리 목록이다 ([바깥, 구멍, 구멍...])
  const polygonsOf = (geometry) => (geometry.type === 'Polygon' ? [geometry.coordinates] : geometry.coordinates);

  function readData(collection) {
    const result = { outline: null, gu: new Map(), hdong: [], bdong: new Map() };
    for (const { properties: p, geometry } of collection.features) {
      if (p.layer === 'outline') result.outline = geometry;
      else if (p.layer === 'gu') result.gu.set(p.gu, geometry);
      else if (p.layer === 'hdong') result.hdong.push(geometry);
      else if (p.layer === 'bdong') result.bdong.set(`${p.gu} ${p.dong}`, geometry);
    }
    return result;
  }

  // ───────── 도형 만들기 (한 번만) ─────────

  const color = (name) => getComputedStyle(document.body).getPropertyValue(name).trim();

  // 테두리만 있는 선. 면이 없어 그 안을 눌러도 지도를 누른 것이 된다
  function lines(geometry, style, colorName, zIndex) {
    const result = [];
    for (const polygon of polygonsOf(geometry)) {
      for (const ring of polygon) {
        result.push(new kakao.maps.Polyline({
          path: toLine(ring), strokeColor: color(colorName), strokeStyle: 'solid', zIndex, ...style,
        }));
      }
    }
    return result;
  }

  // 구 사이의 선만 (2026-10-20 팀장: 광주 바깥 테두리는 긋지 않는다).
  // 구 고리의 마디 중 바깥 경계(outline)에 있는 마디는 빼고, 이어진 나머지만 선으로 긋는다
  function innerLines(geometry, outline, style, colorName, zIndex) {
    const key = ([lng, lat]) => `${lng.toFixed(6)},${lat.toFixed(6)}`;
    const edge = new Set();
    for (const polygon of polygonsOf(outline)) {
      for (const ring of polygon) {
        for (let i = 0; i + 1 < ring.length; i += 1) {
          const a = key(ring[i]);
          const b = key(ring[i + 1]);
          edge.add(`${a}|${b}`);
          edge.add(`${b}|${a}`);
        }
      }
    }
    const result = [];
    const flush = (run) => {
      if (run.length < 2) return;
      result.push(new kakao.maps.Polyline({
        path: run.map(([lng, lat]) => new kakao.maps.LatLng(lat, lng)), strokeColor: color(colorName), strokeStyle: 'solid', zIndex, ...style,
      }));
    };
    for (const polygon of polygonsOf(geometry)) {
      for (const ring of polygon) {
        let run = [];
        for (let i = 0; i + 1 < ring.length; i += 1) {
          if (edge.has(`${key(ring[i])}|${key(ring[i + 1])}`)) {
            flush(run);
            run = [];
            continue;
          }
          if (run.length === 0) run.push(ring[i]);
          run.push(ring[i + 1]);
        }
        flush(run);
      }
    }
    return result;
  }

  // 칠한 면. 사건을 달지 않는다 (위의 설명: 그 위에서도 지도를 끌 수 있게)
  function area(paths, style, colorName, zIndex) {
    return new kakao.maps.Polygon({
      path: paths, strokeWeight: 0, strokeOpacity: 0, fillColor: color(colorName), zIndex, ...style,
    });
  }

  // 경계 밖 덮개: 넓은 사각형에 5개 구의 바깥 경계로 구멍을 낸 다각형 (화면 설계서 9.3)
  function maskPaths(outline) {
    const { south, west, north, east } = BOUNDARY_WORLD;
    const world = [
      new kakao.maps.LatLng(north, west), new kakao.maps.LatLng(north, east),
      new kakao.maps.LatLng(south, east), new kakao.maps.LatLng(south, west),
    ];
    // 5개 구의 조각마다 바깥 고리가 구멍이 된다
    return [world, ...polygonsOf(outline).map((polygon) => toPath(polygon[0]))];
  }

  function buildShapes() {
    const pickedLine = (zIndex) => new kakao.maps.Polyline({
      path: [], strokeColor: color('--boundary-picked'), strokeStyle: 'solid', zIndex, ...BOUNDARY_STYLE.pickedDong,
    });
    shapes = {
      mask: area(maskPaths(data.outline), BOUNDARY_STYLE.mask, '--boundary-mask', BOUNDARY_Z.mask),
      outline: lines(data.outline, BOUNDARY_STYLE.outline, '--boundary-outline', BOUNDARY_Z.outline),
      gu: [...data.gu.values()].flatMap((geometry) => innerLines(geometry, data.outline, BOUNDARY_STYLE.gu, '--boundary-gu', BOUNDARY_Z.gu)),
      hdong: data.hdong.flatMap((geometry) => lines(geometry, BOUNDARY_STYLE.hdong, '--boundary-dong', BOUNDARY_Z.hdong)),
      // 고른 지역: 조각마다 면 하나, 고리마다 선 하나. 고를 때마다 새로 만들지 않고 모양만 바꾼다 (모자랄 때만 만든다)
      pickedFills: [],
      pickedLines: [],
      pickedLine,
      pickedFill: (paths) => area(paths, BOUNDARY_STYLE.pickedDong, '--boundary-picked', BOUNDARY_Z.fill),
    };
    shapes.mask.setMap(map);
    shapes.outline.forEach((shape) => shape.setMap(map));
    shapes.gu.forEach((shape) => shape.setMap(map));
  }

  // ───────── 확대 수준에 따라 ─────────

  // 행정동 선은 말풍선이 보이는 수준(동 표시가 나오기 전)에서만 그린다. 경계를 넘을 때만 setMap을 부른다
  // 동을 골랐으면 그 동의 경계만 보이게 다른 동의 선은 감춘다 (2026-10-15 결정)
  function applyLevel() {
    if (!shapes) return;
    const show = map.getLevel() < options.dongLevel && !dongPicked();
    if (show === shownLevelBand) return;
    shownLevelBand = show;
    shapes.hdong.forEach((shape) => shape.setMap(show ? map : null));
  }

  // ───────── 고른 지역 강조 ─────────

  // 고른 지역의 면을 조각 수만큼 둔다. 조각 하나는 [바깥 고리, 구멍...]이다. 남는 면은 지도에서 뺀다
  function setPickedFills(geometry, fillOpacity) {
    const parts = geometry ? polygonsOf(geometry) : [];
    while (shapes.pickedFills.length < parts.length) shapes.pickedFills.push(shapes.pickedFill(parts[shapes.pickedFills.length].map(toPath)));
    shapes.pickedFills.forEach((fill, index) => {
      if (index < parts.length) {
        fill.setPath(parts[index].map(toPath));
        fill.setOptions({ fillOpacity });
        fill.setMap(map);
      } else {
        fill.setMap(null);
      }
    });
  }

  // 고른 지역의 선을 필요한 만큼만 둔다. 모자라면 만들고, 남으면 지도에서 뺀다 (지운 뒤 다시 쓴다)
  function setPickedLines(geometry) {
    const rings = geometry ? polygonsOf(geometry).flat() : [];
    while (shapes.pickedLines.length < rings.length) shapes.pickedLines.push(shapes.pickedLine(BOUNDARY_Z.picked));
    shapes.pickedLines.forEach((line, index) => {
      if (index < rings.length) {
        line.setPath(toLine(rings[index]));
        line.setMap(map);
      } else {
        line.setMap(null);
      }
    });
  }

  function draw() {
    if (!shapes) return;
    const region = wanted;
    const dongShape = region && region.dong ? data.bdong.get(`${region.gu} ${region.dong}`) : null;
    const guShape = region ? data.gu.get(region.gu) : null;
    // 동을 골랐는데 법정동 경계가 없으면 그 구를 강조한다
    const shape = dongShape || guShape || null;
    const style = dongShape ? BOUNDARY_STYLE.pickedDong : BOUNDARY_STYLE.pickedGu;

    setPickedFills(shape, style.fillOpacity);
    setPickedLines(shape);
    shapes.pickedLines.forEach((line) => line.setOptions({ strokeWeight: style.strokeWeight, strokeOpacity: style.strokeOpacity }));
    applyLevel(); // 동을 고르거나 풀면 행정동 선을 감추거나 다시 보인다
  }

  // 법정동 경계가 있는 동을 골랐는가
  // 법정동을 아직 받는 중이면(bdongLoading) 동을 고른 것으로 본다. 받기 전에 동을 고르면 행정동 선 전체가 잠깐 보였다가
  // 법정동이 오면 사라졌다 (2026-10-20). 받지 못했으면 예전처럼 구를 강조하고 행정동 선을 보인다
  function dongPicked() {
    if (!wanted || !wanted.dong || !data) return false;
    return bdongLoading || data.bdong.has(`${wanted.gu} ${wanted.dong}`);
  }

  // 도형을 감싼 사각형. 한 번 계산하면 기억해 둔다
  const boxes = new Map();
  function boxOf(key, geometry) {
    if (!boxes.has(key)) {
      const box = { south: Infinity, west: Infinity, north: -Infinity, east: -Infinity };
      for (const polygon of polygonsOf(geometry)) {
        for (const [lng, lat] of polygon[0]) { // 바깥 고리만 보면 된다
          box.south = Math.min(box.south, lat);
          box.north = Math.max(box.north, lat);
          box.west = Math.min(box.west, lng);
          box.east = Math.max(box.east, lng);
        }
      }
      boxes.set(key, box);
    }
    return boxes.get(key);
  }

  // 점이 고리 안인가 (반직선과 만나는 변의 수가 홀수면 안)
  function inRing(ring, lat, lng) {
    let inside = false;
    for (let i = 0, j = ring.length - 1; i < ring.length; j = i, i += 1) {
      const [xi, yi] = ring[i];
      const [xj, yj] = ring[j];
      if ((yi > lat) !== (yj > lat) && lng < ((xj - xi) * (lat - yi)) / (yj - yi) + xi) inside = !inside;
    }
    return inside;
  }

  // 같은 지역이면 다시 그리지 않는다
  const sameRegion = (a, b) => (a === null && b === null) || (a !== null && b !== null && a.gu === b.gu && a.dong === b.dong);

  return {
    async attach(kakaoMap, { dongLevel } = {}) {
      if (map) return; // 한 번만
      map = kakaoMap;
      options = { dongLevel: dongLevel ?? options.dongLevel };
      try {
        data = readData(await api.get(BOUNDARY_URL));
      } catch (error) {
        // 경계가 없어도 지도는 그대로 쓸 수 있다. 자료를 만들지 않았으면 data/build_boundaries.py를 돌린다
        console.warn('[boundary] 경계 자료를 받지 못했습니다.', error.status ?? '');
        resolveBdong(false);
        return;
      }
      if (!data.outline || data.gu.size === 0) {
        console.warn('[boundary] 경계 자료가 비어 있습니다.');
        resolveBdong(false);
        return;
      }
      buildShapes();
      kakao.maps.event.addListener(map, 'zoom_changed', applyLevel);
      applyLevel();
      draw();

      // 법정동은 뒤에서 한 번만 받는다. 못 받으면 동을 골라도 구를 강조한다 (지도는 그대로 쓴다)
      try {
        data.bdong = readData(await api.get(BOUNDARY_BDONG_URL)).bdong;
        draw();
        bdongLoading = false;
        resolveBdong(true);
      } catch (error) {
        console.warn('[boundary] 법정동 경계를 받지 못했습니다. 동을 고르면 구를 강조합니다.', error.status ?? '');
        bdongLoading = false;
        draw(); // 행정동 선을 다시 보인다
        resolveBdong(false);
      }
    },

    bdongReady() {
      return bdongPromise;
    },

    // 동이면 법정동 경계, 구면 구 경계를 감싼 사각형. 법정동이 아직 안 왔거나 없으면 null (부르는 쪽이 예전 방식으로 옮긴다)
    boundsOf(gu, dong) {
      if (!data) return null;
      const geometry = dong ? data.bdong.get(`${gu} ${dong}`) : data.gu.get(gu);
      return geometry ? boxOf(`${gu} ${dong || ''}`, geometry) : null;
    },

    // 점이 그 지역 경계 안인가. 바깥 고리 안이고 구멍 안이 아니면 안이다. 경계를 모르면 null
    contains(gu, dong, lat, lng) {
      if (!data) return null;
      const geometry = dong ? data.bdong.get(`${gu} ${dong}`) : data.gu.get(gu);
      if (!geometry) return null;
      const box = boxOf(`${gu} ${dong || ''}`, geometry);
      if (lat < box.south || lat > box.north || lng < box.west || lng > box.east) return false;
      return polygonsOf(geometry).some(([outer, ...holes]) => inRing(outer, lat, lng) && !holes.some((hole) => inRing(hole, lat, lng)));
    },

    select(region) {
      const next = region && region.gu ? { gu: region.gu, dong: region.dong || null } : null;
      if (sameRegion(wanted, next)) return;
      wanted = next;
      draw();
    },
  };
})();
