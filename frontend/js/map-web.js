// 지도 화면의 웹 배치 (가로 1024px 이상. 2026-10-20 팀장 결정으로 1200 → 1024. 입력 화면은 1200 그대로). 담당: 박채은 (2026-10-20 팀장 결정: 웹 지도 시안 2 "두 패널")
// 모양은 css/map-web.css. 이 파일은 웹에서만 아래 창(sheet.js)의 동작을 왼쪽 패널에 맞게 바꾼다.
// sheet.js, map-view.js, apartment.js(안세환)는 고치지 않고, 그 객체의 함수를 웹일 때만 감싸 바꾼다.
// 그래서 map.html에서 이 파일은 맨 마지막(map-view.js 다음)에 불러온다. 1023px 이하에서는 원래 함수 그대로 동작한다.
//
// 웹에서 바뀌는 것
//   - 단계가 없다. 창은 늘 30% 단계로 연다 (지도가 보이는 단계. 주변 시설 줄을 누르면 지도에 점선을 잇는 것도 이 단계에서 된다).
//     모양은 map-web.css가 단계와 상관없이 왼쪽 패널로 그린다. 손잡이를 누르거나 끌어도 바뀌지 않는다.
//   - 목록은 늘 열려 있다. 아파트 창을 닫으면(✕, 뒤로 가기, 다른 지역 고르기) 창을 닫지 않고 목록만 남긴다. 목록의 스크롤 자리는 그대로 둔다.
//   - 지도는 창에 가리지 않으므로 고른 아파트는 지도의 가운데에 둔다. 패널 폭이 바뀌면 카카오맵에 알린다 (relayout).
//   - 목록 패널을 접고 펼 수 있다. 접은 상태는 저장하지 않는다: 지도 화면을 열면 늘 목록이 펼쳐진 채로 시작한다 (2026-10-20 팀장 결정).
//   - 조건 줄(머리 줄 바로 아래): [조건] · 구·동을 고르면 지역 칩 · 넣은 조건 칩 · 실거래 기준일 · 안내(!) (2026-10-20, 김목산).
//     칩 줄(.chip-row)과 안내(.info-tip)는 웹일 때만 이 줄로 옮기고 모바일이면 제자리로 돌린다. id와 동작은 그대로다.
//   - 로드뷰는 아파트 패널 맨 위에 늘 보인다 (아파트 정보 탭 · 시나리오 탭 모두, 2026-10-20 팀장 결정).
//     모바일은 창 맨 위(손잡이 앞)에 두고 전체 단계에서만 보이지만, 웹에는 단계가 없으므로 자리를 아파트 패널 안으로 옮긴다.
//
// html에 다는 표시 (map-web.css가 쓴다)
//   data-map-web-panel = "list" | "apartment"   패널에 지금 보이는 것. 창이 닫혀 있으면 없다
//   data-map-web-fold                           목록 패널을 접었다
//   data-map-web-apt-fold                       아파트 패널을 접었다

const MAP_WEB_QUERY = window.matchMedia('(min-width: 1024px)'); // css/map-web.css의 @media와 같은 폭
const MAP_WEB_STAGE = '30';

