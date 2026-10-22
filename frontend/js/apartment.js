// 아래 창의 아파트 (P-06 ⑥ 30%, ⑦ 80%). 담당: 안세환
//
// 30%에 보이는 것 (guide_sehwan 4장, 와이어프레임 P-06 ⑥)
//   아파트명, 구분 배지, 이전·다음·닫기, 면적 고르기와 ㎡/평 전환,
//   "최근 1년 실거래 평균 3억 원", "5년 뒤 기준 여유 2,000만 원"
//   대출 없이 계산이면 기준 줄에 "· 대출 없이"를 붙인다 (와이어프레임 "P-06 아파트 30% (대출 없이)").
// 80% 이상에는 탭(아파트 정보, 시나리오)이 보인다.
//   아파트 정보 (P-06 ⑦): 아파트 한 곳 API(A-06, GET /api/apartments/{id})로 채운다.
//     창이 80% 이상이고 아파트 정보 탭이 보일 때 처음 한 번 부른다. 받은 것은 아파트마다 기억해 두고 다시 부르지 않는다.
//     여덟 줄: 지번 주소("농성동 654-34". 복사하면 "전남광주통합특별시 서구 농성동 654-34"), 도로명 주소, 준공 연도, 면적, 실거래 평균가, 최근 1년 거래(집계 기간), 세대수, 가격 범위.
//     순서는 목업 A9(4010:1111), C6(4022:1188)을 따른다. 1차 여섯 줄 뒤에 2차 두 줄을 붙인다.
//     세대수는 "1,234세대 (2026년 8월 기준)", 가격 범위는 "2억 7,000만 ~ 3억 3,000만 원" (FR-APT-15, 16).
//     값을 모르는 줄(도로명 주소, 준공 연도, 세대수가 비어 있음)은 그리지 않는다.
//   로드뷰 (3차, FR-MAP-09, 10, T-MAP-11. 목업 C6 4022:1205, C6b 4022:1356):
//     아파트 정보 탭을 전체로 올렸을 때만, 창 맨 위(손잡이 위)에 둔다. 그때 처음 불러온다.
//     창 폭 전체를 채우고 가로:세로는 황금비 1.618 : 1이다 (시안 ②, sheet.css).
//     그 아파트 둘레 100m 안의 가장 가까운 로드뷰를 카카오맵으로 찾는다 (서버 API 없음. API 명세서 3.5).
//     로드뷰가 없거나, 좌표가 없거나, 카카오맵을 쓸 수 없으면 같은 자리에 "이 위치에는 로드뷰가 없습니다" 문장을 둔다.
//     자리(#apt-roadview)는 이 파일이 만들어 창(#sheet)의 손잡이 앞에 넣는다.
//   비슷한 아파트 (3차, FR-APT-17, T-APT-11. 목업 C6 4022:1301): 정보 줄 아래에 김목산의 similar.js가 그린다.
//     이 파일은 자리(#apt-similar)를 만들고 similarView.load를 부르기만 한다. 아파트·면적·조건이 그대로면 다시 부르지 않는다.
//     similar.js가 있으면 정보 줄 위에 "기본 정보" 제목을 붙인다 (C6. 묶음이 둘이 되므로).
//     카드를 누르면 그 아파트로 넘어간다. map-view.js가 넘겨준 handlers.onPickSimilar를 부른다
//     (없으면 지금 지도에 있는 아파트만 ‹ ›와 같이 넘긴다).
//     similar.js를 불러오지 않았으면 아무것도 하지 않는다.
//   주변 시설 (3차, FR-MAP-23, T-MAP-23. 와이어프레임 C6): 기본 정보와 비슷한 아파트 사이에 둔다.
//     지하철역, 학교, 대형마트, 편의점, 병원 다섯 줄(앞에 작은 그림). 학교 줄의 ⌄로 초·중·고·대학교를 펼친다.
//     줄마다 반경 1km(직선) 안에서 가장 가까운 곳의 이름과, 걸어가는 거리 · 시간의 어림값 (aptWalk, 2026-10-19 세환 결정).
//     지하철역은 가장 가까운 출구까지의 거리 ("김대중컨벤션센터역 광주1호선" / "[5]번 출구 약 430m · 도보 약 7분"),
//     나머지는 "전남고등학교 약 170m · 도보 약 3분". 걷는 거리는 A-06의 직선거리에 1.3을 곱한 어림값이다 (길찾기 API는 쓰지 않는다).
//     찾은 줄을 누르면 지도에서 보여 준다: map-view.js의 showFacilityOnMap(kind, 시설)을 불러 창을 30%로 내리고
//     고른 아파트에서 그 시설까지 점선을 잇는다.
//     1km 안에 없으면 "근처에 없음". 대학교만 5km 안. 병원은 동물병원을 뺀다. 수는 적지 않는다 (2026-10-19 세환 결정).
//     값은 A-06의 facilities다. data/load_facilities.py가 카카오 장소 검색으로 미리 받아 DB에 넣은 것이라 화면은 카카오를 부르지 않는다
//     (NFR-08, 2026-10-19 팀장 결정). 맨 아래에 받은 날을 적는다. 받은 값이 없거나 좌표가 없으면 묶음을 두지 않는다.
//   좌표가 없는 아파트 (P-06 ⑱, 목업 4009:492): 이름과 배지 옆에 "위치 없음"을 붙이고,
//     아파트 정보 탭의 맨 위에 점선 안내를 둔다. 목록에서 열었을 때만 생긴다 (지도에는 표시가 없다).
//   시나리오:    박채은의 scenario.js가 #scenario-panel에 그린다.
//
// 30%의 값은 모두 A-05 응답에 있다. 30%에서는 서버를 다시 부르지 않는다.
// 계산하지 않는다. 배지의 구분과 금액은 서버가 준 값이다 (NFR-13). 글자는 textContent로 넣는다.
// 부족자금(shortage)이 0보다 크면 "부족", 아니면 그 절댓값이 "여유"다 (API 명세서 A-05, list.js와 같은 규칙).
//
// 지도와 이어지는 일은 map-view.js가 init에 넘긴 함수로 한다.
//   aptPanel.init({
//     order(current)     ‹ › 로 넘길 아파트들. 지금 지도에 보이는 아파트를 목록의 순서로 (FR-MAP-16)
//     basis()            "5년 뒤 기준", "지금 기준 · 대출 없이" 같은 기준 줄
//     onMove(apartment)  ‹ › 로 다른 아파트로 넘어감
//     onBackToList()     "← 치평동 목록"
//     onClose()          닫기
//     onUnitChange()     ㎡/평을 바꿈. 지도의 말풍선과 단위 버튼도 함께 바뀐다
//   });
//   aptPanel.show(apartment, areaIndex, { listPlace: '치평동' })   listPlace가 있으면 목록에서 연 것이다

