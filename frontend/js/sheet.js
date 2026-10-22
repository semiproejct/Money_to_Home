// 아래 창 (P-06). 담당: 안세환
//
// 창의 단계와 열고 닫기만 맡는다. 창 안의 내용은 다른 파일이 그린다.
//   목록 (P-06 ⑤)        : list.js (김목산)가 #apt-list 안에. map-view.js가 A-05 응답을 받을 때마다 다시 그린다
//   아파트 (P-06 ⑥, ⑦)   : apartment.js가 #apartment-panel 안에
//
// 단계 (화면 설계서 7.1, 와이어프레임 2.5, guide_sehwan 4장)
//   '30'   262px. 말풍선을 누름
//   '80'   지도 영역의 90% (2026-10-21 세환. 예전 80%라 이름이 '80'). 목록 창의 하나뿐인 단계
//   'full' 내 조건 줄 바로 아래부터
//
// 창마다 쓰는 단계 (2026-10-21 세환. 예전에는 둘 다 30% → 80% → 전체 → 30%)
//   아파트 창: 30% ↔ 전체. 손잡이를 누르면 다른 쪽으로. 80%로 열라고 하면(목록의 카드) 전체로 연다
//   목록 창:   90% 하나. 무엇으로 열든(목록 보기, 결과 없음, 불러오기 실패) 90%로 열고, 손잡이를 누르면 닫는다
// 웹(1024px 이상)은 map-web.js가 창을 왼쪽 패널로 쓰고 단계를 바꾸지 않으므로, 이 단계는 모바일에서만 보인다.
// 닫기 버튼, 아래로 길게 끌기, 브라우저의 뒤로 가기로 닫는다. 뒤로 가기는 페이지를 떠나지 않고 창만 닫는다 (화면 설계서 7.1).
//
// 끌기 (FR-MAP-17, T-MAP-17, 화면 설계서 7.1과 7.6)
//   손잡이와 머리 부분(아파트 창의 머리, 목록의 머리)을 위아래로 끈다. 내용 영역은 스크롤만 된다.
//   8px 넘게 움직여야 끌기다. 그보다 적으면 누르기라서 손잡이와 머리의 버튼이 그대로 눌린다.
//   옆으로 더 많이 움직이면 끌기가 아니다 (좌우로 밀어 넘기기는 따로다. FR-MAP-18).
//   끄는 동안 창의 높이가 손가락을 따라온다. 전체보다 높이 올라가지 않는다.
//   30%보다 아래로 끌면 창이 그 높이 그대로 내려간다.
//   손을 떼면
//     30%보다 100px 넘게 내렸으면 닫는다 ("아래로 길게 끌어 닫는다")
//     빠르게 튕겼으면(1초에 500px 이상) 튕긴 쪽의 다음 단계로 간다
//     그 밖에는 가장 가까운 단계로 간다
//   끄는 동안 지도는 건드리지 않는다. 다른 단계로 가면 손잡이를 누른 것과 같이 맞추고, 처음 단계로 돌아오면 지도는 그대로다.
//
// 움직임 (0.6초, sheet.css의 --sheet-duration)
//   열 때는 아래에서 올라오고, 닫을 때는 아래로 내려간다.
//   단계가 바뀔 때(30% → 80% → 전체 → 30%)는 창의 높이가 그 시간 동안 바뀐다.
//   움직이는 동안 지도는 둘 가운데 넓은 쪽 크기를 쓴다. 그래야 창이 줄어들며 빈자리가 드러나지 않는다.
//     창이 커질 때: 지도는 그대로 두고, 다 커진 뒤에 줄인다
//     창이 작아질 때(닫을 때도): 지도를 먼저 넓히고 창이 줄어든다
//
// 창의 상태(phase)
//   'closed'   닫힘. 창이 숨어 있다
//   'opening'  올라오는 중
//   'open'     열림 (단계가 바뀌는 중이면 moving이 true)
//   'closing'  내려가는 중
//   끄는 동안은 'open'이고 moving과 dragging이 true다.
//
// 여기서는 속성만 바꾼다. 모양은 sheet.css가 맡는다.
//   .sheet[data-stage]        창의 높이와 창 안의 내용
//   .map-app[data-sheet]      지도 위 버튼과 검색 줄, 칩 줄 (열 때 바로 바뀌고, 닫을 때 바로 돌아온다)
//   .map-app[data-sheet-map]  지도의 크기 (위의 규칙대로 움직임의 처음이나 끝에 바꾼다)
//
//   sheet.show('30', 'apartment')   닫혀 있으면 열고, 열려 있으면 단계와 내용을 바꾼다
//   sheet.setStage('80')            단계만 바꾼다
//   sheet.close()                   닫는다 (뒤로 가기와 같다)
//   sheet.onChange(() => {})        상태가 바뀔 때마다 부른다. sheet.phase, stage, mode, moving을 읽는다
//   sheet.targetHeight()            지금 단계의 창이 다 움직인 뒤의 높이(px)
//   sheet.stageHeight('80')         그 단계의 창 높이(px)
//
// 예외 화면. 언제 띄울지는 아는 쪽(map-view.js)이 정해서 부른다. 이 파일은 보여 주기만 한다.
//   sheet.showEmpty()                         결과 없음 (P-05 ⑨). 목록을 30%로 연다.
//                                             빈 화면의 문장과 버튼은 list.js(김목산)가 이미 그려 둔 것을 쓴다
//   sheet.showLoadError({ message, onRetry }) 아파트를 불러오지 못함. 목록 자리에 오류와 '다시 시도'를 그리고 30%로 연다.
//                                             그리기는 list.js의 listView.renderError를 부른다.
//                                             message를 빼면 list.js의 문장 "아파트를 불러오지 못했습니다. 잠시 후 다시 시도해 주세요."

