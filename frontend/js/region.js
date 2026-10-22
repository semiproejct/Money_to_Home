// 지역 선택 (P-05 ⑬). 담당: 김해원
//
// 구와 동을 골라 지도를 그 지역으로 옮긴다 (FR-APT-02). 선택지는 거래 자료가 있는 구와 동만 나온다 (A-02).
// 지도 화면에 묶이지 않는다. 그릴 요소와 구·동 목록을 받아 그 안에만 그린다.
//
//   regionPicker.open(요소, regions, { gu: '서구', dong: '치평동' }, (picked) => { ... });
//     regions : GET /api/regions 의 regions
//     지금 고른 지역 : dong이 null이면 구 전체
//     picked  : { gu, dong, latitude, longitude }. "이 지역으로 이동"을 눌렀을 때 한 번 부른다.
//               위치는 그 동(또는 구)의 아파트 좌표 평균이다. 좌표가 없으면 null이다.
//   regionPicker.close();
//
// 서버에서 온 글자는 textContent로 넣는다. innerHTML을 쓰지 않는다.
//
// 버튼을 누를 때 화면이 흔들리지 않게 한다.
//   - 창은 열 때 한 번만 만든다. 누를 때는 고른 표시(aria-pressed)만 바꾼다.
//   - 구를 바꿀 때만 동 격자를 새로 채운다. 창의 높이는 CSS에서 고정해 동의 수가 달라도 변하지 않는다.

// 구를 보여 주는 순서. 목업(P-05 ⑬)의 순서다. 서버는 가나다순으로 준다. 여기에 없는 구는 뒤에 붙인다.
const REGION_GU_ORDER = ['동구', '서구', '남구', '북구', '광산구'];

const regionPicker = (() => {
  let container = null;
  let regions = [];
  let picked = { gu: null, dong: null };
  let onPick = null;
  let guRow = null;
  let dongGrid = null;

  function el(tag, className, text) {
    const node = document.createElement(tag);
    if (className) node.className = className;
    if (text !== undefined) node.textContent = text;
    return node;
  }

  const findGu = (gu) => regions.find((region) => region.gu === gu) || null;

  // 선택지 하나. data-value에 구나 동의 이름을 둔다. "○○구 전체"는 빈 글자다.
  function option(text, value, className, onClick) {
    const button = el('button', className, text);
    button.type = 'button';
    button.dataset.value = value;
    button.addEventListener('click', onClick);
    return button;
  }

  // 고른 표시만 바꾼다. 요소를 새로 만들지 않으므로 자리가 움직이지 않는다.
  function markPicked() {
    for (const button of guRow.children) {
      button.setAttribute('aria-pressed', String(button.dataset.value === picked.gu));
    }
    for (const button of dongGrid.children) {
      button.setAttribute('aria-pressed', String(button.dataset.value === (picked.dong || '')));
    }
  }

  // 고른 구의 동으로 격자를 채운다. 구를 바꿨을 때만 부른다.
  function fillDongs() {
    const region = findGu(picked.gu);
    const buttons = [];
    if (region) {
      buttons.push(option(`${region.gu} 전체`, '', 'region-sheet__dong region-sheet__dong--all', () => {
        picked = { gu: region.gu, dong: null };
        markPicked();
      }));
      for (const item of region.dongs) {
        buttons.push(option(item.dong, item.dong, 'region-sheet__dong', () => {
          picked = { gu: region.gu, dong: item.dong };
          markPicked();
        }));
      }
    }
    dongGrid.replaceChildren(...buttons);
    dongGrid.parentElement.scrollTop = 0;
  }

  function build() {
    const head = el('header', 'region-sheet__head');
    head.append(el('h2', 'region-sheet__title', '지역 선택'));
    const close = el('button', 'region-sheet__close', '×');
    close.type = 'button';
    close.setAttribute('aria-label', '닫기');
    close.addEventListener('click', api.close);
    head.append(close);

    // 구: 한 줄로 붙인 선택지
    guRow = el('div', 'region-sheet__gu');
    for (const item of regions) {
      guRow.append(option(item.gu, item.gu, 'region-sheet__gu-option', () => {
        if (picked.gu === item.gu) return;
        picked = { gu: item.gu, dong: null }; // 구를 바꾸면 동은 "전체"로 돌아간다
        fillDongs();
        markPicked();
      }));
    }

    // 동: "○○구 전체" 한 줄과 동 이름 격자. 동이 많으면 이 안에서만 위아래로 움직인다.
    dongGrid = el('div', 'region-sheet__dongs');
    const body = el('div', 'region-sheet__body');
    body.append(dongGrid);

    const go = el('button', 'button button--primary', '이 지역으로 이동');
    go.type = 'button';
    go.disabled = regions.length === 0;
    go.addEventListener('click', () => {
      const region = findGu(picked.gu);
      if (!region) return;
      const dong = region.dongs.find((item) => item.dong === picked.dong) || null;
      const place = dong || region;
      const result = { gu: region.gu, dong: dong ? dong.dong : null, latitude: place.latitude, longitude: place.longitude };
      const callback = onPick;
      api.close();
      if (callback) callback(result);
    });

    const foot = el('div', 'region-sheet__foot');
    foot.append(el('p', 'region-sheet__note', '최근 1년 거래가 있는 구와 동만 나옵니다.'), go);

    const sheet = el('div', 'region-sheet__inner');
    sheet.append(
      el('div', 'region-sheet__handle'),
      head,
      el('p', 'region-sheet__label', '구'),
      guRow,
      el('p', 'region-sheet__label', '동'),
      body,
      foot,
    );
    container.replaceChildren(sheet);
  }

  const api = {
    open(target, regionList, current, callback) {
      container = target;
      const rank = (gu) => (REGION_GU_ORDER.includes(gu) ? REGION_GU_ORDER.indexOf(gu) : REGION_GU_ORDER.length);
      regions = [...(regionList || [])].sort((a, b) => rank(a.gu) - rank(b.gu));
      const gu = findGu(current && current.gu) ? current.gu : regions[0] ? regions[0].gu : null;
      const region = findGu(gu);
      const dong = region && current && region.dongs.some((item) => item.dong === current.dong) ? current.dong : null;
      picked = { gu, dong };
      onPick = callback;
      build();
      fillDongs();
      markPicked();
      container.hidden = false;
    },

    close() {
      if (!container) return;
      container.hidden = true;
      container.replaceChildren();
      onPick = null;
    },

    isOpen: () => Boolean(container) && !container.hidden,
  };
  return api;
})();