const APT_CATEGORY_NAMES = { now: '지금 가능', within: '기간 내 가능', lack: '자금 부족' };
// 불러오지 못했을 때. 지도 화면의 문장과 같다 (와이어프레임 P-04 ⑩). 아래에 "다시 시도"를 둔다 (P-05 ⑰과 같은 모양)
const APT_INFO_FAIL = '아파트를 불러오지 못했습니다. 잠시 후 다시 시도해 주세요.';
// 좌표가 없는 아파트 (와이어프레임 P-06 ⑱의 문장 그대로)
const APT_NO_COORD = '위치 없음';
const APT_NO_COORD_NOTICE = '이 아파트는 위치 정보가 없어 지도에 표시하지 못했습니다. 지도는 그대로 두었습니다.';
// 로드뷰 (목업 C6, C6b)
const APT_ROADVIEW_RADIUS = 100; // 아파트 좌표에서 이 거리(m) 안의 가장 가까운 로드뷰를 쓴다
// 로드뷰를 바꿀 때 (2026-10-20 팀장: 아파트를 넘길 때마다 사진이 빠르게 바뀌는 모습이 보기 싫다)
//   - 동을 받으면 그 동 아파트들의 로드뷰 지점(panoId)을 미리 찾아 둔다 (prefetchRoadviews). 넘길 때 찾느라 기다리지 않는다.
//     카카오 로드뷰는 한 번에 한 장만 띄울 수 있고 사진을 미리 받아 두는 기능이 없어, 지점까지만 미리 찾는다.
//   - 로드뷰 화면을 두 개 두고 번갈아 쓴다 (크로스페이드, 2026-10-20 팀장 결정). 새 사진은 뒤의 화면에 띄워 아파트 쪽으로 돌린 뒤,
//     앞 사진 위로 서서히 나타나게 한다 (sheet.css .apt-roadview__view--on). 사진이 바뀌는 모습이나 빈 화면이 보이지 않는다
const APT_ROADVIEW_PREFETCH_MAX = 80; // 한 번에 미리 찾는 아파트 수의 상한
const APT_ROADVIEW_PREFETCH_AT_ONCE = 4; // 동시에 찾는 수
const APT_ROADVIEW_SETTLE_MS = 200; // 새 사진의 방향 변경 신호가 이만큼 더 오지 않으면(움직임이 멈추면) 나타나게 한다
const APT_ROADVIEW_REVEAL_MAX_MS = 1500; // 신호가 안 와도 이만큼 지나면 나타나게 한다
const APT_ROADVIEW_FADE_MS = 400; // 새 사진이 앞 사진 위로 나타나는 시간 (sheet.css의 transition과 같다)
const APT_ROADVIEW_TILT = -20; // 처음 볼 때 위아래 각도. 카카오 로드뷰는 음수가 위다 (-90 ~ 90)
const APT_ROADVIEW_ZOOM = -3; // 처음 볼 때 확대. -3이 가장 넓게 보인다 (-3 ~ 3)
const APT_NO_ROADVIEW = '이 위치에는 로드뷰가 없습니다'; // 2026-10-20 팀장: "기본 이미지"와 집 그림은 빼고 문장만
const APT_INFO_TITLE = '기본 정보'; // 목업 C6 (4022:1279). 비슷한 아파트가 아래에 붙을 때만 둔다

// 주변 시설 (FR-MAP-23, 와이어프레임 C6). kind는 A-06 facilities의 kind
const APT_NEAR_TITLE = '주변 시설';
// icon: 줄 앞의 작은 그림 (24 × 24 SVG path. 직접 그린 단순한 모양)
// code: 카카오 장소 분류. 지도에 띄운 시설 아이콘의 색 이름(map.css .facility--sw8 등)에 쓴다
const APT_NEAR_KINDS = [
  { kind: 'subway', code: 'SW8', label: '지하철역', icon: 'M8 2h8a4 4 0 0 1 4 4v9a3 3 0 0 1-3 3l2 3h-2.4l-2-3H9.4l-2 3H5l2-3a3 3 0 0 1-3-3V6a4 4 0 0 1 4-4zM6 6v4h12V6H6zm2 7.5a1.5 1.5 0 1 0 0 3 1.5 1.5 0 0 0 0-3zm8 0a1.5 1.5 0 1 0 0 3 1.5 1.5 0 0 0 0-3z' },
  { kind: 'school', code: 'SC4', label: '학교', icon: 'M12 3l10 5-10 5L2 8l10-5zM6 11.2l6 3 6-3V16c0 1.9-2.7 4-6 4s-6-2.1-6-4v-4.8zM20 9.5h1.5V15H20V9.5z' },
  { kind: 'mart', code: 'MT1', label: '대형마트', icon: 'M2 3h3.2l.7 3H21l-2 8.5a2 2 0 0 1-2 1.5H9a2 2 0 0 1-2-1.5L4.2 5H2V3zm7 15a1.75 1.75 0 1 0 0 3.5A1.75 1.75 0 0 0 9 18zm8 0a1.75 1.75 0 1 0 0 3.5 1.75 1.75 0 0 0 0-3.5z' },
  { kind: 'convenience', code: 'CS2', label: '편의점', icon: 'M4 3h16l1.5 5a3 3 0 0 1-2.5 3.2V20a1 1 0 0 1-1 1H6a1 1 0 0 1-1-1v-8.8A3 3 0 0 1 2.5 8L4 3zm3 10v6h4v-4h2v4h4v-6H7zm-1.2-8L4.6 8.4a1 1 0 0 0 1 1.1h12.8a1 1 0 0 0 1-1.1L18.2 5H5.8z' },
  { kind: 'hospital', code: 'HP8', label: '병원', icon: 'M6 3h12a3 3 0 0 1 3 3v12a3 3 0 0 1-3 3H6a3 3 0 0 1-3-3V6a3 3 0 0 1 3-3zm4.5 4v3.5H7v3h3.5V17h3v-3.5H17v-3h-3.5V7h-3z' },
];
// 근처(1km)에 지하철역이 없으면 지하철역 줄을 가장 가까운 버스정류장으로 바꿔 보인다 (2026-10-20 팀장 결정. A-06의 bus 줄)
const APT_NEAR_BUS = {
  kind: 'bus',
  label: '버스정류장',
  icon: 'M7 3h10a3 3 0 0 1 3 3v11a2 2 0 0 1-1.5 1.94v1.56a1 1 0 0 1-1 1h-1a1 1 0 0 1-1-1V19h-7v1.5a1 1 0 0 1-1 1h-1a1 1 0 0 1-1-1v-1.56A2 2 0 0 1 4 17V6a3 3 0 0 1 3-3zM6.5 6.5v5h11v-5h-11zM8 14.2a1.3 1.3 0 1 0 0 2.6 1.3 1.3 0 0 0 0-2.6zm8 0a1.3 1.3 0 1 0 0 2.6 1.3 1.3 0 0 0 0-2.6z',
};
// 학교 줄의 ⌄를 누르면 펼치는 종류별 학교
const APT_NEAR_SCHOOLS = [
  { kind: 'elementary', label: '초등학교' },
  { kind: 'middle', label: '중학교' },
  { kind: 'high', label: '고등학교' },
  { kind: 'university', label: '대학교' },
];
const APT_AREA_SLIDE_MS = 380; // 면적 칸이 고른 면적으로 미끄러지는 시간 (slideArea)
const APT_NEAR_MORE = '학교 종류별로 보기';
const APT_NEAR_LESS = '학교 종류별 접기';
const APT_NEAR_NONE = '근처에 없음'; // 반경 안에 없을 때
// 맨 아래 출처. 뒤에 받은 날을 붙인다: "카카오 장소 정보 · 2026년 10월 19일 기준".
// 미리 받아 둔 자료라 받은 날을 적는다. "직선거리로 어림" 안내는 뺐다 (2026-10-20 팀장 결정. 세환 의견: '어림'으로 끝나는 말이 좋지 않다)
const APT_NEAR_SOURCE = '카카오 장소 정보';
const APT_NEAR_ON_MAP = '지도에서 보기'; // 찾은 줄의 단추 이름 끝에 붙인다 (화면 읽기)
// 찾은 줄 끝의 작은 위치 표시. 누르면 지도에서 보여 준다는 뜻
const APT_NEAR_PIN = 'M12 2a7 7 0 0 0-7 7c0 5.2 7 13 7 13s7-7.8 7-13a7 7 0 0 0-7-7zm0 9.5A2.5 2.5 0 1 1 12 6.5a2.5 2.5 0 0 1 0 5z';

// 주변 시설 줄 앞의 작은 그림. 글자와 같은 색을 쓰고 화면 읽기에서는 건너뛴다
function aptNearIcon(path) {
  const NS = 'http://www.w3.org/2000/svg';
  const svg = document.createElementNS(NS, 'svg');
  svg.setAttribute('class', 'apt-near__icon');
  svg.setAttribute('viewBox', '0 0 24 24');
  svg.setAttribute('aria-hidden', 'true');
  const shape = document.createElementNS(NS, 'path');
  shape.setAttribute('d', path);
  shape.setAttribute('fill-rule', 'evenodd');
  svg.append(shape);
  return svg;
}

// 걸어가는 거리와 시간의 어림값 (2026-10-19 세환 결정). 길찾기 API 없이 직선거리로 어림한다.
//   길은 직선보다 돌아가므로 직선거리에 1.3을 곱하고 10m 단위로 맞춘다. 걷는 빠르기는 시속 4km(1분에 약 67m)로 본다.
//   실제와 다를 수 있다. 지도의 시설 이름표(map-view.js)도 같은 값을 쓴다.
const APT_WALK_DETOUR = 1.3;
const APT_WALK_M_PER_MIN = 67;