const SHEET_HISTORY_KEY = 'sheet'; // history.state에 남기는 표시. 창이 열려 있다는 뜻이다
// 단계마다 지도가 쓰는 자리의 크기 순서. 클수록 지도가 넓다. 전체 단계에서는 지도를 줄이지 않는다 (창에 다 가려진다).
const SHEET_MAP_ROOM = { 80: 1, 30: 2, full: 3 };
const SHEET_RATIO_80 = 0.9; // sheet.css의 '80' 단계 높이(90%)와 같은 값 (2026-10-21 세환. 예전 0.8)
const SHEET_LIST_STAGES = ['80']; // 목록 창의 단계. 90% 하나 (2026-10-21 세환)
const SHEET_APT_STAGES = ['30', 'full']; // 아파트 창의 단계. 낮은 것부터. 80%는 쓰지 않는다 (2026-10-21 세환)
// 끌기 (화면 설계서 7.1, 7.6). 손잡이와 머리 부분에서만 받는다. 목록의 머리는 김목산의 list.js가 그린다.
const SHEET_DRAG_AREA = '.sheet__handle, .apt__head, .list__head';
const SHEET_DRAG_START = 8; // 이만큼(px) 움직여야 끌기로 본다. 그보다 적으면 누르기다
const SHEET_CLOSE_DISTANCE = 100; // 30%보다 이만큼(px) 넘게 내리고 떼면 닫는다
const SHEET_FLICK_SPEED = 0.5; // 1ms에 이만큼(px), 곧 1초에 500px 넘게 움직이다 떼면 튕긴 것으로 본다
const SHEET_FLICK_TIME = 100; // 손을 떼기 전 이 시간(ms) 동안의 움직임으로 빠르기를 잰다

