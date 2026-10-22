// 조건 창 (P-05 ② 조건). 담당: 김목산
//
// 면적(전용), 평균가, 준공 연도의 최소와 최대와, 자금 부족 표시를 고른다 (FR-APT-03, 09, 10, FR-MAP-15).
// 지도 화면에 묶이지 않는다. 그릴 요소를 받아 그 안에만 그린다. 고른 값은 A-05의 filters 모양으로 돌려준다.
//
//   <section id="filter-sheet" aria-label="조건" hidden></section>   (map.html. 모양은 filter.css가 붙인다)
//
//   filterSheet.open(요소, 지금 조건, (filters, { showLack }) => { ... }, { showLack: false });
//     지금 조건 : A-05의 filters. null이면 조건 없음
//                 { area_min, area_max, price_min, price_max, built_year_min, built_year_max }
//                 면적은 면적대(㎡ 정수), 평균가는 원, 준공 연도는 연도. 값이 없으면 null
//     onApply   : '적용'을 누르면 창을 닫고 한 번 부른다. 여섯 값이 모두 든 filters를 넘긴다 (없는 값은 null).
//                 둘째 값은 { showLack } — 자금 부족 표시 스위치를 켰는지
//     showLack  : 자금 부족 표시의 지금 상태. 처음에는 꺼져 있다 (CLAUDE.md). 서버에 보내는 조건이 아니라
//                 지도에 자금이 부족한 아파트를 그릴지만 정한다. 목록에는 스위치와 상관없이 나온다
//     focus     : 'region', 'area', 'price', 'year', 'lack' 중 하나면 그 항목으로 내려가 있다 (빼면 맨 위)
//     regions   : GET /api/regions 의 regions. 주면 맨 위에 "지역"(구 칩과 동 칩)이 생긴다 (2026-10-18 새 스타일)
//     region    : 지금 보는 지역 { gu, dong }. dong이 null이면 구 전체
//                 '적용'을 누를 때 지역을 바꿨으면 onApply의 둘째 값에 region: { gu, dong, latitude, longitude }가 붙는다
//   filterSheet.close();
//   filterSheet.isOpen();
//
//   // 칩에 적을 글자. 조건이 없으면 null (칩은 "면적 ▾"처럼 그대로 둔다)
//   filterSheet.label(filters, 'area', 'm2')   // "면적 59~84㎡", "면적 135㎡~"
//   filterSheet.label(filters, 'price')        // "가격 1억~3억 원", "가격 2억 원~"
//   filterSheet.label(filters, 'year')         // "준공 2020~"
//   filterSheet.isEmpty(filters)               // 조건이 하나도 없으면 true
//
// 금액은 원 정수로 돌려준다. 천만 원은 평균가 입력란에서만 쓴다 (CLAUDE.md 3).
// 평은 면적을 보여 줄 때만 쓴다. 돌려주는 값은 늘 ㎡의 면적대다.
// 서버에서 온 글자는 없다. 글자는 모두 textContent로 넣는다.

const FILTER_TEXT = {
  title: '조건',
  region: '지역',
  regionHelp: '최근 1년 거래가 있는 구와 동만 나옵니다.',
  area: '면적 (전용)',
  price: '평균가 (천만 원)',
  year: '준공 연도',
  lack: '자금 부족한 곳도 지도에 보기',
  lackHelp: '목록에는 항상 나옵니다.',
  min: '최소',
  max: '최대',
  yearMin: '예: 2000',
  yearMax: '예: 2020',
  reset: '초기화',
  apply: '적용',
  notNumber: '숫자만 입력할 수 있습니다.', // API 명세서 5장
  range: '조건의 최소와 최대를 다시 확인해 주세요.', // API 명세서 5장 (A-05 filters)
};

// 슬라이더의 양 끝. 끝에 두면 그쪽은 조건이 없다 (입력란이 빈다).
// 광주 5개 구 면적대는 15 ~ 258㎡이고 165㎡ 넘는 면적은 22개뿐이라 165에서 끊는다. 더 크면 입력란에 적는다.
const FILTER_AREA = {
  m2: { min: 0, max: 165, step: 1, unit: '㎡' },
  pyeong: { min: 0, max: 50, step: 1, unit: '평' },
};