// 직선거리(m) → { distance: "약 670m", time: "도보 약 10분" }. 1시간이 넘으면 "도보 약 1시간 28분"
function aptWalk(meters) {
  const walk = Math.max(10, Math.round((Number(meters) * APT_WALK_DETOUR) / 10) * 10);
  const minutes = Math.max(1, Math.ceil(walk / APT_WALK_M_PER_MIN));
  const rest = minutes % 60;
  const time = minutes < 60 ? `${minutes}분` : `${Math.floor(minutes / 60)}시간${rest ? ` ${rest}분` : ''}`;
  return { distance: `약 ${aptNearDistance(walk)}`, time: `도보 약 ${time}` };
}

// 직선거리(m) → "약 670m · 도보 약 10분"
function aptWalkText(meters) {
  const { distance, time } = aptWalk(meters);
  return `${distance} · ${time}`;
}

// 거리(m)를 "383m", 1km부터는 "4.5km"로
function aptNearDistance(meters) {
  const value = Number(meters);
  return value < 1000 ? `${format.comma(value)}m` : `${(Math.round(value / 100) / 10).toLocaleString('ko-KR')}km`;
}

// "기본 정보" 제목 (목업 C6)
const aptInfoTitle = () => {
  const title = document.createElement('h3');
  title.className = 'apt-info__title';
  title.textContent = APT_INFO_TITLE;
  return title;
};

const aptHasCoord = (apartment) =>
  apartment.latitude !== null && apartment.latitude !== undefined &&
  apartment.longitude !== null && apartment.longitude !== undefined;