const sheet = {
  stage: null, // '30' | '80' | 'full' | null
  shownMode: null, // 지금 보이는 내용 ('list' | 'apartment'). 닫혀 있으면 null. 바뀌면 맨 위로 (apply)
  topPending: null, // 맨 위로 보내야 하는데 높이가 0이라(30% 단계) 아직 못 보낸 스크롤 요소. 높이가 생기면 apply가 보낸다
  mode: null, // 'list' | 'apartment' | null
  phase: 'closed', // 'closed' | 'opening' | 'open' | 'closing'
  moving: false, // 올라오거나 높이가 바뀌는 중인가 (끄는 중에도 true)
  dragging: false, // 손잡이나 머리를 끄는 중인가
  backPending: false, // close()가 기록을 되돌렸고 그 popstate를 기다리는 중
  reopened: false, // 기다리는 사이에 show()로 다시 열었다
  dragFrom: null, // 끌기를 시작한 단계 (단계를 바꾸던 중에 잡았으면 null)
  suppressClick: false, // 끌기를 막 끝냈다. 손을 뗄 때 생기는 누르기를 버린다
  mapStage: null, // 지도가 지금 맞춰져 있는 단계. null이면 지도가 화면을 다 쓴다
  timer: null,
  listeners: [],

  init() {
    document.getElementById('sheet-handle').addEventListener('click', () => {
      if (!sheet.stage) return;
      const next = sheet.nextStage(sheet.stage);
      if (next) sheet.setStage(next);
      else sheet.close(); // 단계가 하나뿐인 창(목록)은 손잡이를 누르면 닫는다
    });

    // 브라우저의 뒤로 가기. 창을 열 때 남긴 기록에서 빠져나오면 창을 닫는다.
    // 닫기(close)가 기록을 되돌린 뒤 그 알림이 오기 전에 다시 열었으면(show) 닫지 않고 기록만 다시 남긴다.
    // 지역을 바꾸며 창을 닫고 곧바로 다른 아파트를 여는 경우다 (이름 검색, 비슷한 아파트).
    window.addEventListener('popstate', () => {
      if (sheet.backPending) {
        sheet.backPending = false;
        if (sheet.reopened) {
          sheet.reopened = false;
          if (sheet.isShown() && !sheet.isOwnHistory()) history.pushState({ [SHEET_HISTORY_KEY]: true }, '');
          return;
        }
      }
      if (sheet.isShown() && !sheet.isOwnHistory()) sheet.hide();
    });

    // 창이 열린 채로 새로 고치면 기록에 표시가 남아 있다. 창은 닫힌 채로 시작하므로 표시를 지운다.
    if (sheet.isOwnHistory()) history.replaceState(null, '');
    sheet.initDrag();
    sheet.apply();
  },

  isOwnHistory: () => Boolean(history.state && history.state[SHEET_HISTORY_KEY]),
  // 스크롤 요소를 맨 위로. 높이가 0인 요소는 크롬이 0을 무시하고 커질 때 앞 자리를 되살리므로, 높이가 생기면 다시 한다
  scrollToTop(scroller) {
    scroller.scrollTop = 0;
    sheet.topPending = scroller.clientHeight > 0 ? null : scroller;
  },

  isShown: () => sheet.phase === 'opening' || sheet.phase === 'open',

  // 그 내용(mode)이 쓰는 단계. 낮은 것부터
  stagesFor: (mode) => (mode === 'apartment' ? SHEET_APT_STAGES : SHEET_LIST_STAGES),
  // 그 내용에 없는 단계는 그 내용의 가장 높은 단계로. 아파트 창의 80%는 전체로, 목록 창의 30% · 전체는 90%로
  fitStage(stage, mode) {
    const stages = sheet.stagesFor(mode);
    return stages.includes(stage) ? stage : stages[stages.length - 1];
  },
  // 손잡이를 누르면 갈 단계. 맨 위에서 누르면 맨 아래로. 단계가 하나뿐이면 null (닫는다)
  nextStage(stage) {
    const stages = sheet.stagesFor(sheet.mode);
    if (stages.length < 2) return null;
    const index = stages.indexOf(stage);
    return stages[(index + 1) % stages.length];
  },

  // 움직이는 시간(ms). sheet.css의 --sheet-duration을 읽는다.
  // 움직임을 줄이도록 설정했으면 0이다 (바로 열리고, 바로 바뀌고, 바로 닫힌다).
  duration() {
    if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) return 0;
    const value = getComputedStyle(document.body).getPropertyValue('--sheet-duration').trim();
    const number = parseFloat(value);
    if (!(number >= 0)) return 0;
    return value.endsWith('ms') ? number : number * 1000;
  },

  // 지금 단계의 창이 다 움직인 뒤의 높이(px). 움직이는 동안의 높이가 아니다.
  targetHeight() {
    return sheet.stageHeight(sheet.stage);
  },

  // 그 단계의 창 높이(px). sheet.css의 높이와 같은 값이다.
  stageHeight(stage) {
    const area = document.querySelector('.map-area').clientHeight;
    if (stage === '30') return parseFloat(getComputedStyle(document.body).getPropertyValue('--sheet-height-30'));
    if (stage === '80') return area * SHEET_RATIO_80;
    // 아파트 창의 전체는 내 조건 줄 뒤까지 올라간다 (로드뷰가 줄 아래로 살짝 들어간다, new-style.css)
    if (sheet.mode === 'apartment') return document.querySelector('.map-app').clientHeight;
    return area;
  },

  // 닫혀 있으면(내려가는 중도) 아래에서 올라오게 연다. 열려 있으면 단계와 내용을 바꾼다.
  // 기록은 열 때 하나만 남긴다. 그래서 몇 번을 바꿔도 뒤로 가기 한 번이면 창이 닫힌다.
  show(stage, mode) {
    stage = sheet.fitStage(stage, mode);
    if (sheet.backPending) sheet.reopened = true; // 닫기가 아직 끝나지 않았다. popstate에서 닫지 않는다
    else if (!sheet.isOwnHistory()) history.pushState({ [SHEET_HISTORY_KEY]: true }, '');
    if (sheet.isShown()) {
      sheet.mode = mode;
      if (sheet.stage === stage) sheet.apply();
      else sheet.changeStage(stage);
      return;
    }
    sheet.clearDrag(); // 끌어 닫던 창이 다 내려가기 전에 다시 연 경우
    sheet.stage = stage;
    sheet.mode = mode;
    sheet.phase = 'opening';
    sheet.mapStage = null; // 올라오는 동안 지도는 화면을 다 쓴다
    sheet.run('sheet--opening', () => {
      sheet.phase = 'open';
      sheet.mapStage = sheet.stage;
    });
  },

  setStage(stage) {
    stage = sheet.fitStage(stage, sheet.mode);
    if (!sheet.isShown() || sheet.stage === stage) return;
    sheet.changeStage(stage);
  },

  // 단계를 바꾼다. 창의 높이는 CSS의 transition이 0.6초 동안 바꾼다.
  // 지도가 넓어지는 쪽이면 바로 넓히고, 좁아지는 쪽이면 창이 다 커진 뒤에 줄인다.
  changeStage(stage) {
    sheet.stage = stage;
    if (sheet.phase === 'opening') {
      sheet.apply(); // 올라오는 중이면 높이만 바꾼다. 다 올라오면 그 단계로 지도를 맞춘다
      return;
    }
    const current = sheet.mapStage || 'full';
    if (SHEET_MAP_ROOM[stage] >= SHEET_MAP_ROOM[current]) sheet.mapStage = stage;
    sheet.run(null, () => {
      sheet.mapStage = sheet.stage;
    });
  },

  // 닫기 버튼. 열 때 남긴 기록을 되돌려(뒤로 가기) 닫는다. 기록이 어긋나 있으면 바로 닫는다.
  close() {
    if (!sheet.isShown()) return;
    if (sheet.isOwnHistory()) {
      sheet.backPending = true;
      sheet.reopened = false;
      history.back(); // popstate에서 hide()가 불린다
    } else sheet.hide();
  },

  // 아래로 내려가게 닫는다. 지도는 먼저 화면을 다 쓰게 되돌린다. 다 내려가면 숨기고 비운다.
  hide() {
    if (!sheet.isShown()) return;
    sheet.phase = 'closing';
    sheet.mapStage = null;
    sheet.run('sheet--closing', () => {
      sheet.phase = 'closed';
      sheet.stage = null;
      sheet.mode = null;
      sheet.clearDrag();
    });
  },

  // ───────── 끌기 (FR-MAP-17) ─────────

  // 손잡이와 머리 부분의 누름, 움직임, 뗌을 받는다. 창 전체에서 받고 누른 곳을 본다
  // (목록의 머리는 list.js가 다시 그릴 때마다 새로 생기기 때문이다).
  initDrag() {
    const box = document.getElementById('sheet');
    let drag = null; // { id, x, y, startHeight, dragging, sideways, samples }

    box.addEventListener('pointerdown', (event) => {
      if (drag || sheet.phase !== 'open') return;
      if (event.pointerType === 'mouse' && event.button !== 0) return;
      if (!event.target.closest(SHEET_DRAG_AREA)) return;
      drag = { id: event.pointerId, x: event.clientX, y: event.clientY, startHeight: 0, dragging: false, sideways: false, samples: [] };
    });

    window.addEventListener('pointermove', (event) => {
      if (!drag || event.pointerId !== drag.id || drag.sideways) return;
      const dx = event.clientX - drag.x;
      const dy = event.clientY - drag.y;
      if (!drag.dragging) {
        if (Math.abs(dx) < SHEET_DRAG_START && Math.abs(dy) < SHEET_DRAG_START) return;
        if (Math.abs(dx) > Math.abs(dy)) {
          drag.sideways = true; // 옆으로 민 것. 끌기도 누르기도 아니다
          return;
        }
        drag.dragging = true;
        drag.startHeight = box.getBoundingClientRect().height; // 움직이는 중이었으면 그때의 높이
        box.setPointerCapture(event.pointerId); // 손가락이 창 밖으로 나가도 계속 받는다
        sheet.startDrag();
      }
      event.preventDefault(); // 끄는 동안 글자가 골라지지 않게 한다
      drag.samples.push({ y: event.clientY, t: event.timeStamp });
      sheet.moveDrag(drag.startHeight - dy);
    });

    // 뗌. 누르기였으면 아무것도 하지 않는다 (버튼이 눌린다). 취소(pointercancel)는 빠르기 없이 뗀 것으로 본다.
    const release = (event) => {
      if (!drag || event.pointerId !== drag.id) return;
      const done = drag;
      drag = null;
      if (!done.dragging && !done.sideways) return; // 누르기
      sheet.suppressClick = true;
      setTimeout(() => {
        sheet.suppressClick = false;
      }, 0);
      if (!done.dragging) return; // 옆으로 민 것
      done.samples.push({ y: event.clientY, t: event.timeStamp });
      const speed = event.type === 'pointercancel' ? 0 : sheet.dragSpeed(done.samples);
      sheet.endDrag(done.startHeight - (event.clientY - done.y), speed);
    };
    // 뗌은 페이지 전체(window)에서 받는다. 창 밖이나 화면 밖에서 떼면 창이 받지 못할 때가 있다.
    window.addEventListener('pointerup', release, true);
    window.addEventListener('pointercancel', release, true);

    // 끌기를 끝내거나 옆으로 밀고 뗀 손이 무엇도 누르지 않게 한다.
    // 창 밖에서 손을 떼면 누른 곳이 창 밖(내 조건 줄 등)이 되어 "바깥을 누르면 닫기"(map-view.js)가 창을 닫으므로,
    // 창이 아니라 페이지 전체(window)에서 가장 먼저 받아 버린다.
    window.addEventListener('click', (event) => {
      if (!sheet.suppressClick) return;
      event.preventDefault();
      event.stopPropagation();
    }, true);
  },

  // 손을 떼기 전 SHEET_FLICK_TIME 동안의 빠르기(px/ms). 아래로 움직였으면 +, 위로면 -
  dragSpeed(samples) {
    const last = samples[samples.length - 1];
    const recent = samples.filter((sample) => last.t - sample.t <= SHEET_FLICK_TIME);
    const first = recent[0];
    if (last.t - first.t <= 0) return 0;
    return (last.y - first.y) / (last.t - first.t);
  },

  // 끌기를 시작한다. 단계를 바꾸던 중이면 멈춘다.
  // 지도는 건드리지 않고 알리지도 않는다. 알리면 map-view.js가 고른 아파트를 가운데로 다시 옮겨서,
  // 사용자가 옮겨 둔 지도가 끄는 순간 움직인다 (2026-10-14 확인).
  startDrag() {
    sheet.dragFrom = sheet.moving ? null : sheet.stage; // 단계를 바꾸던 중이었으면 null
    clearTimeout(sheet.timer);
    document.getElementById('sheet').classList.add('sheet--dragging');
    sheet.dragging = true;
    sheet.moving = true;
  },

  // 창의 높이를 손가락에 맞춘다. 그 창의 가장 높은 단계(아파트는 전체, 목록은 90%)보다 높이 가지 않는다.
  // 가장 낮은 단계(아파트는 30%, 목록은 90%)보다 낮으면 높이는 그대로 두고 창을 아래로 내린다 (안의 내용이 찌그러지지 않게).
  moveDrag(height) {
    const box = document.getElementById('sheet');
    const stages = sheet.stagesFor(sheet.mode);
    const low = sheet.stageHeight(stages[0]);
    const h = Math.min(height, sheet.stageHeight(stages[stages.length - 1]));
    box.style.height = `${Math.max(h, low)}px`;
    box.style.transform = h < low ? `translateY(${low - h}px)` : '';
  },

  // 손을 뗐다. 길게 내렸으면 닫고, 아니면 고른 단계로 0.6초 동안 간다 (지금 높이에서 출발한다).
  endDrag(height, speed) {
    const box = document.getElementById('sheet');
    box.classList.remove('sheet--dragging');
    sheet.dragging = false;
    const down = sheet.stageHeight(sheet.stagesFor(sheet.mode)[0]) - height; // 가장 낮은 단계(아파트 30%, 목록 90%)보다 내린 거리
    if (down > SHEET_CLOSE_DISTANCE) {
      // 내린 자리에서 이어서 내려가게 한다 (sheet.css의 sheet-down이 --sheet-drag-y에서 출발한다)
      box.style.setProperty('--sheet-drag-y', `${down}px`);
      sheet.stage = '30';
      sheet.close();
      return;
    }
    const stage = sheet.pickStage(height, speed);
    box.style.height = '';
    box.style.transform = '';
    if (stage === sheet.dragFrom) {
      // 처음 단계로 돌아간다. 높이만 0.6초 동안 돌아가고 지도는 그대로 둔다 (아무에게도 알리지 않는다)
      sheet.moving = false;
      return;
    }
    sheet.changeStage(stage); // 다른 단계로 간다. 손잡이를 누른 것과 같다 (지도도 그 단계에 맞춘다)
  },

  // 뗀 높이와 빠르기로 갈 단계를 고른다.
  // 위로 튕겼으면 지금 높이보다 높은 첫 단계, 아래로 튕겼으면 낮은 첫 단계, 아니면 가장 가까운 단계
  // 아파트 창은 30%와 전체 둘 가운데서 고른다 (stagesFor)
  pickStage(height, speed) {
    const stages = sheet.stagesFor(sheet.mode);
    const heights = stages.map((stage) => sheet.stageHeight(stage));
    if (speed <= -SHEET_FLICK_SPEED) {
      const index = heights.findIndex((h) => h > height + 1);
      return stages[index === -1 ? stages.length - 1 : index];
    }
    if (speed >= SHEET_FLICK_SPEED) {
      const lower = heights.filter((h) => h < height - 1).length;
      return stages[Math.max(lower - 1, 0)];
    }
    let best = 0;
    heights.forEach((h, index) => {
      if (Math.abs(h - height) < Math.abs(heights[best] - height)) best = index;
    });
    return stages[best];
  },

  // 끌며 붙인 높이와 위치를 지운다 (sheet.css의 단계 높이로 돌아간다)
  clearDrag() {
    const box = document.getElementById('sheet');
    box.classList.remove('sheet--dragging');
    box.style.height = '';
    box.style.transform = '';
    box.style.removeProperty('--sheet-drag-y');
    sheet.dragging = false;
  },

  // 움직임을 시작하고(className이 있으면 그 움직임을 붙인다), 끝나면 done을 부른 뒤 다시 그린다.
  // 움직이는 도중에 다시 부르면 앞의 것은 버린다 (내려가다가 다른 말풍선을 누른 경우, 손잡이를 빨리 두 번 누른 경우 등).
  run(className, done) {
    const box = document.getElementById('sheet');
    clearTimeout(sheet.timer);
    box.classList.remove('sheet--opening', 'sheet--closing');
    const ms = sheet.duration();
    sheet.moving = sheet.phase !== 'closing' && ms > 0;
    sheet.apply();
    const finish = () => {
      if (className) box.classList.remove(className);
      sheet.moving = false;
      done();
      sheet.apply();
    };
    if (ms === 0) {
      finish();
      return;
    }
    if (className) {
      void box.offsetWidth; // 같은 움직임을 처음부터 다시 하게 한다
      box.classList.add(className);
    }
    sheet.timer = setTimeout(finish, ms);
  },

  onChange(listener) {
    sheet.listeners.push(listener);
  },

  // ───────── 예외 화면 ─────────

  // 결과 없음 (P-05 ⑨). 목록 90% (2026-10-21. 예전 30%). 목록은 받은 응답(0곳)으로 list.js가 이미 그려 두었다.
  showEmpty() {
    sheet.show('80', 'list');
  },

  // 아파트를 불러오지 못함. 목록 자리에 오류 문장과 '다시 시도'를 그리고 목록 90%로 연다 (2026-10-21. 예전 30%).
  // list.js를 불러오지 않았으면 아무것도 하지 않는다.
  showLoadError({ message, onRetry } = {}) {
    if (typeof listView === 'undefined' || typeof listView.renderError !== 'function') return;
    listView.renderError(document.getElementById('apt-list'), {
      message, // undefined면 list.js의 문장
      onRetry,
      onClose: () => sheet.close(),
    });
    sheet.show('80', 'list');
  },

  apply() {
    const app = document.querySelector('.map-app');
    const box = document.getElementById('sheet');
    const { stage, mode, phase, mapStage } = sheet;

    box.hidden = phase === 'closed';
    if (phase === 'closed') delete box.dataset.stage;
    else box.dataset.stage = stage;

    if (sheet.isShown()) {
      app.dataset.sheet = stage;
      app.dataset.sheetMode = mode;
    } else {
      delete app.dataset.sheet;
      delete app.dataset.sheetMode;
    }
    if (mapStage) app.dataset.sheetMap = mapStage;
    else delete app.dataset.sheetMap;

    document.getElementById('apt-list').hidden = mode !== 'list';
    document.getElementById('apartment-panel').hidden = mode !== 'apartment';
    // 닫혀 있다가 열리거나 목록 ↔ 아파트로 바뀌면 새로 보이는 쪽을 맨 위부터 보여 준다 (2026-10-19).
    // 숨겨져 있던 요소는 스크롤이 먹지 않으므로, 보이게 된 이 자리에서 한다
    const showing = sheet.isShown() ? mode : null;
    if (showing && showing !== sheet.shownMode) {
      const scroller = showing === 'list' ? document.getElementById('apt-list') : document.querySelector('.apt__panels');
      if (scroller) sheet.scrollToTop(scroller);
    } else if (sheet.topPending && sheet.topPending.clientHeight > 0) {
      sheet.scrollToTop(sheet.topPending); // 30%에서 높이가 없던 내용이 창을 키워 보이게 됐다
    }
    sheet.shownMode = showing;
    const single = sheet.stagesFor(mode).length < 2; // 목록 창은 손잡이를 누르면 닫는다
    document.getElementById('sheet-handle').setAttribute('aria-label', single ? '창 닫기' : stage === 'full' ? '창 줄이기' : '창 키우기');

    sheet.listeners.forEach((listener) => listener());
  },
};