const PYEONG_M2 = 3.3058; // 평 환산 (요구사항 부록 C, format.pyeong과 같은 값)

// 평균가 입력란의 단위. 천만 원이다. 10을 넣으면 1억 원 (1억을 10000으로 적지 않게)
const PRICE_UNIT = 10000000;

const FILTER_CLOSE_MS = 300; // 닫힐 때 내려가는 시간. filter.css의 filter-sheet-down과 같다

const filterSheet = (() => {
  let container = null;
  let onApply = null;
  let unit = 'm2';
  let inputs = {}; // area_min, area_max, price_min, price_max, built_year_min, built_year_max
  let errors = {}; // area, price, year
  let slider = null;
  let unitButtons = [];
  let lackSwitch = null; // 자금 부족 표시 스위치 (button role=switch)
  let onKey = null;
  let regionState = null; // { list, picked: { gu, dong }, start: { gu, dong }, guRow, dongGrid }

  function el(tag, className, text) {
    const node = document.createElement(tag);
    if (className) node.className = className;
    if (text !== undefined && text !== null) node.textContent = text;
    return node;
  }

  // ㎡ 면적대 ↔ 평. 평으로 적힌 범위에는 화면에 그 평으로 보이는 면적대가 모두 들게 한다 (반올림의 양 끝까지).
  const toPyeong = (m2) => Math.round(m2 / PYEONG_M2);
  const pyeongToMin = (p) => Math.max(0, Math.ceil((p - 0.5) * PYEONG_M2));
  const pyeongToMax = (p) => Math.ceil((p + 0.5) * PYEONG_M2) - 1;

  // 입력란의 글자 → 숫자. 비었으면 null, 숫자가 아니면 NaN. 쉼표는 지운다
  function readNumber(input) {
    const text = input.value.replace(/,/g, '').trim();
    if (text === '') return null;
    return /^\d+$/.test(text) ? Number(text) : NaN;
  }

  function numberInput(placeholder, label) {
    const input = el('input', 'filter-sheet__input');
    input.type = 'text';
    input.inputMode = 'numeric';
    input.autocomplete = 'off';
    input.placeholder = placeholder;
    input.setAttribute('aria-label', label);
    return input;
  }

  // 최소 ~ 최대 한 줄과 그 아래 오류 줄
  function rangeRow(key, minInput, maxInput, unitText) {
    const row = el('div', 'filter-sheet__range');
    row.append(minInput, el('span', 'filter-sheet__tilde', '~'), maxInput);
    if (unitText) row.append(el('span', 'filter-sheet__unit', unitText));
    const error = el('p', 'filter-sheet__error');
    error.setAttribute('aria-live', 'polite');
    errors[key] = error;
    return [row, error];
  }

  // 양쪽 손잡이 슬라이더. 손잡이 두 개는 겹쳐 둔 range 두 개다
  function buildSlider() {
    const wrap = el('div', 'filter-sheet__slider');
    const fill = el('div', 'filter-sheet__fill');
    const low = el('input', 'filter-sheet__thumb');
    const high = el('input', 'filter-sheet__thumb');
    low.type = 'range';
    high.type = 'range';
    low.setAttribute('aria-label', '면적 최소 (끌기)');
    high.setAttribute('aria-label', '면적 최대 (끌기)');
    wrap.append(el('div', 'filter-sheet__track'), fill, low, high);

    const range = () => FILTER_AREA[unit];
    const paint = () => {
      const { min, max } = range();
      const left = ((Number(low.value) - min) / (max - min)) * 100;
      const right = ((Number(high.value) - min) / (max - min)) * 100;
      fill.style.left = `${left}%`;
      fill.style.width = `${right - left}%`;
      // 두 손잡이가 오른쪽 끝에서 겹치면 최소 손잡이를 위로 올려 잡을 수 있게 한다
      low.style.zIndex = left > 50 ? '1' : '';
    };
    // 입력란 → 슬라이더. 빈 칸은 끝으로, 범위 밖은 끝에 붙인다
    const sync = () => {
      const { min, max, step } = range();
      [low, high].forEach((thumb) => Object.assign(thumb, { min, max, step }));
      const a = readNumber(inputs.area_min);
      const b = readNumber(inputs.area_max);
      low.value = Number.isFinite(a) && a !== null ? Math.min(Math.max(a, min), max) : min;
      high.value = Number.isFinite(b) && b !== null ? Math.min(Math.max(b, min), max) : max;
      paint();
    };
    // 슬라이더 → 입력란. 끝에 두면 그쪽은 빈다. 두 손잡이는 서로 넘지 않는다
    const onSlide = (thumb) => {
      const { min, max } = range();
      if (Number(low.value) > Number(high.value)) {
        if (thumb === low) low.value = high.value;
        else high.value = low.value;
      }
      inputs.area_min.value = Number(low.value) === min ? '' : low.value;
      inputs.area_max.value = Number(high.value) === max ? '' : high.value;
      setError('area', null);
      paint();
    };
    low.addEventListener('input', () => onSlide(low));
    high.addEventListener('input', () => onSlide(high));
    return { wrap, sync };
  }

  function setError(key, message) {
    errors[key].textContent = message || '';
    errors[key].classList.remove('filter-sheet__error--read');
    errors[key].parentElement.classList.toggle('filter-sheet__section--error', Boolean(message));
    if (key === 'price' && !message) paintPriceRead();
  }

  // 평균가 입력란 아래에 넣은 값을 원으로 읽어 준다. "1억 원 ~ 3억 원". 오류 문구가 없을 때만 그 자리에
  function paintPriceRead() {
    const a = readNumber(inputs.price_min);
    const b = readNumber(inputs.price_max);
    if (Number.isNaN(a) || Number.isNaN(b) || (a === null && b === null)) {
      errors.price.textContent = '';
      return;
    }
    const won = (v) => (v === null ? '' : format.won(v * PRICE_UNIT));
    errors.price.textContent = `${won(a)} ~ ${won(b)}`.trim();
    errors.price.classList.add('filter-sheet__error--read');
  }

  // ㎡ / 평 고르기. 바꾸면 입력란의 숫자도 그 단위로 바꾼다.
  // 평으로 바꿨다가 고치지 않고 ㎡로 돌아오면 처음 ㎡ 값을 그대로 돌려놓는다 (59 → 18평 → 58이 되지 않게)
  let beforePyeong = null; // { m2: [최소 글자, 최대 글자], pyeong: [최소 글자, 최대 글자] }
  function setUnit(next) {
    if (next === unit) return;
    const a = readNumber(inputs.area_min);
    const b = readNumber(inputs.area_max);
    const convert = (value, toMin) => {
      if (value === null || Number.isNaN(value)) return value;
      if (next === 'pyeong') return toPyeong(value);
      return toMin ? pyeongToMin(value) : pyeongToMax(value);
    };
    const m2Text = [inputs.area_min.value, inputs.area_max.value];
    const shown = [inputs.area_min.value, inputs.area_max.value];
    unit = next;
    const ca = convert(a, true);
    const cb = convert(b, false);
    if (!Number.isNaN(ca)) inputs.area_min.value = ca === null ? '' : ca;
    if (!Number.isNaN(cb)) inputs.area_max.value = cb === null ? '' : cb;
    if (next === 'pyeong') {
      beforePyeong = { m2: m2Text, pyeong: [inputs.area_min.value, inputs.area_max.value] };
    } else {
      if (beforePyeong && beforePyeong.pyeong[0] === shown[0] && beforePyeong.pyeong[1] === shown[1]) {
        [inputs.area_min.value, inputs.area_max.value] = beforePyeong.m2;
      }
      beforePyeong = null;
    }
    unitButtons.forEach((button) => button.setAttribute('aria-pressed', String(button.dataset.unit === unit)));
    areaUnitText.textContent = FILTER_AREA[unit].unit;
    slider.sync();
  }

  let areaUnitText = null;

  function section(key, labelText, extra) {
    const box = el('section', 'filter-sheet__section');
    box.dataset.filter = key;
    const head = el('div', 'filter-sheet__label-row');
    head.append(el('h3', 'filter-sheet__label', labelText));
    if (extra) head.append(extra);
    box.append(head);
    return box;
  }

  // 자금 부족 표시 한 줄. 줄 전체를 눌러도 켜고 끈다
  function lackSection(on) {
    const box = el('section', 'filter-sheet__section filter-sheet__section--lack');
    box.dataset.filter = 'lack';
    lackSwitch = el('button', 'filter-sheet__lack');
    lackSwitch.type = 'button';
    lackSwitch.setAttribute('role', 'switch');
    lackSwitch.setAttribute('aria-checked', String(on));
    const text = el('span', 'filter-sheet__lack-text');
    text.append(el('span', 'filter-sheet__label', FILTER_TEXT.lack), el('span', 'filter-sheet__lack-help', FILTER_TEXT.lackHelp));
    const knob = el('span', 'filter-sheet__switch');
    knob.setAttribute('aria-hidden', 'true');
    knob.append(el('span', 'filter-sheet__switch-knob'));
    lackSwitch.append(text, knob);
    lackSwitch.addEventListener('click', () => {
      lackSwitch.setAttribute('aria-checked', String(lackSwitch.getAttribute('aria-checked') !== 'true'));
    });
    box.append(lackSwitch);
    return box;
  }

  // 지역 (구와 동). 구 칩 한 줄(옆으로 밀기)과 그 구의 동 칩. 고른 표시만 바꾸고 '적용'을 누를 때 옮긴다
  const REGION_ORDER = ['동구', '서구', '남구', '북구', '광산구']; // region.js와 같은 순서
  function regionSection(list, current) {
    const rank = (gu) => (REGION_ORDER.includes(gu) ? REGION_ORDER.indexOf(gu) : REGION_ORDER.length);
    const sorted = [...list].sort((a, b) => rank(a.gu) - rank(b.gu));
    const find = (gu) => sorted.find((item) => item.gu === gu) || null;
    const startGu = current && find(current.gu) ? current.gu : sorted[0] ? sorted[0].gu : null;
    const startDong = current && find(startGu) && find(startGu).dongs.some((d) => d.dong === current.dong) ? current.dong : null;
    regionState = { list: sorted, find, picked: { gu: startGu, dong: startDong }, start: { gu: startGu, dong: startDong } };

    const box = section('region', FILTER_TEXT.region);
    const guRow = el('div', 'filter-sheet__gu');
    guRow.setAttribute('role', 'group');
    guRow.setAttribute('aria-label', '구');
    const dongGrid = el('div', 'filter-sheet__dongs');
    dongGrid.setAttribute('role', 'group');
    dongGrid.setAttribute('aria-label', '동');

    const chip = (text, value, onClick) => {
      const button = el('button', 'filter-sheet__pick', text);
      button.type = 'button';
      button.dataset.value = value;
      button.addEventListener('click', onClick);
      return button;
    };
    const mark = () => {
      for (const b of guRow.children) b.setAttribute('aria-pressed', String(b.dataset.value === regionState.picked.gu));
      for (const b of dongGrid.children) b.setAttribute('aria-pressed', String(b.dataset.value === (regionState.picked.dong || '')));
    };
    const fillDongs = () => {
      const region = find(regionState.picked.gu);
      const buttons = [];
      if (region) {
        buttons.push(chip(`${region.gu} 전체`, '', () => { regionState.picked = { gu: region.gu, dong: null }; mark(); }));
        region.dongs.forEach((item) => buttons.push(chip(item.dong, item.dong, () => {
          regionState.picked = { gu: region.gu, dong: item.dong };
          mark();
        })));
      }
      dongGrid.replaceChildren(...buttons);
      dongGrid.scrollTop = 0;
    };
    sorted.forEach((item) => guRow.append(chip(item.gu, item.gu, () => {
      if (regionState.picked.gu === item.gu) return;
      regionState.picked = { gu: item.gu, dong: null }; // 구를 바꾸면 동은 "전체"로
      fillDongs();
      mark();
    })));
    fillDongs();
    mark();
    // 고른 동이 보이게 동 칩 상자 안에서만 내린다
    requestAnimationFrame(() => {
      const on = dongGrid.querySelector('[aria-pressed="true"]');
      if (on) dongGrid.scrollTop = on.offsetTop - dongGrid.offsetTop - 8;
    });
    box.append(guRow, dongGrid, el('p', 'filter-sheet__help', FILTER_TEXT.regionHelp));
    return box;
  }

  // 지역을 바꿨으면 { gu, dong, latitude, longitude }, 그대로면 null
  function pickedRegion() {
    if (!regionState) return null;
    const { picked, start, find } = regionState;
    if (picked.gu === start.gu && (picked.dong || null) === (start.dong || null)) return null;
    const region = find(picked.gu);
    if (!region) return null;
    const dong = region.dongs.find((item) => item.dong === picked.dong) || null;
    const place = dong || region;
    return { gu: region.gu, dong: dong ? dong.dong : null, latitude: place.latitude, longitude: place.longitude };
  }

  function build(current, showLack, regionOptions) {
    errors = {};
    beforePyeong = null;
    regionState = null;
    const head = el('header', 'filter-sheet__head');
    head.append(el('h2', 'filter-sheet__title', FILTER_TEXT.title));
    const close = el('button', 'filter-sheet__close', '×');
    close.type = 'button';
    close.setAttribute('aria-label', '닫기');
    close.addEventListener('click', api.close);
    head.append(close);

    inputs = {
      area_min: numberInput(FILTER_TEXT.min, '면적 최소'),
      area_max: numberInput(FILTER_TEXT.max, '면적 최대'),
      price_min: numberInput(FILTER_TEXT.min, '평균가 최소 (천만 원)'),
      price_max: numberInput(FILTER_TEXT.max, '평균가 최대 (천만 원)'),
      built_year_min: numberInput(FILTER_TEXT.yearMin, '준공 연도 시작'),
      built_year_max: numberInput(FILTER_TEXT.yearMax, '준공 연도 끝'),
    };
    inputs.built_year_min.maxLength = 4;
    inputs.built_year_max.maxLength = 4;

    // 지금 조건을 입력란에 넣는다. 면적은 고른 단위로, 금액은 천만 원으로.
    // 천만 원으로 나눠떨어지지 않는 값(예전에 만 원으로 넣은 것)은 범위가 좁아지지 않게 최소는 내리고 최대는 올린다
    const put = (input, value) => { input.value = value === null || value === undefined ? '' : value; };
    const f = current || {};
    const area = (v) => (v === null || v === undefined ? null : unit === 'pyeong' ? toPyeong(v) : v);
    put(inputs.area_min, area(f.area_min));
    put(inputs.area_max, area(f.area_max));
    if (unit === 'pyeong') {
      const text = (v) => (v === null || v === undefined ? '' : String(v));
      beforePyeong = { m2: [text(f.area_min), text(f.area_max)], pyeong: [inputs.area_min.value, inputs.area_max.value] };
    }
    put(inputs.price_min, f.price_min === null || f.price_min === undefined ? null : Math.floor(f.price_min / PRICE_UNIT));
    put(inputs.price_max, f.price_max === null || f.price_max === undefined ? null : Math.ceil(f.price_max / PRICE_UNIT));
    put(inputs.built_year_min, f.built_year_min);
    put(inputs.built_year_max, f.built_year_max);

    // 면적: ㎡/평, 슬라이더, 입력란
    const toggle = el('div', 'filter-sheet__unit-toggle');
    toggle.setAttribute('role', 'group');
    toggle.setAttribute('aria-label', '면적 단위');
    unitButtons = [['m2', '㎡'], ['pyeong', '평']].map(([value, text]) => {
      const button = el('button', 'filter-sheet__unit-option', text);
      button.type = 'button';
      button.dataset.unit = value;
      button.setAttribute('aria-pressed', String(value === unit));
      button.addEventListener('click', () => setUnit(value));
      return button;
    });
    toggle.append(...unitButtons);

    const areaBox = section('area', FILTER_TEXT.area, toggle);
    slider = buildSlider();
    const [areaRow, areaError] = rangeRow('area', inputs.area_min, inputs.area_max, FILTER_AREA[unit].unit);
    areaUnitText = areaRow.querySelector('.filter-sheet__unit');
    areaBox.append(slider.wrap, areaRow, areaError);
    [inputs.area_min, inputs.area_max].forEach((input) => input.addEventListener('input', () => {
      setError('area', null);
      slider.sync();
    }));

    const priceBox = section('price', FILTER_TEXT.price);
    priceBox.append(...rangeRow('price', inputs.price_min, inputs.price_max));
    [inputs.price_min, inputs.price_max].forEach((input) => input.addEventListener('input', () => setError('price', null)));
    paintPriceRead();

    const yearBox = section('year', FILTER_TEXT.year);
    yearBox.append(...rangeRow('year', inputs.built_year_min, inputs.built_year_max));
    [inputs.built_year_min, inputs.built_year_max].forEach((input) => input.addEventListener('input', () => setError('year', null)));

    const body = el('div', 'filter-sheet__body');
    body.append(areaBox, priceBox, yearBox, lackSection(showLack));
    if (regionOptions.regions && regionOptions.regions.length) body.prepend(regionSection(regionOptions.regions, regionOptions.region));

    const reset = el('button', 'button filter-sheet__reset', FILTER_TEXT.reset);
    reset.type = 'button';
    reset.addEventListener('click', () => {
      Object.values(inputs).forEach((input) => { input.value = ''; });
      ['area', 'price', 'year'].forEach((key) => setError(key, null));
      lackSwitch.setAttribute('aria-checked', 'false'); // 처음 상태(꺼짐)로
      slider.sync();
    });
    const apply = el('button', 'button button--primary filter-sheet__apply', FILTER_TEXT.apply);
    apply.type = 'button';
    apply.addEventListener('click', submit);

    const foot = el('div', 'filter-sheet__foot');
    foot.append(reset, apply);

    const sheet = el('div', 'filter-sheet__inner');
    sheet.append(el('div', 'filter-sheet__handle'), head, body, foot);
    container.replaceChildren(sheet);
    slider.sync();
  }

  // 입력란을 읽어 filters를 만든다. 잘못된 값이 있으면 그 항목에 문구를 적고 null
  function read() {
    let ok = true;
    const pair = (key, minInput, maxInput) => {
      const a = readNumber(minInput);
      const b = readNumber(maxInput);
      if (Number.isNaN(a) || Number.isNaN(b)) {
        setError(key, FILTER_TEXT.notNumber);
        ok = false;
      } else if (a !== null && b !== null && a > b) {
        setError(key, FILTER_TEXT.range);
        ok = false;
      }
      return [a, b];
    };
    const [areaMin, areaMax] = pair('area', inputs.area_min, inputs.area_max);
    const [priceMin, priceMax] = pair('price', inputs.price_min, inputs.price_max);
    const [yearMin, yearMax] = pair('year', inputs.built_year_min, inputs.built_year_max);
    if (!ok) return null;

    const pyeong = unit === 'pyeong';
    // 평으로 보고만 있고 고치지 않았으면 처음 ㎡ 값을 그대로 쓴다
    const untouched = pyeong && beforePyeong
      && beforePyeong.pyeong[0] === inputs.area_min.value && beforePyeong.pyeong[1] === inputs.area_max.value;
    const m2 = (text) => (text === '' ? null : Number(text));
    return {
      area_min: untouched ? m2(beforePyeong.m2[0]) : areaMin === null ? null : pyeong ? pyeongToMin(areaMin) : areaMin,
      area_max: untouched ? m2(beforePyeong.m2[1]) : areaMax === null ? null : pyeong ? pyeongToMax(areaMax) : areaMax,
      price_min: priceMin === null ? null : priceMin * PRICE_UNIT,
      price_max: priceMax === null ? null : priceMax * PRICE_UNIT,
      built_year_min: yearMin,
      built_year_max: yearMax,
    };
  }

  function submit() {
    const filters = read();
    if (!filters) {
      const first = container.querySelector('.filter-sheet__section--error input');
      if (first) first.focus();
      return;
    }
    const callback = onApply;
    const showLack = lackSwitch.getAttribute('aria-checked') === 'true';
    const region = pickedRegion();
    api.close();
    if (callback) callback(filters, region ? { showLack, region } : { showLack });
  }

  let closing = null; // 내려가는 중이면 다 내려간 뒤 비울 타이머

  // 다 내려간 창을 숨기고 비운다
  function finishClose() {
    clearTimeout(closing);
    closing = null;
    container.classList.remove('filter-sheet--closing');
    container.hidden = true;
    container.replaceChildren();
  }

  const api = {
    open(target, current, callback, options = {}) {
      if (container && container !== target) {
        api.close();
        finishClose();
      }
      if (closing) finishClose(); // 내려가는 중에 다시 열면 바로 새로 연다
      container = target;
      container.classList.add('filter-sheet');
      onApply = callback;
      unit = (store.get('map').area_unit === 'pyeong') ? 'pyeong' : 'm2';
      build(current, options.showLack === true, { regions: options.regions, region: options.region });
      container.hidden = false;

      // 누른 칩의 항목으로 내려가 있게 한다. 창 안의 목록만 움직인다.
      // scrollIntoView는 지도 화면 전체까지 밀어 올리므로 쓰지 않는다
      const focus = options.focus && container.querySelector(`.filter-sheet__section[data-filter="${options.focus}"]`);
      const body = container.querySelector('.filter-sheet__body');
      if (focus && body) body.scrollTop = focus.offsetTop - body.offsetTop;

      if (onKey) document.removeEventListener('keydown', onKey);
      onKey = (event) => { if (event.key === 'Escape') api.close(); };
      document.addEventListener('keydown', onKey);
    },

    // 아래로 내려간 뒤 사라진다. 움직임을 줄이는 설정이면 바로 사라진다
    close() {
      if (!container || container.hidden || closing) return;
      onApply = null;
      if (onKey) document.removeEventListener('keydown', onKey);
      onKey = null;
      if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
        finishClose();
        return;
      }
      container.classList.add('filter-sheet--closing');
      closing = setTimeout(finishClose, FILTER_CLOSE_MS);
    },

    // 내려가는 중이면 닫힌 것으로 본다
    isOpen: () => Boolean(container) && !container.hidden && !closing,

    isEmpty: (filters) => !filters || Object.values(filters).every((value) => value === null || value === undefined),

    // 칩의 글자. "면적 59~84㎡", "면적 135㎡~", "가격 ~3억 원", "준공 2020~". 조건이 없으면 null
    label(filters, key, areaUnit = 'm2') {
      if (!filters) return null;
      const pick = {
        area: ['area_min', 'area_max', '면적'],
        price: ['price_min', 'price_max', '가격'],
        year: ['built_year_min', 'built_year_max', '준공'],
      }[key];
      if (!pick) return null;
      const [minKey, maxKey, name] = pick;
      const a = filters[minKey];
      const b = filters[maxKey];
      const has = (v) => v !== null && v !== undefined;
      if (!has(a) && !has(b)) return null;
      // 양쪽: "59~84㎡", 최소만: "135㎡~", 최대만: "~84㎡" (와이어프레임 P-05 ⑨)
      const span = (show, tail) => {
        if (has(a) && has(b)) return `${name} ${show(a)}~${show(b)}${tail}`;
        return has(a) ? `${name} ${show(a)}${tail}~` : `${name} ~${show(b)}${tail}`;
      };
      if (key === 'area') {
        const pyeong = areaUnit === 'pyeong';
        return span((v) => (pyeong ? toPyeong(v) : v), pyeong ? '평' : '㎡');
      }
      if (key === 'price') return span((v) => format.won(v).replace(/ ?원$/, ''), ' 원'); // "가격 1억~3억 원"
      return span((v) => v, '');
    },
  };
  return api;
})();