const aptPanel = {
  apartment: null,
  scenarioKey: null, // 시나리오 탭에 마지막으로 그린 아파트와 면적 ("번호:면적대")
  areaIndex: 0, // 고른 면적. areas는 평균가가 낮은 순이고 첫째가 처음에 골라져 있다 (FR-APT-05)
  listPlace: null,
  handlers: {},
  details: new Map(), // 아파트 번호 → A-06 응답. 받은 것만 둔다
  panoIds: new Map(), // 아파트 번호 → 가장 가까운 로드뷰 지점(panoId). 없으면 null. 찾은 것만 둔다
  roadviews: [null, null], // 번갈아 쓰는 로드뷰 두 개 (kakao.maps.Roadview). 만든 것만
  roadviewFront: 0, // 지금 보이는 쪽 (0 또는 1). aptPanel.roadview는 이쪽이다
  roadviewTimers: [],
  areaOnly: false, // 지금 다시 그리는 것이 면적 칩을 눌러서인가 (render 동안만 true)
  similarTimer: null, // 면적 칸이 다 미끄러진 뒤 비슷한 아파트를 받는 타이머
  loading: new Set(), // 받는 중인 아파트 번호
  failed: new Set(), // 받지 못한 아파트 번호 ("다시 시도"를 누르면 지운다)
  roadview: null, // 카카오 로드뷰 (처음 보일 때 한 번 만든다)
  roadviewFor: null, // 로드뷰 자리에 마지막으로 그린 아파트 번호
  similarKey: null, // 비슷한 아파트를 마지막으로 부른 것 (아파트 번호, 면적대, 조건)

  init(handlers) {
    aptPanel.handlers = handlers;

    document.getElementById('apt-prev').addEventListener('click', () => aptPanel.move(-1));
    document.getElementById('apt-next').addEventListener('click', () => aptPanel.move(1));
    document.getElementById('apt-close').addEventListener('click', () => handlers.onClose());
    document.getElementById('apt-back').addEventListener('click', () => handlers.onBackToList());
    // 공유 아이콘 (FR-APT-18, 김목산의 share.js). 닫기 ✕ 앞에 두어 30% · 80% · 전체 어디서나 보인다
    if (typeof shareView !== 'undefined') {
      document.getElementById('apt-close').before(shareView.shareButton(() => {
        const { apartment } = aptPanel;
        const area = apartment.areas[aptPanel.areaIndex];
        return { id: apartment.id, name: apartment.name, area_band: area.area_band,
          supply_area: area.supply_area, exclusive_area: area.exclusive_area };
      }));
    }
    // 찜 하트 (2026-10-21, 박채은의 scenario.js). 공유 아이콘 앞에 둔다. ♡ 누르면 찜, ♥ 다시 누르면 찜 해제
    if (typeof scenarioView !== 'undefined') {
      const share = document.getElementById('apt-close').previousElementSibling;
      const before = share && share.classList.contains('share-action') ? share : document.getElementById('apt-close');
      before.before(scenarioView.heartButton(() => {
        const { apartment } = aptPanel;
        if (!apartment) return null;
        return { conditions: guard.conditions(), apartment_id: apartment.id, area_band: apartment.areas[aptPanel.areaIndex].area_band };
      }));
    }

    document.querySelectorAll('.apt__unit-option').forEach((button) => {
      button.addEventListener('click', () => {
        if (button.dataset.unit === aptPanel.unit()) return;
        store.set('map', { area_unit: button.dataset.unit });
        handlers.onUnitChange();
        aptPanel.render();
      });
    });

    document.querySelectorAll('.apt__tab').forEach((tab) => {
      tab.addEventListener('click', () => {
        aptPanel.selectTab(tab.id);
        aptPanel.renderInfo();
        aptPanel.renderRoadview();
      });
    });

    // 창이 80% 이상으로 커지면 아파트 정보 탭이 보인다. 그때 처음 부른다. 전체가 되면 로드뷰를 부른다.
    sheet.onChange(() => {
      aptPanel.renderInfo();
      aptPanel.renderRoadview();
    });
  },

  unit: () => (store.get('map').area_unit === 'pyeong' ? 'pyeong' : 'm2'),

  // 아파트를 보여 준다. 면적은 넘겨받은 것(목록 카드에서 보던 면적)을, 없으면 첫째를 고른다.
  show(apartment, areaIndex = 0, { listPlace = null } = {}) {
    aptPanel.apartment = apartment;
    aptPanel.areaIndex = areaIndex < apartment.areas.length ? areaIndex : 0;
    aptPanel.listPlace = listPlace;
    aptPanel.selectTab('apt-tab-info');
    aptPanel.render();
    aptPanel.scrollTop(); // 다른 아파트(또는 다시 연 아파트)는 늘 맨 위의 기본 상태에서 시작한다 (2026-10-19)
  },

  // 아파트 창의 내용을 맨 위로. 앞 아파트에서 내려 둔 자리가 다음 아파트에 남지 않게 한다
  // 창이 숨겨져 있거나 높이가 없으면(30%) 스크롤이 먹지 않는다. 그때는 sheet가 보이게 된 때 한다
  scrollTop() {
    sheet.scrollToTop(document.querySelector('.apt__panels'));
  },

  // ‹ › : 지도에 보이는 아파트를 목록의 순서로 넘긴다. 처음과 끝에서는 그 방향 버튼을 끈다.
  move(step) {
    const order = aptPanel.handlers.order(aptPanel.apartment);
    const next = order[order.indexOf(aptPanel.apartment) + step];
    if (!next) return;
    aptPanel.show(next, 0, { listPlace: aptPanel.listPlace });
    aptPanel.handlers.onMove(next);
  },

  selectTab(tabId) {
    // 탭을 바꾸면 그 탭의 맨 위부터 보여 준다 (아파트 정보 ↔ 시나리오)
    const changed = document.getElementById(tabId).getAttribute('aria-selected') !== 'true';
    if (changed) aptPanel.scrollTop();
    document.querySelectorAll('.apt__tab').forEach((tab) => {
      const selected = tab.id === tabId;
      tab.setAttribute('aria-selected', String(selected));
      document.getElementById(tab.getAttribute('aria-controls')).hidden = !selected;
    });
    aptPanel.renderScenario();
  },

  // ───────── 시나리오 탭 (P-06 ⑧) ─────────
  // 내용은 박채은의 scenario.js가 그린다. 여기서는 그릴 때를 알려 주기만 한다.
  //   시나리오 탭을 열 때, 그 탭이 열린 채 면적이나 아파트를 바꿀 때 부른다.
  //   같은 아파트의 같은 면적이면 다시 부르지 않는다 (탭을 오가도 "다시 계산"한 결과가 남는다).
  //   scenario.js가 없으면 아무것도 하지 않는다.
  renderScenario() {
    const { apartment, areaIndex } = aptPanel;
    if (!apartment || typeof scenarioView === 'undefined') return;
    if (document.getElementById('apt-tab-scenario').getAttribute('aria-selected') !== 'true') return;
    const area = apartment.areas[areaIndex];
    const key = `${apartment.id}:${area.area_band}`;
    if (aptPanel.scenarioKey === key) return;
    aptPanel.scenarioKey = key;
    scenarioView.render(document.getElementById('scenario-panel'), { apartment, area, conditions: guard.conditions() });
  },

  render() {
    const { apartment, areaIndex, listPlace, handlers } = aptPanel;
    if (!apartment) return;
    const area = apartment.areas[areaIndex];
    const unit = aptPanel.unit();

    // 이름과 배지는 늘 둘째 줄 (2026-10-19). 첫 줄은 "← ○○ 목록"(목록에서 열었을 때만)과 오른쪽의 공유 · ✕.
    // 이름이 ✕와 한 줄에 있으면 길 때 잘려서, 둘째 줄에서 줄을 바꿔 다 보여 준다. 배지는 이름 오른쪽
    const title = document.getElementById('apt-title');
    const back = document.getElementById('apt-back');
    const titleRow = document.getElementById('apt-title-row');
    back.hidden = !listPlace;
    titleRow.hidden = false;
    if (listPlace) back.textContent = `← ${listPlace} 목록`;
    if (title.parentElement !== titleRow) titleRow.append(title);
    format.keepWords(document.getElementById('apt-name'), apartment.name); // 띄어쓰기에서만 줄바꿈
    const badge = document.getElementById('apt-badge');
    badge.className = `badge badge--${area.category}`; // 고른 면적의 구분
    badge.textContent = APT_CATEGORY_NAMES[area.category];
    if (typeof scenarioView !== 'undefined') scenarioView.refreshSave(); // 찜 하트를 이 아파트 · 면적으로 (2026-10-21)
    aptPanel.renderNoCoordTag();

    // 이전·다음
    const order = handlers.order(apartment);
    const index = order.indexOf(apartment);
    document.getElementById('apt-prev').disabled = index <= 0;
    document.getElementById('apt-next').disabled = index < 0 || index >= order.length - 1;

    // 면적 칩. "111㎡ (전용 84㎡)", 공급면적을 모르면 "전용 49㎡"
    const areaList = document.getElementById('apt-areas');
    const sameApartment = areaList.dataset.apartment === String(apartment.id);
    // 같은 아파트에서 면적만 바꿨으면 칩을 다시 만들지 않고 고른 표시만 옮긴다. 다시 만들면 미끄러지던 칸이 끊겼다
    const sameChips = sameApartment && areaList.dataset.unit === unit && areaList.children.length === apartment.areas.length;
    areaList.dataset.apartment = String(apartment.id);
    areaList.dataset.unit = unit;
    aptPanel.watchAreaList(areaList);
    if (sameChips) {
      [...areaList.children].forEach((chip, i) => chip.setAttribute('aria-pressed', String(i === areaIndex)));
    } else areaList.replaceChildren(...apartment.areas.map((item, i) => {
      const chip = document.createElement('button');
      chip.type = 'button';
      chip.className = 'apt__area';
      chip.textContent = format.area(item.supply_area, item.exclusive_area, unit);
      chip.setAttribute('aria-pressed', String(i === areaIndex));
      chip.addEventListener('click', () => {
        if (areaList.dataset.dragged) return; // 잡아 끈 뒤 놓은 것은 누름이 아니다
        aptPanel.areaIndex = i;
        // 면적만 바꿨다: 같은 아파트라 로드뷰는 그대로 두고, 비슷한 아파트는 칸이 다 미끄러진 뒤에 받는다 (2026-10-20, 덜 끊기게)
        aptPanel.areaOnly = true;
        try {
          aptPanel.render();
        } finally {
          aptPanel.areaOnly = false;
        }
      });
      return chip;
    }));

    // 고른 면적이 칸 가운데에 오게 옆으로 미끄러진다 (2026-10-20 팀장 결정). 그래서 누르면 그 옆 면적도 보인다.
    // 같은 아파트에서 면적을 바꿨으면 미끄러지게, 새 아파트를 열었으면 맨 앞에서 바로 둔다
    // 창을 처음 열 때는 아직 숨겨져 있어 폭을 잴 수 없으므로 창이 보인 뒤(다음 차례)에 맞춘다
    if (!sameChips) areaList.scrollLeft = 0;
    setTimeout(() => aptPanel.centerArea(areaList, areaIndex, sameChips), 0);

    document.querySelectorAll('.apt__unit-option').forEach((button) => {
      button.setAttribute('aria-pressed', String(button.dataset.unit === unit));
    });

    // 평균가와 여유자금 (또는 부족자금)
    document.getElementById('apt-price').textContent = format.won(area.avg_price);
    document.getElementById('apt-basis').textContent = handlers.basis();
    const gap = document.getElementById('apt-gap');
    gap.className = `apt__value amount--${area.category}`;
    gap.textContent = area.shortage > 0 ? `부족 ${format.won(area.shortage)}` : `여유 ${format.won(-area.shortage)}`;

    aptPanel.renderInfo();
    aptPanel.renderScenario();
    if (!aptPanel.areaOnly) aptPanel.renderRoadview(); // 면적만 바꿨으면 로드뷰는 바뀔 것이 없다 (다시 맞추는 데 약 12ms)
  },

  // ───────── 좌표가 없는 아파트 (P-06 ⑱) ─────────

  // 이름과 배지 옆의 "위치 없음". 처음 쓸 때 한 번 만들어 이름 줄에 붙이고, 아파트마다 보이고 숨긴다.
  renderNoCoordTag() {
    let tag = document.getElementById('apt-no-coord');
    if (!tag) {
      tag = document.createElement('span');
      tag.id = 'apt-no-coord';
      tag.className = 'apt__tag';
      tag.textContent = APT_NO_COORD;
      document.getElementById('apt-title').append(tag);
    }
    tag.hidden = aptHasCoord(aptPanel.apartment);
  },

  // 아파트 정보 탭 맨 위의 점선 안내. 좌표가 있으면 null
  noCoordNotice() {
    if (aptHasCoord(aptPanel.apartment)) return null;
    const box = document.createElement('p');
    box.className = 'apt-info__notice';
    box.textContent = APT_NO_COORD_NOTICE;
    return box;
  },

  // ───────── 로드뷰 (3차, 목업 C6, C6b) ─────────

  // 로드뷰 자리가 보이는가. 전체 단계이고 아파트 창일 때 (C6). 탭은 가리지 않는다:
  // 아파트 정보 탭과 시나리오 탭 모두 전체가 되면 위에 로드뷰가 보인다 (2026-10-18, 예전에는 아파트 정보 탭만)
  roadviewVisible() {
    return (sheet.phase === 'opening' || sheet.phase === 'open') && sheet.mode === 'apartment' &&
      sheet.stage === 'full';
  },

  // 로드뷰 자리. 처음 쓸 때 한 번 만들어 창의 손잡이 앞(창 맨 위)에 넣는다.
  //   .apt-roadview__view   카카오 로드뷰가 그려지는 곳
  //   .apt-roadview__empty  로드뷰가 없을 때의 문장 "이 위치에는 로드뷰가 없습니다"
  roadviewBox() {
    let box = document.getElementById('apt-roadview');
    if (box) return box;
    box = document.createElement('div');
    box.id = 'apt-roadview';
    box.className = 'apt-roadview';
    box.hidden = true;
    // 번갈아 쓰는 로드뷰 자리 두 개 (크로스페이드)
    const views = [0, 1].map(() => {
      const view = document.createElement('div');
      view.className = 'apt-roadview__view';
      view.hidden = true;
      return view;
    });
    const empty = document.createElement('div');
    empty.className = 'apt-roadview__empty';
    empty.hidden = true;
    const text = document.createElement('p');
    text.className = 'apt-roadview__text';
    text.textContent = APT_NO_ROADVIEW;
    empty.append(text);
    box.append(...views, empty);
    const handle = document.getElementById('sheet-handle');
    handle.parentElement.insertBefore(box, handle);
    return box;
  },

  // 'view' 로드뷰, 'empty' 로드뷰 없음 문장, null 아무것도 (찾는 중)
  roadviewShow(which) {
    const box = aptPanel.roadviewBox();
    box.querySelectorAll('.apt-roadview__view').forEach((view) => {
      view.hidden = which !== 'view';
      if (which !== 'view') view.classList.remove('apt-roadview__view--on', 'apt-roadview__view--top');
    });
    box.querySelector('.apt-roadview__empty').hidden = which !== 'empty';
  },

  // 보일 때만 그린다. 같은 아파트면 다시 찾지 않는다 (창이 움직임을 마치면 크기만 맞춘다).
  // 아파트를 열면(30%부터) 미리 찾아 그려 둔다 (2026-10-18). 전체가 아닐 때는 같은 크기로 창 뒤에 숨겨 두고
  // (.apt-roadview--parked), 전체가 되면 그 자리에서 창과 함께 올라온다. 그래서 전체가 된 뒤 기다리지 않는다
  renderRoadview() {
    const { apartment } = aptPanel;
    const box = aptPanel.roadviewBox();
    const visible = Boolean(apartment) && aptPanel.roadviewVisible();
    const open = Boolean(apartment) && (sheet.phase === 'opening' || sheet.phase === 'open') && sheet.mode === 'apartment';
    box.hidden = !open;
    box.classList.toggle('apt-roadview--parked', open && !visible);
    if (!open) return;
    if (aptPanel.roadviewFor === apartment.id) {
      if (visible && aptPanel.roadview && !sheet.moving) aptPanel.roadview.relayout();
      return;
    }
    aptPanel.roadviewFor = apartment.id;
    const kakaoReady = typeof kakao !== 'undefined' && kakao.maps && typeof kakao.maps.RoadviewClient === 'function';
    if (!aptHasCoord(apartment) || !kakaoReady) {
      aptPanel.roadviewShow('empty');
      return;
    }
    const id = apartment.id;
    const position = new kakao.maps.LatLng(Number(apartment.latitude), Number(apartment.longitude));
    try {
      aptPanel.findPano(apartment, (panoId) => {
        if (aptPanel.roadviewFor !== id) return; // 찾는 사이에 다른 아파트로 넘겼다
        if (panoId === null || panoId === undefined) {
          aptPanel.roadviewShow('empty');
          return;
        }
        aptPanel.showPano(panoId, position, id);
      });
    } catch (error) {
      aptPanel.roadviewShow('empty'); // 카카오맵이 로드뷰를 주지 못하면 "로드뷰가 없습니다" 문장
    }
  },

  // 새 사진을 뒤의 화면에 띄우고, 아파트 쪽으로 돌린 뒤 앞 사진 위로 서서히 나타나게 한다 (크로스페이드).
  // 지금 보이는 사진이 없으면(처음, 없음 문장 뒤) 앞 화면에 그대로 띄워 나타나게 한다
  showPano(panoId, position, id) {
    const box = aptPanel.roadviewBox();
    const views = box.querySelectorAll('.apt-roadview__view');
    const front = aptPanel.roadviewFront;
    const showing = views[front].classList.contains('apt-roadview__view--on') && !views[front].hidden;
    const slot = showing ? 1 - front : front;
    const view = views[slot];
    const other = views[1 - slot];
    aptPanel.roadviewTimers.forEach(clearTimeout);
    aptPanel.roadviewTimers = [];
    box.querySelector('.apt-roadview__empty').hidden = true;
    views.forEach((item) => { item.hidden = false; });
    view.classList.remove('apt-roadview__view--on'); // 투명한 채로 맨 위에 둔다
    view.classList.add('apt-roadview__view--top');
    other.classList.remove('apt-roadview__view--top');
    if (!showing) other.classList.remove('apt-roadview__view--on');

    let rv = aptPanel.roadviews[slot];
    if (!rv) {
      rv = new kakao.maps.Roadview(view);
      aptPanel.roadviews[slot] = rv;
      // 촬영 지점이 정해지면(처음, 그리고 다른 지점으로 바뀔 때마다) 기다리던 일을 한다
      const ready = () => {
        const next = rv.onReady;
        rv.onReady = null;
        if (next) next();
      };
      kakao.maps.event.addListener(rv, 'init', ready);
      kakao.maps.event.addListener(rv, 'panoid_changed', ready);
      // 지점을 바꾸면 카카오 로드뷰가 스스로 옮겨 가는 움직임(방향이 바뀜)을 넣는다. 움직이는 동안은 신호가 계속 온다 (rv.onMove)
      kakao.maps.event.addListener(rv, 'viewpoint_changed', () => {
        if (rv.onMove) rv.onMove();
      });
    }
    let shown = false;
    const reveal = () => {
      if (shown || aptPanel.roadviewFor !== id) return;
      shown = true;
      view.classList.add('apt-roadview__view--on'); // 서서히 나타난다
      aptPanel.roadviewFront = slot;
      aptPanel.roadview = rv;
      aptPanel.roadviewTarget = position;
      // 다 나타난 뒤 앞 사진은 투명하게 둔다 (다음에 뒤의 화면으로 쓴다)
      aptPanel.roadviewTimers.push(setTimeout(() => other.classList.remove('apt-roadview__view--on'), APT_ROADVIEW_FADE_MS));
    };
    // 움직임이 멈출 때까지 기다렸다가 보여 준다 (2026-10-20). 예전에는 신호 뒤 0.25초에 보여 줘서,
    // 카카오의 옮겨 가는 움직임이 끝나기 전에 나타나 사진이 옆으로 밀렸다가 자리 잡는 것이 보였다.
    // 방향 변경 신호가 APT_ROADVIEW_SETTLE_MS 동안 더 오지 않으면 멈춘 것으로 본다
    let settle = null;
    const waitStill = () => {
      clearTimeout(settle);
      settle = setTimeout(() => {
        rv.onMove = null;
        reveal();
      }, APT_ROADVIEW_SETTLE_MS);
      aptPanel.roadviewTimers.push(settle);
    };
    rv.onReady = () => {
      aptPanel.aimRoadview(rv, position);
      rv.onMove = waitStill;
      waitStill();
    };
    const samePano = typeof rv.getPanoId === 'function' && rv.getPanoId() === panoId;
    rv.setPanoId(panoId, position);
    rv.relayout();
    if (samePano && rv.onReady) rv.onReady(); // 같은 지점이면 바뀌었다는 신호가 오지 않는다
    aptPanel.roadviewTimers.push(setTimeout(reveal, APT_ROADVIEW_REVEAL_MAX_MS)); // 신호가 안 와도 언젠가는 보인다
  },

  // 아파트의 가장 가까운 로드뷰 지점. 찾아 둔 것이 있으면 바로, 없으면 카카오에 물어 기억해 둔다
  findPano(apartment, done) {
    if (aptPanel.panoIds.has(apartment.id)) {
      done(aptPanel.panoIds.get(apartment.id));
      return;
    }
    const position = new kakao.maps.LatLng(Number(apartment.latitude), Number(apartment.longitude));
    new kakao.maps.RoadviewClient().getNearestPanoId(position, APT_ROADVIEW_RADIUS, (panoId) => {
      aptPanel.panoIds.set(apartment.id, panoId ?? null);
      done(panoId);
    });
  },

  // 동을 받으면(map-view.js의 loadData) 그 아파트들의 로드뷰 지점을 미리 찾아 둔다. 몇 개씩 차례로, 찾은 것은 다시 찾지 않는다
  prefetchRoadviews(apartments) {
    const kakaoReady = typeof kakao !== 'undefined' && kakao.maps && typeof kakao.maps.RoadviewClient === 'function';
    if (!kakaoReady) return;
    const todo = apartments.filter((a) => aptHasCoord(a) && !aptPanel.panoIds.has(a.id)).slice(0, APT_ROADVIEW_PREFETCH_MAX);
    const next = () => {
      const apartment = todo.shift();
      if (!apartment) return;
      try {
        aptPanel.findPano(apartment, next);
      } catch (error) {
        next();
      }
    };
    for (let i = 0; i < APT_ROADVIEW_PREFETCH_AT_ONCE; i += 1) next();
  },

  // 로드뷰가 아파트를 바라보게 한다 (2026-10-18). 카카오는 바라보는 방향을 정해 주지 않아 길 방향으로 열린다.
  // 촬영 지점(로드뷰의 자리)에서 아파트 좌표로 가는 방위각(북쪽 0도, 시계 방향)을 구해 시점의 좌우 각도(pan)로 둔다.
  // 위아래(tilt)는 살짝 위(-20도, 카카오는 음수가 위), 확대(zoom)는 가장 넓게(-3). 아파트 건물이 위층까지 들어온다
  roadviewTarget: null,
  aimRoadview(rv = aptPanel.roadview, target = aptPanel.roadviewTarget) {
    if (!rv || !target) return;
    const from = rv.getPosition();
    if (!from) return;
    const rad = Math.PI / 180;
    const lat1 = from.getLat() * rad;
    const lat2 = target.getLat() * rad;
    const dLng = (target.getLng() - from.getLng()) * rad;
    const y = Math.sin(dLng) * Math.cos(lat2);
    const x = Math.cos(lat1) * Math.sin(lat2) - Math.sin(lat1) * Math.cos(lat2) * Math.cos(dLng);
    const pan = (Math.atan2(y, x) / rad + 360) % 360;
    rv.setViewpoint(new kakao.maps.Viewpoint(pan, APT_ROADVIEW_TILT, APT_ROADVIEW_ZOOM));
  },

  // ───────── 비슷한 아파트 (3차, 목업 C6, 김목산의 similar.js) ─────────

  similarReady: () => typeof similarView !== 'undefined' && typeof similarView.load === 'function',

  // 자리. similar.js가 없으면 null (자리를 만들지 않는다)
  similarBox() {
    if (!aptPanel.similarReady()) return null;
    let box = document.getElementById('apt-similar');
    if (!box) {
      box = document.createElement('div');
      box.id = 'apt-similar';
    }
    return box;
  },

  // 아파트 정보 탭이 보일 때 부른다. 아파트, 면적, 조건이 지난번과 같으면 다시 부르지 않는다
  renderSimilar() {
    // 면적만 바꿨으면 칸이 미끄러지는 동안(약 0.4초)은 기다렸다가 받는다. 도중에 카드를 다시 그리면 움직임이 걸렸다.
    // 기다린 뒤에는 그때의 아파트 · 면적으로 다시 본다 (그사이 바뀌었어도 맞는 것을 받는다)
    clearTimeout(aptPanel.similarTimer);
    if (aptPanel.areaOnly) {
      aptPanel.similarTimer = setTimeout(() => aptPanel.renderSimilar(), APT_AREA_SLIDE_MS + 40);
      return;
    }
    const { apartment } = aptPanel;
    const box = aptPanel.similarBox();
    if (!box || !apartment || !aptPanel.infoVisible()) return;
    const area = apartment.areas[aptPanel.areaIndex];
    const key = JSON.stringify([apartment.id, area.area_band, guard.conditions()]);
    if (key === aptPanel.similarKey) return;
    aptPanel.similarKey = key;
    similarView.load(box, { apartmentId: apartment.id, areaBand: area.area_band }, { onPick: aptPanel.pickSimilar });
  },

  // ───────── 주변 시설 (3차, FR-MAP-23, 와이어프레임 C6) ─────────

  // 주변 시설 자리. 제목, 다섯 줄(이름 칸과 값 칸), 학교 종류별 네 줄, 출처를 한 번만 만든다
  nearBox() {
    let box = document.getElementById('apt-near');
    if (box) return box;
    box = document.createElement('section');
    box.id = 'apt-near';
    box.className = 'apt-near';
    const title = document.createElement('h3');
    title.className = 'apt-near__title';
    title.textContent = APT_NEAR_TITLE;
    const list = document.createElement('dl');
    list.className = 'apt-near__list';
    const makeRow = (label, kind, icon) => {
      const row = document.createElement('div');
      row.className = 'apt-near__row';
      const term = document.createElement('dt');
      term.className = 'apt-near__label';
      if (icon) term.append(aptNearIcon(icon));
      term.append(document.createTextNode(label));
      const desc = document.createElement('dd');
      desc.className = 'apt-near__value';
      desc.dataset.kind = kind;
      row.append(term, desc);
      return row;
    };
    APT_NEAR_KINDS.forEach(({ kind, label, icon }) => {
      const row = makeRow(label, kind, icon);
      list.append(row);
      if (kind === 'school') {
        // 학교: 오른쪽 ⌄로 초·중·고·대학교를 펼친다. 처음에는 접어 두고 가장 가까운 학교만 보인다
        const toggle = document.createElement('button');
        toggle.type = 'button';
        toggle.className = 'apt-near__toggle';
        toggle.setAttribute('aria-expanded', 'false');
        toggle.setAttribute('aria-label', APT_NEAR_MORE);
        toggle.append(aptNearIcon('M6.4 8.6L12 14.2l5.6-5.6L19 10l-7 7-7-7 1.4-1.4z'));
        toggle.addEventListener('click', () => aptPanel.toggleSchools());
        row.append(toggle);
        const sub = document.createElement('div');
        sub.className = 'apt-near__sub';
        sub.id = 'apt-near-schools';
        sub.hidden = true;
        APT_NEAR_SCHOOLS.forEach((school) => {
          const subRow = makeRow(school.label, school.kind);
          subRow.classList.add('apt-near__row--sub');
          sub.append(subRow);
        });
        toggle.setAttribute('aria-controls', sub.id);
        list.append(sub);
      }
    });
    const source = document.createElement('p');
    source.className = 'apt-near__source';
    box.append(title, list, source);
    return box;
  },

  // 학교 줄의 ⌄. 값은 이미 채워 두었으므로 펼치고 접기만 한다. open을 주면 그 상태로
  toggleSchools(open) {
    const box = document.getElementById('apt-near');
    if (!box) return;
    const toggle = box.querySelector('.apt-near__toggle');
    const next = open === undefined ? toggle.getAttribute('aria-expanded') !== 'true' : open;
    toggle.setAttribute('aria-expanded', String(next));
    toggle.setAttribute('aria-label', next ? APT_NEAR_LESS : APT_NEAR_MORE);
    box.querySelector('.apt-near__sub').hidden = !next;
  },

  // A-06의 facilities로 주변 시설을 채운다. 받은 값이 없거나 좌표가 없으면 묶음을 숨긴다
  renderNear(detail) {
    const { apartment } = aptPanel;
    const box = aptPanel.nearBox();
    const items = (detail && detail.facilities) || [];
    box.hidden = !apartment || !aptHasCoord(apartment) || !items.length;
    if (box.hidden) return;
    if (box.dataset.apartmentId !== String(apartment.id)) aptPanel.toggleSchools(false); // 다른 아파트로 바뀌면 학교 종류별 묶음은 접는다
    box.dataset.apartmentId = String(apartment.id);
    const byKind = new Map(items.map((item) => [item.kind, item]));
    box.querySelectorAll('.apt-near__value').forEach((cell) => {
      let kind = cell.dataset.kind;
      let item = byKind.get(kind);
      if (kind === 'subway') {
        // 지하철역이 근처에 없고 버스정류장은 있으면 이 줄을 버스정류장으로 (이름 칸도 바꾼다). 아니면 지하철역 그대로
        const bus = byKind.get(APT_NEAR_BUS.kind);
        const useBus = !(item && item.place_name) && Boolean(bus && bus.place_name);
        const base = APT_NEAR_KINDS[0];
        aptPanel.nearLabel(cell, useBus ? APT_NEAR_BUS : base);
        if (useBus) {
          kind = APT_NEAR_BUS.kind;
          item = bus;
        }
      }
      aptPanel.nearFill(cell, item ? aptPanel.nearValue(item) : APT_NEAR_NONE, kind);
    });
    const [year, month, day] = (detail.facilities_base_date || '').split('-');
    box.querySelector('.apt-near__source').textContent = year
      ? `${APT_NEAR_SOURCE} · ${year}년 ${Number(month)}월 ${Number(day)}일 기준`
      : '';
  },

  // 줄의 이름 칸(그림 + 이름)을 바꾼다. 같은 것이면 그대로 둔다
  nearLabel(cell, { label, icon }) {
    const term = cell.previousElementSibling;
    if (!term || term.dataset.label === label) return;
    term.dataset.label = label;
    term.replaceChildren(aptNearIcon(icon), document.createTextNode(label));
  },

  // 한 줄의 값. 화면에는 nearFill이 "전남고등학교" / "약 170m · 도보 약 3분" 두 줄로 적는다.
  //   { name: "전남고등학교", meters: 130(직선), item }. 지하철역은 { name, exit, meters, item } (출구 번호를 노란 상자로)
  //   출구를 못 찾은 역은 exit 없이 { name: "상무역 광주1호선", meters, item }
  // item(A-06의 시설 하나)은 줄을 누르면 지도에서 그 시설을 찾아 보여 주려고 같이 둔다
  // 면적 칸에 한 번만 단다: 마우스 휠(위아래)로도 옆으로 넘기고, 넘길 것이 남은 쪽 끝을 흐리게 한다 (sheet.css)
  // 네이버 지도처럼 끊김 없이 (2026-10-20): 움직임은 브라우저의 smooth 대신 직접 그린다 (slideArea, 감속 곡선).
  //   휠: 굴린 만큼 목표를 더해 그쪽으로 미끄러진다 (빠르게 여러 번 굴려도 이어서 간다)
  //   마우스로 잡아 끌기: 손을 따라 움직이고, 놓으면 그 빠르기로 조금 더 미끄러지다 멈춘다 (터치는 브라우저 기본 그대로)
  watchAreaList(list) {
    if (list.dataset.watched) return;
    list.dataset.watched = 'true';
    const max = () => Math.max(0, list.scrollWidth - list.clientWidth);
    list.addEventListener('wheel', (event) => {
      if (max() === 0 || Math.abs(event.deltaX) > Math.abs(event.deltaY)) return;
      event.preventDefault(); // 창이 위아래로 스크롤되지 않게
      const from = list.slide ? list.slide.to : list.scrollLeft;
      aptPanel.slideArea(list, from + event.deltaY, 260);
    }, { passive: false });
    list.addEventListener('scroll', () => aptPanel.markAreaEdges(list), { passive: true });

    let drag = null;
    list.addEventListener('pointerdown', (event) => {
      if (event.pointerType !== 'mouse' || event.button !== 0 || max() === 0) return;
      aptPanel.stopArea(list);
      drag = { x: event.clientX, left: list.scrollLeft, moved: false, samples: [[event.timeStamp, event.clientX]] };
    });
    window.addEventListener('pointermove', (event) => {
      if (!drag) return;
      const dx = event.clientX - drag.x;
      if (!drag.moved && Math.abs(dx) < 4) return; // 조금 흔들린 것은 누름으로 둔다
      if (!drag.moved) list.classList.add('apt__area-list--dragging');
      drag.moved = true;
      list.scrollLeft = drag.left - dx;
      drag.samples.push([event.timeStamp, event.clientX]);
      if (drag.samples.length > 5) drag.samples.shift();
    });
    window.addEventListener('pointerup', () => {
      if (!drag) return;
      const { moved, samples } = drag;
      drag = null;
      list.classList.remove('apt__area-list--dragging');
      if (!moved) return;
      list.dataset.dragged = 'true'; // 바로 뒤에 오는 click을 막는다
      setTimeout(() => delete list.dataset.dragged, 0);
      // 놓기 직전의 빠르기(px/ms)로 관성. 0.3초 동안 그 빠르기의 약 1/3만큼 더 간다
      const [t0, x0] = samples[0];
      const [t1, x1] = samples[samples.length - 1];
      const speed = t1 > t0 ? (x1 - x0) / (t1 - t0) : 0;
      if (Math.abs(speed) > 0.1) aptPanel.slideArea(list, list.scrollLeft - speed * 120, 420);
    });
  },

  // 면적 칸을 left까지 ms 동안 미끄러뜨린다. 처음 빠르고 끝에 천천히 멈춘다 (easeOutCubic).
  // 움직이는 중에 다시 부르면 지금 자리에서 새 목표로 이어 간다
  slideArea(list, left, ms = APT_AREA_SLIDE_MS) {
    const to = Math.max(0, Math.min(left, list.scrollWidth - list.clientWidth));
    aptPanel.stopArea(list);
    if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
      list.scrollLeft = to;
      return;
    }
    const from = list.scrollLeft;
    const start = performance.now();
    const slide = { to, frame: 0 };
    const step = (now) => {
      const t = Math.min(1, (now - start) / ms);
      list.scrollLeft = from + (to - from) * (1 - (1 - t) ** 3);
      if (t < 1) slide.frame = requestAnimationFrame(step);
      else list.slide = null;
    };
    list.slide = slide;
    slide.frame = requestAnimationFrame(step);
  },

  stopArea(list) {
    if (list.slide) cancelAnimationFrame(list.slide.frame);
    list.slide = null;
  },

  // index번째 면적이 칸 가운데에 오게 옆으로 민다. 끝 쪽 면적이면 끝까지만
  centerArea(list, index, smooth) {
    const picked = list.children[index];
    if (picked && list.clientWidth) {
      const chip = picked.getBoundingClientRect();
      const box = list.getBoundingClientRect();
      const left = list.scrollLeft + (chip.left - box.left) - (list.clientWidth - chip.width) / 2;
      if (smooth) aptPanel.slideArea(list, left);
      else {
        aptPanel.stopArea(list);
        list.scrollLeft = Math.max(0, left);
      }
    }
    aptPanel.markAreaEdges(list);
  },

  // 왼쪽 · 오른쪽에 더 볼 면적이 있는가 (sheet.css의 흐린 끝)
  markAreaEdges(list) {
    const max = list.scrollWidth - list.clientWidth;
    list.classList.toggle('apt__area-list--more-left', list.scrollLeft > 2);
    list.classList.toggle('apt__area-list--more-right', list.scrollLeft < max - 2);
  },

  nearValue(item) {
    if (!item.place_name) return APT_NEAR_NONE;
    const meters = Number(item.distance);
    if (item.kind !== 'subway') return { name: item.place_name, meters, item };
    if (item.exit_no === null || item.exit_no === undefined) return { name: item.place_name, meters, item };
    return { name: item.place_name, exit: String(item.exit_no), meters, item };
  },

  // 한 칸을 채운다. 글자(근처에 없음)이면 그대로 적는다.
  // 찾은 곳이면 누를 수 있게 단추로 만든다. 누르면 지도에서 그 시설을 보여 준다 (map-view.js의 showFacilityOnMap)
  // 모든 줄이 두 줄이다 (2026-10-20): 첫 줄은 이름, 둘째 줄은 거리와 도보 시간.
  //   "전남고등학교"                       "김대중컨벤션센터역 광주1호선"
  //   "약 170m · 도보 약 3분 [위치]"        "[5]번 출구 약 430m · 도보 약 7분 [위치]"
  // 지하철도 다른 시설과 같게 "까지"를 붙이지 않는다. 출구 번호는 지하철 출구 표지처럼 작은 노란 상자로 (sheet.css .apt-near__exit)
  // 이름이 한 줄에 다 들어가지 않으면 끝을 "…"로 줄인다 (sheet.css .apt-near__name). 전체 이름은 aria-label과 title에 있다
  // kind: 그 줄의 A-06 kind (학교 종류별 줄은 elementary 등)
  nearFill(cell, value, kind) {
    if (typeof value === 'string') {
      cell.textContent = value;
      return;
    }
    const button = document.createElement('button');
    button.type = 'button';
    button.className = 'apt-near__link';
    const pin = aptNearIcon(APT_NEAR_PIN);
    pin.setAttribute('class', 'apt-near__pin');
    const { distance, time } = aptWalk(value.meters);

    const name = document.createElement('span');
    name.className = 'apt-near__name';
    name.textContent = value.name;
    name.title = value.name;

    // 둘째 줄. "약 670m · 도보 약 10분 [위치]" (지하철은 "[5]번 출구 약 430m · 도보 약 7분 [위치]"). 줄을 바꾸지 않는다 (sheet.css .apt-near__line)
    const line = document.createElement('span');
    line.className = 'apt-near__line';
    if (value.exit) {
      const badge = document.createElement('span');
      badge.className = 'apt-near__exit';
      badge.textContent = value.exit;
      line.append(badge, '번 출구 ');
    }
    line.append(`${distance} · ${time}`, pin);

    button.append(name, line);
    const exit = value.exit ? ` ${value.exit}번 출구` : '';
    button.setAttribute('aria-label', `${value.name}${exit} ${distance} · ${time} ${APT_NEAR_ON_MAP}`);
    button.addEventListener('click', () => {
      if (typeof showFacilityOnMap === 'function') showFacilityOnMap(kind, value.item);
    });
    cell.replaceChildren(button);
  },

  // 비슷한 아파트의 카드를 누름. apartment는 A-24 응답의 아파트, areaBand는 카드에 보이던 면적대
  //   map-view.js의 onPickSimilar에 맡긴다. 같은 동이든 다른 동이든 지도를 한 번에(setCenter) 옮긴다.
  //   (‹ ›의 onMove는 panTo로 부드럽게 옮기는데, 실제 카카오맵의 panTo는 80%의 좁은 지도에서 가운데에 멈추지 않을 때가 있었다)
  //   onPickSimilar가 없으면 지금 지도에 있는 아파트만 ‹ ›와 같이 넘긴다 (그 면적을 고르고, 아파트 정보 탭 맨 위로)
  pickSimilar(apartment, areaBand) {
    const { handlers } = aptPanel;
    if (typeof handlers.onPickSimilar === 'function') {
      handlers.onPickSimilar(apartment, areaBand);
      return;
    }
    const order = handlers.order ? handlers.order(aptPanel.apartment) : [];
    const known = order.find((item) => item.id === apartment.id);
    if (known) {
      const areaIndex = Math.max(known.areas.findIndex((area) => area.area_band === areaBand), 0);
      aptPanel.show(known, areaIndex, { listPlace: aptPanel.listPlace });
      handlers.onMove(known);
      document.querySelector('.apt__panels').scrollTop = 0;
    }
  },

  // ───────── 아파트 정보 탭 (P-06 ⑦, A-06) ─────────

  // 아파트 정보 탭이 지금 보이는가. 80% 이상이고, 아파트 창이고, 그 탭이 골라져 있을 때
  infoVisible() {
    return (sheet.phase === 'opening' || sheet.phase === 'open') && sheet.mode === 'apartment' &&
      (sheet.stage === '80' || sheet.stage === 'full') &&
      document.getElementById('apt-tab-info').getAttribute('aria-selected') === 'true';
  },

  // 보일 때만 그린다. 받은 것이 없으면 받으러 간다.
  renderInfo() {
    const { apartment } = aptPanel;
    if (!apartment || !aptPanel.infoVisible()) return;
    const panel = document.getElementById('apartment-info');
    const notice = aptPanel.noCoordNotice(); // 좌표가 없으면 맨 위에 (받는 중에도 보인다)
    const similar = aptPanel.similarBox(); // 비슷한 아파트 자리. 같은 요소를 다시 붙이므로 그려 둔 카드가 남는다
    const near = aptPanel.nearBox(); // 주변 시설 자리. 같은 요소를 다시 붙인다
    // rows: 정보 줄을 그릴 때만 "기본 정보" 제목과 주변 시설을 붙인다 (제목은 비슷한 아파트가 있을 때만)
    const show = (content, rows = false) => {
      const title = rows && similar ? aptInfoTitle() : null;
      panel.replaceChildren(...[notice, title, content, rows ? near : null, similar].filter(Boolean));
      if (rows) aptPanel.renderNear(aptPanel.details.get(apartment.id));
      aptPanel.renderSimilar();
    };
    const detail = aptPanel.details.get(apartment.id);
    if (detail) {
      show(aptPanel.infoRows(detail), true);
      return;
    }
    if (aptPanel.failed.has(apartment.id)) {
      show(aptPanel.infoFail(apartment.id));
      return;
    }
    show(null); // 받는 동안은 안내만 두고 비워 둔다
    aptPanel.loadDetail(apartment.id);
  },

  async loadDetail(id) {
    if (aptPanel.loading.has(id)) return;
    aptPanel.loading.add(id);
    try {
      aptPanel.details.set(id, await api.get(`/api/apartments/${id}`));
    } catch (error) {
      aptPanel.failed.add(id);
    } finally {
      aptPanel.loading.delete(id);
    }
    // 받는 동안 다른 아파트로 넘어갔으면 그 아파트를 그린다. 같은 아파트면 지금 받은 것으로 그린다
    aptPanel.renderInfo();
  },

  // 정보 여덟 줄. 면적, 평균가, 가격 범위, 거래 건수는 지금 고른 면적의 것이다.
  // 세대수를 모르는 아파트는 세대수 줄을 그리지 않는다 (FR-APT-15).
  infoRows(detail) {
    const picked = aptPanel.apartment.areas[aptPanel.areaIndex];
    const area = detail.areas.find((item) => item.area_band === picked.area_band) || picked;
    const rows = [
      ['지번 주소', `${detail.dong} ${detail.jibun}`],
      ['도로명 주소', detail.road_address],
      ['준공 연도', detail.built_year === null ? null : `${detail.built_year}년`],
      ['면적', format.area(area.supply_area, area.exclusive_area, aptPanel.unit())],
      ['실거래 평균가', format.won(area.avg_price)],
      ['최근 1년 거래', aptPanel.tradeText(area)],
      ['세대수', aptPanel.householdsText(detail)],
      ['가격 범위', aptPanel.priceRangeText(area)],
    ];
    const list = document.createElement('dl');
    list.className = 'apt-info';
    rows.filter(([, value]) => value !== null && value !== undefined && value !== '').forEach(([label, value]) => {
      const row = document.createElement('div');
      row.className = 'apt-info__row';
      const term = document.createElement('dt');
      term.className = 'apt-info__label';
      term.textContent = label;
      const desc = document.createElement('dd');
      desc.className = 'apt-info__value';
      desc.textContent = value;
      // 주소 옆 복사 아이콘 (FR-APT-18, share.js). 누르면 바로 클립보드에 넣는다
      if ((label === '지번 주소' || label === '도로명 주소') && typeof shareView !== 'undefined') {
        desc.append(shareView.copyButton(() => format.fullAddress(detail.gu, value), `${label} 복사`)); // 복사는 시도와 구까지
      }
      row.append(term, desc);
      list.append(row);
    });
    return list;
  },

  // 세대수 "1,234세대 (2026년 8월 기준)". 세대수를 모르면 null (줄을 그리지 않는다). 기준일을 모르면 괄호를 뺀다
  householdsText(detail) {
    if (detail.households === null || detail.households === undefined) return null;
    const count = `${format.comma(detail.households)}세대`;
    if (!detail.households_base_date) return count;
    const [year, month] = detail.households_base_date.split('-');
    return `${count} (${year}년 ${Number(month)}월 기준)`;
  },

  // 최근 1년 거래 "14건 (2025년 10월 ~ 2026년 9월)". 괄호는 집계 기간(A-06의 period_start ~ period_end)이다.
  // 줄을 늘리지 않고 이 줄에 붙인다 (와이어프레임의 여덟 줄 그대로). 기간을 모르면 괄호를 뺀다
  tradeText(area) {
    const count = `${format.comma(area.trade_count)}건`;
    if (!area.period_start || !area.period_end) return count;
    const month = (text) => {
      const [year, mm] = text.split('-');
      return `${year}년 ${Number(mm)}월`;
    };
    return `${count} (${month(area.period_start)} ~ ${month(area.period_end)})`;
  },

  // 가격 범위 "2억 7,000만 ~ 3억 3,000만 원" (목업 2038:566). 앞 금액의 "원"은 뺀다
  priceRangeText(area) {
    if (area.min_price === null || area.min_price === undefined || area.max_price === null || area.max_price === undefined) return null;
    return `${format.won(area.min_price).replace(/ 원$/, '')} ~ ${format.won(area.max_price)}`;
  },

  infoFail(id) {
    const box = document.createElement('div');
    box.className = 'apt-info__fail';
    const text = document.createElement('p');
    text.className = 'apt-info__fail-text';
    text.textContent = APT_INFO_FAIL;
    const retry = document.createElement('button');
    retry.type = 'button';
    retry.className = 'link-button';
    retry.textContent = '다시 시도';
    retry.addEventListener('click', () => {
      aptPanel.failed.delete(id);
      aptPanel.renderInfo();
    });
    box.append(text, retry);
    return box;
  },
};