const mapWeb = {
  isOn: () => MAP_WEB_QUERY.matches,

  // 감싸기 전의 원래 함수
  base: {
    show: sheet.show,
    hide: sheet.hide,
    apply: sheet.apply,
    setStage: sheet.setStage,
    startDrag: sheet.startDrag,
    moveDrag: sheet.moveDrag,
    endDrag: sheet.endDrag,
    targetHeight: sheet.targetHeight,
    infoVisible: aptPanel.infoVisible,
    roadviewVisible: aptPanel.roadviewVisible,
    roadviewBox: aptPanel.roadviewBox,
  },

  wasOn: false, // 마지막으로 맞춘 배치가 웹이었는가 (창 폭이 1024px을 넘나드는 것을 알아챈다)

  init() {
    mapWeb.wrapSheet();
    mapWeb.initFilterBar();
    mapWeb.initFold();
    mapWeb.watchMapSize();

    // 처음 열 때: 웹이면 목록을 바로 연다 (map-view.js의 initMap 다음에 부른다)
    document.addEventListener('DOMContentLoaded', () => {
      if (mapWeb.isOn()) mapWeb.openList();
    });

    // 창 폭이 1024px을 넘나들 때. 미디어 쿼리의 change만으로는 놓치는 브라우저가 있어 resize에서도 확인한다.
    // 앞의 상태(mapWeb.wasOn)와 다를 때만 바꾼다
    mapWeb.wasOn = mapWeb.isOn();
    const onModeChange = () => {
      const on = mapWeb.isOn();
      if (on === mapWeb.wasOn) return;
      mapWeb.wasOn = on;
      if (on) {
        if (sheet.isShown()) sheet.show(MAP_WEB_STAGE, sheet.mode); // 모바일 단계에서 웹 단계로
        else mapWeb.openList();
      } else if (sheet.isShown() && sheet.mode === 'list') {
        mapWeb.base.hide(); // 웹에서만 늘 열어 두던 목록은 닫는다. 모바일은 지도만 보이는 처음 모양에서 시작한다
      } else if (sheet.isShown()) {
        mapWeb.base.show(MAP_WEB_STAGE, sheet.mode); // 아파트를 보던 중이면 모바일 30%로 둔다
      }
      sheet.apply(); // 표시를 다시 단다 (모바일이면 sheet.js의 원래 표시로 돌아간다)
      mapWeb.placeRoadview();
      mapWeb.placeFilterBar();
      aptPanel.renderRoadview();
    };
    MAP_WEB_QUERY.addEventListener('change', onModeChange);
    window.addEventListener('resize', onModeChange);
  },

  // ───────── 아래 창을 왼쪽 패널로 ─────────
  wrapSheet() {
    const { base } = mapWeb;

    sheet.show = (stage, mode) => {
      if (mode === 'apartment' && mapWeb.aptFolded) {
        mapWeb.aptFolded = false; // 아파트를 새로 열면 접어 둔 아파트 패널을 편다
        mapWeb.renderFold();
      }
      base.show(mapWeb.isOn() ? MAP_WEB_STAGE : stage, mode);
    };

    sheet.setStage = (stage) => {
      if (!mapWeb.isOn()) base.setStage(stage);
    };

    // 끌기: 웹에서는 높이를 바꾸지 않는다
    sheet.startDrag = () => {
      if (!mapWeb.isOn()) base.startDrag();
    };
    sheet.moveDrag = (height) => {
      if (!mapWeb.isOn()) base.moveDrag(height);
    };
    sheet.endDrag = (height, speed) => {
      if (!mapWeb.isOn()) {
        base.endDrag(height, speed);
        return;
      }
      sheet.dragging = false;
      sheet.moving = false;
    };

    // 지도는 창에 가리지 않는다. 고른 아파트를 남은 자리가 아니라 지도의 가운데에 둔다 (map-view.js의 panToRemaining)
    sheet.targetHeight = () => (mapWeb.isOn() ? 0 : base.targetHeight());

    // 닫기: 아파트 창이면 목록으로 돌아가고, 목록이면 닫지 않는다
    sheet.hide = () => {
      if (!mapWeb.isOn()) {
        base.hide();
        return;
      }
      if (sheet.mode === 'apartment') mapWeb.backToList();
    };

    // 모바일의 단계 표시(.map-app의 data-sheet, data-sheet-map)를 떼어 sheet.css의 단계별 규칙
    // (검색 줄 · 버튼 숨기기, 지도 줄이기)이 걸리지 않게 하고, 웹 표시를 단다
    sheet.apply = () => {
      // 웹에서는 목록이 늘 옆에 보이므로 보던 자리를 그대로 둔다 (2026-10-20 팀장 결정).
      // sheet.js는 보이는 칸이 바뀌면(아파트 → 목록) 목록을 맨 위로 보내므로, 그 전 자리를 기억했다가 되돌린다
      const list = document.getElementById('apt-list');
      const keep = mapWeb.isOn() ? list.scrollTop : null;
      base.apply();
      if (keep !== null && mapWeb.isOn()) list.scrollTop = keep;
      const app = document.querySelector('.map-app');
      const root = document.documentElement;
      if (!mapWeb.isOn()) {
        delete root.dataset.mapWebPanel;
        return;
      }
      delete app.dataset.sheet;
      delete app.dataset.sheetMap;
      if (sheet.isShown()) root.dataset.mapWebPanel = sheet.mode;
      else delete root.dataset.mapWebPanel;
    };

    // 로드뷰: 웹에서는 아파트 패널이 열려 있으면 늘 보인다 (단계와 상관없이)
    aptPanel.roadviewVisible = () => {
      if (!mapWeb.isOn()) return base.roadviewVisible();
      return sheet.isShown() && sheet.mode === 'apartment';
    };
    // 로드뷰 자리를 만들 때와 웹 ↔ 모바일이 바뀔 때 알맞은 곳에 둔다
    aptPanel.roadviewBox = () => {
      const box = base.roadviewBox();
      mapWeb.placeRoadview(box);
      return box;
    };

    // 아파트 정보 탭은 원래 80% 이상에서만 그린다. 웹에서는 단계와 상관없이 늘 보인다
    aptPanel.infoVisible = () => {
      if (!mapWeb.isOn()) return base.infoVisible();
      return sheet.isShown() && sheet.mode === 'apartment' &&
        document.getElementById('apt-tab-info').getAttribute('aria-selected') === 'true';
    };
  },

  // 로드뷰 자리를 옮긴다. 웹: 아파트 패널 맨 위(이름 줄 위). 모바일: 창 맨 위(손잡이 앞, apartment.js가 처음 둔 곳)
  // 옮긴 뒤에는 카카오 로드뷰에 새 크기를 알린다 (relayout)
  placeRoadview(box = document.getElementById('apt-roadview')) {
    if (!box) return;
    const panel = document.getElementById('apartment-panel');
    const handle = document.getElementById('sheet-handle');
    if (mapWeb.isOn()) {
      if (box.parentElement === panel && panel.firstElementChild === box) return;
      panel.prepend(box);
    } else {
      if (box.nextElementSibling === handle) return;
      handle.parentElement.insertBefore(box, handle);
    }
    if (aptPanel.roadview) requestAnimationFrame(() => aptPanel.roadview.relayout());
  },

  // 목록을 연다. 기록(history)을 남기지 않는다: 늘 열려 있는 목록이라 뒤로 가기는 앞 화면으로 가야 한다.
  // sheet.show는 닫기가 끝나기를 기다리는 중(backPending)에는 기록을 더하지 않으므로, 그 표시를 잠깐 빌린다.
  openList() {
    if (sheet.isShown()) return;
    const pending = sheet.backPending;
    sheet.backPending = true;
    sheet.show(MAP_WEB_STAGE, 'list');
    sheet.backPending = pending;
    sheet.reopened = false;
  },

  // 아파트 창 → 목록. 창은 닫지 않고 보이는 것만 바꾼다 (map-view.js의 backToList와 같이 말풍선을 푼다).
  // 목록은 늘 옆에 보이던 것이라 보던 자리를 그대로 둔다 (모바일은 맨 위부터)
  backToList() {
    selectMarker(null);
    sheet.mode = 'list';
    sheet.apply();
  },

  // ───────── 조건 줄 (2026-10-20, 김목산) ─────────
  // 지역 칩은 이 화면에서 조건 창으로 구·동을 골라 적용한 뒤에만 보인다 (처음에는 [조건] 하나).
  // 글자는 map-view.js가 쓰는 지역 이름(#region-name)과 같다: "서구 치평동", "서구 전체"
  regionPicked: false,
  home: null, // 칩 줄 · 안내의 원래 자리 { chip: [부모, 다음 형제], info: [...] }. 모바일로 돌아갈 때 쓴다

  initFilterBar() {
    const open = document.getElementById('map-web-filter-open');
    const region = document.getElementById('map-web-region');
    if (!open || !region) return;
    open.addEventListener('click', () => openFilters());
    region.addEventListener('click', () => openFilters());

    const chip = document.querySelector('.chip-row');
    const info = document.querySelector('.info-tip');
    mapWeb.home = {
      chip: chip && [chip.parentElement, chip.nextSibling],
      info: info && [info.parentElement, info.nextSibling],
    };
    mapWeb.placeFilterBar();

    // 조건 창의 '적용'에서 지역을 바꿨는지 본다. map-view.js의 applyFilters를 감싼다 (조건 창은 부를 때마다 이 이름을 찾는다)
    const baseApply = applyFilters;
    applyFilters = (filters, extra = {}) => { // eslint-disable-line no-global-assign
      if (extra.region) mapWeb.regionPicked = true;
      baseApply(filters, extra);
      mapWeb.renderRegion();
    };
    const name = document.getElementById('region-name');
    if (name) new MutationObserver(() => mapWeb.renderRegion()).observe(name, { childList: true, characterData: true, subtree: true });

    // 실거래 기준일 (A-13). 받지 못하면 비워 둔다
    api.get('/api/data-status').then((data) => {
      if (!data || !data.trades_base_date) return;
      const [year, month, day] = data.trades_base_date.split('-'); // "2026-10-12" → "2026년 10월 12일" (다른 화면과 같은 모양)
      document.getElementById('map-web-base').textContent = `실거래 ${year}년 ${Number(month)}월 ${Number(day)}일 기준`;
    }).catch(() => {});
  },

  // 웹이면 칩 줄과 안내를 조건 줄로, 모바일이면 원래 자리로
  placeFilterBar() {
    const { home } = mapWeb;
    if (!home) return;
    const tags = document.getElementById('map-web-filter-tags');
    const end = document.getElementById('map-web-filter-end');
    const chip = document.querySelector('.chip-row');
    const info = document.querySelector('.info-tip');
    if (mapWeb.isOn()) {
      if (chip && chip.parentElement !== tags) tags.append(chip);
      if (info && info.parentElement !== end) end.append(info);
    } else {
      if (chip && home.chip && chip.parentElement !== home.chip[0]) home.chip[0].insertBefore(chip, home.chip[1]);
      if (info && home.info && info.parentElement !== home.info[0]) home.info[0].insertBefore(info, home.info[1]);
    }
  },

  renderRegion() {
    const region = document.getElementById('map-web-region');
    const name = document.getElementById('region-name');
    if (!region || !name) return;
    const text = name.textContent.trim();
    region.hidden = !mapWeb.regionPicked || !text;
    if (region.hidden || region.dataset.text === text) return;
    region.dataset.text = text;
    region.textContent = text;
    region.insertAdjacentHTML('beforeend', '<svg width="12" height="12" viewBox="0 0 24 24" aria-hidden="true" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"><path d="M6 9l6 6 6-6"/></svg>');
    region.setAttribute('aria-label', `지역 ${text}, 조건 창 열기`);
  },

  // ───────── 목록 패널 접기 ─────────
  // 접은 상태는 이 화면을 보는 동안만 기억한다 (mapWeb.folded). 새로 열면 목록이 펼쳐져 있다
  folded: false,

  // 아파트 패널도 접을 수 있다 (mapWeb.aptFolded). 접어도 고른 아파트는 그대로 두고, 다른 아파트를 열면 다시 편다
  aptFolded: false,

  initFold() {
    const button = document.getElementById('map-web-fold');
    const aptButton = document.getElementById('map-web-apt-fold');
    if (!button || !aptButton) return;
    store.set('map', { web_fold: null }); // 예전에 저장해 둔 접기 값을 지운다
    const mark = (target, folded, name) => {
      target.setAttribute('aria-expanded', String(!folded));
      target.setAttribute('aria-label', `${name} ${folded ? '펴기' : '접기'}`);
      target.querySelector('.map-web-fold__icon').textContent = folded ? '›' : '‹';
    };
    mapWeb.renderFold = () => {
      const root = document.documentElement;
      root.toggleAttribute('data-map-web-fold', mapWeb.folded);
      root.toggleAttribute('data-map-web-apt-fold', mapWeb.aptFolded);
      mark(button, mapWeb.folded, '목록');
      mark(aptButton, mapWeb.aptFolded, '아파트 창');
    };
    button.addEventListener('click', () => {
      mapWeb.folded = !mapWeb.folded;
      mapWeb.renderFold();
    });
    aptButton.addEventListener('click', () => {
      mapWeb.aptFolded = !mapWeb.aptFolded;
      mapWeb.renderFold();
    });
    mapWeb.renderFold();
    mapWeb.watchFoldTop(button, aptButton);
  },

  renderFold() {}, // initFold가 채운다

  // 아파트 패널이 열려 있으면 두 손잡이의 세로 가운데를 "아파트 정보 · 시나리오" 탭 밑줄에 맞춘다 (2026-10-20 팀장).
  // 로드뷰 · "← 목록" 줄에 따라 밑줄 높이가 달라서 잴 때마다 --map-web-fold-top에 넣는다. 패널이 없거나 접혀도 같은 높이에 둔다
  watchFoldTop(button, aptButton) {
    const panel = document.getElementById('apartment-panel');
    const tabs = panel && panel.querySelector('.apt__tabs');
    if (!tabs || typeof ResizeObserver === 'undefined') return;
    const root = document.documentElement;
    const place = () => {
      const parent = button.offsetParent;
      const shown = mapWeb.isOn() && root.dataset.mapWebPanel === 'apartment' && tabs.offsetHeight > 0 && parent;
      if (!shown) return; // 패널이 없거나 접혀 있으면 마지막으로 잰 높이 그대로 (처음에는 CSS 기본 441)
      const box = parent.getBoundingClientRect();
      const scale = box.height / parent.offsetHeight || 1; // 화면 90%(common.css zoom)를 CSS px로 되돌린다
      const line = (tabs.getBoundingClientRect().bottom - box.top) / scale;
      root.style.setProperty('--map-web-fold-top', `${Math.round(line)}px`); // 손잡이는 translateY(-50%)로 top이 세로 가운데다 (CSS)
    };
    const observer = new ResizeObserver(place);
    observer.observe(panel);
    const head = panel.querySelector('.apt__head');
    if (head) observer.observe(head); // "← 목록" 줄 · 면적 줄이 바뀌면 높이가 바뀐다
    // 로드뷰가 들어오거나 숨겨질 때 (apartment.js가 패널 맨 위에 넣는다)
    new MutationObserver(place).observe(panel, { childList: true, attributes: true, attributeFilter: ['hidden'], subtree: true });
    new MutationObserver(place).observe(root, { attributes: true, attributeFilter: ['data-map-web-panel'] });
    window.addEventListener('resize', place);
    place();
  },

  // ───────── 패널 폭이 바뀌면 지도에 알린다 ─────────
  // 카카오맵은 상자의 크기가 바뀐 것을 모른다. relayout()을 불러야 새 크기로 그린다.
  // 아파트 패널이 열리고 닫히거나 목록을 접으면 지도의 폭이 바뀐다. 고른 아파트가 있으면 줄어든 지도의 가운데로 옮긴다.
  // 고른 아파트가 없으면 보던 가운데를 그대로 둔다. relayout()은 왼쪽 위를 붙잡아 두므로, 창을 줄이거나 모바일로 바꾸면
  // 보던 곳이 오른쪽으로 밀려나 구 표시가 엉뚱한 자리에 있는 것처럼 보였다 (2026-10-20).
  // 맞추는 일은 map-view.js의 ensureMapSize가 한다 (높이가 바뀌거나 탭을 다시 열 때도 같이 본다, 2026-10-20)
  watchMapSize() {
    const box = document.getElementById('kakao-map');
    if (!box || typeof ResizeObserver === 'undefined') return;
    new ResizeObserver(() => ensureMapSize()).observe(box);
  },
};

mapWeb.init();
