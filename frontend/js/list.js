// 목록 (P-06 ⑤ 목록 80%). 담당: 김목산
//
// 지도 화면에 묶이지 않는다. 그릴 요소를 받아 그 안에만 그린다.
// map.html(안세환)은 고치지 않는다. 세환과 맞춘 자리는 id="apt-list" 하나다.
//
//   const el = document.getElementById('apt-list');
//
//   // A-05 응답으로 그리기만 한다. 지도가 이미 A-05를 불렀으면 그 응답을 넘긴다.
//   listView.render(el, result);
//   listView.render(el, result, {
//     where: { gu: '서구', dong: '치평동' },        // 머리의 "서구 치평동 · 23곳"
//     sort: 'category',                              // 지금 정렬. 머리 오른쪽의 "구분순 ▾" (없으면 구분순)
//     onSort: (sort) => { ... },                     // 정렬을 고름. A-05를 sort로 다시 불러 그린다. 없으면 정렬 버튼이 없다
//     onSelect: (apartment, areaIndex) => { ... },  // 카드를 누름. 80% 아파트 창을 연다 (세환)
//     onClose: () => { ... },                        // 닫기
//     onResetFilters: () => { ... },                 // 결과 없음의 '조건 초기화'. 없으면 버튼이 없다
//     onChangeFilters: () => { ... },                // 결과 없음의 '조건 바꾸기' (조건 창을 연다). 없으면 버튼이 없다
//   });
//
//   // 불러오는 중 (P-05 ⑯, FR-COMMON-10). 회색 자리표시 카드 3장. where가 있으면 머리에 지역 이름, onClose가 있으면 닫기
//   listView.renderLoading(el, { where: { gu: '서구', dong: '치평동' }, onClose: () => { ... } });
//   // 결과가 오면 render나 renderError로 바꿔 그리면 된다
//
//   // 불러오지 못했을 때. message가 없으면 "아파트를 불러오지 못했습니다…", onRetry가 있으면 '다시 시도', onClose가 있으면 닫기
//   listView.renderError(el, { message, onRetry: () => { ... }, onClose: () => { ... } });
//
//   // A-05를 불러 그리고, 받은 응답을 돌려준다. 정렬은 store의 map.sort를 쓰고, 바꾸면 알아서 다시 부른다.
//   const result = await listView.load(el, { gu: '서구', dong: '치평동' }, { onSelect, onClose });
//
// 숫자는 서버(A-05)가 준 것을 그대로 보여 준다. 여기서 계산하지 않는다 (NFR-13).
// 서버에서 온 글자는 textContent로 넣는다. innerHTML을 쓰지 않는다.
// 순서는 서버가 준 순서 그대로다. 정렬은 서버(A-05의 sort)가 한다 (와이어프레임 B1, B2).
// 면적 단위(평)는 아직 없다.

const LIST_GROUPS = [
  { key: 'now', title: '지금 목표할 수 있는 곳', chip: '지금', badge: '지금 가능' },
  { key: 'within', title: '목표 기간 안에 가능한 곳', chip: '기간 내', badge: '기간 내 가능' },
  { key: 'lack', title: '자금이 부족한 곳', chip: '부족', badge: '자금 부족' },
];

// 정렬. 값은 A-05의 sort와 같다. 처음에는 구분순이다
const LIST_SORTS = [
  { key: 'category', label: '구분순' },
  { key: 'price_asc', label: '가격 낮은 순' },
  { key: 'price_desc', label: '가격 높은 순' },
  { key: 'area_desc', label: '면적 넓은 순' },
  { key: 'households_desc', label: '세대수 많은 순' },
  { key: 'newest', label: '최근 준공 순' },
];
const LIST_DEFAULT_SORT = 'category';

// 카드가 많으면(광주 전체 1,055곳) 한 번에 다 만들면 화면이 0.3초쯤 멈췄다 (2026-10-20 측정).
// 그래서 처음 LIST_FIRST_CARDS장만 바로 그리고, 나머지는 LIST_CHUNK_CARDS장씩 다음 차례에 이어 붙인다.
// 순서와 내용은 같다. 그사이 목록을 다시 그리면 앞의 이어 붙이기는 멈춘다
const LIST_FIRST_CARDS = 60;
const LIST_CHUNK_CARDS = 150;

// 보기 방식 (2026-10-18). 칩 줄 오른쪽 끝의 아이콘 두 개로 고른다. store의 map.list_view에 둔다
//   basic: 이름, 면적·거래, 평균가 · 여유/부족
//   gauge: 위에 더해 막대 하나. 쓸 수 있는 자금이 집값의 몇 %인지 (200% 이상이면 가득).
//          여유가 적을수록 짧고, 부족하면 빨간 막대가 조금만 찬다
const LIST_VIEWS = [
  { key: 'basic', label: '기본', icon: ['M4 7h16', 'M4 12h16', 'M4 17h16'] }, // 줄 세 개
  { key: 'gauge', label: '게이지', icon: ['M4 8h16', 'M4 8h9', 'M4 16h16', 'M4 16h5'] }, // 막대 두 개 (앞은 찬 부분)
];

// 보기 방식 아이콘 두 개 (기본 | 게이지). 누른 쪽이 고른 것이다. 같은 것을 누르면 아무 일도 없다
function listViewToggle(current, onPick) {
  const box = listEl('div', 'list__view');
  box.setAttribute('role', 'group');
  box.setAttribute('aria-label', '보기 방식');
  const ns = 'http://www.w3.org/2000/svg';
  LIST_VIEWS.forEach((v) => {
    const button = listEl('button', `list__view-option list__view-option--${v.key}`);
    button.type = 'button';
    button.setAttribute('aria-label', v.label);
    button.title = v.label;
    button.setAttribute('aria-pressed', String(v.key === current));
    const svg = document.createElementNS(ns, 'svg');
    svg.setAttribute('viewBox', '0 0 24 24');
    svg.setAttribute('width', '18');
    svg.setAttribute('height', '18');
    svg.setAttribute('aria-hidden', 'true');
    v.icon.forEach((d, i) => {
      const path = document.createElementNS(ns, 'path');
      path.setAttribute('d', d);
      path.setAttribute('fill', 'none');
      path.setAttribute('stroke', 'currentColor');
      path.setAttribute('stroke-linecap', 'round');
      // 게이지 아이콘: 막대 바탕은 옅게, 찬 부분은 진하게
      path.setAttribute('stroke-width', v.key === 'gauge' ? '3' : '2');
      if (v.key === 'gauge' && i % 2 === 0) path.setAttribute('stroke-opacity', '0.3');
      svg.append(path);
    });
    button.append(svg);
    button.addEventListener('click', () => { if (v.key !== current) onPick(v.key); });
    box.append(button);
  });
  return box;
}
// 웹(가로 1024px 이상, css/map-web.css와 같은 폭)에서는 구분을 칩 대신 탭 네 칸(전체 · 지금 가능 · 기간 내 가능 · 자금 부족)으로 하나만 고른다 (2026-10-20)
const LIST_WEB_QUERY = window.matchMedia('(min-width: 1024px)');
const LIST_ALL_CATS = ['now', 'within', 'lack'];

// 목록에 보이는 구분 (모바일은 칩으로 켜고 끈다). 처음에는 셋 다.
// 웹의 탭은 하나만 고르므로, 모바일에서 둘을 켜 둔 채 넓히면 웹에서는 '전체'로 본다
const listShownCats = () => {
  const saved = store.get('map').list_cats;
  const keys = Array.isArray(saved) ? saved.filter((k) => LIST_ALL_CATS.includes(k)) : [];
  if (keys.length === 0) return LIST_ALL_CATS;
  if (LIST_WEB_QUERY.matches && keys.length !== 1) return LIST_ALL_CATS;
  return keys;
};

// 웹의 내 조건 상자 (목록 맨 위, 2026-10-20). 지도 화면 머리 줄의 "내 조건" 문장을 웹에서는 여기로 옮긴다.
//   5년 뒤 목표할 수 있는 가격
//   3억 6,666만 원 까지                      [수정]
//   보유 5,000만 원 · 월 100만 원 · 5년 · 보금자리론 30년
// 금액은 A-05 응답의 target_price (계산하지 않는다), 아래 줄은 넣어 둔 입력값(store의 input)이다.
// 대출 상품 이름은 A-04에서 한 번만 받아 둔다. 받기 전이나 실패하면 "대출 30년"으로 적는다
let listLoanProducts = null; // A-04 응답의 products. 받기 전에는 null
let listLoanRequest = null;
function listLoanName(id) {
  if (!listLoanRequest) {
    listLoanRequest = api.get('/api/loan-products')
      .then((data) => { listLoanProducts = (data && data.products) || []; })
      .catch(() => { listLoanProducts = []; });
  }
  const product = (listLoanProducts || []).find((p) => p.id === id);
  return product ? product.name : null;
}

function listGoal(targetPrice) {
  const input = store.get('input') || {};
  const box = listEl('div', 'list__goal');
  const when = input.target_years === 0 ? '지금' : `${input.target_years}년 뒤`;
  box.append(listEl('p', 'list__goal-label', `${when} 목표할 수 있는 가격`));
  const value = listEl('p', 'list__goal-value', format.won(targetPrice));
  value.append(listEl('span', 'list__goal-until', ' 까지'));
  box.append(value);
  const sub = listEl('p', 'list__goal-sub');
  const writeSub = () => {
    const period = input.target_years === 0 ? '지금' : `${input.target_years}년`;
    const loan = input.loan_choice === 'none'
      ? '대출 없이'
      : `${listLoanName(input.loan_product_id) || '대출'} ${input.repayment_years}년`;
    sub.textContent = `보유 ${format.won(input.current_assets)} · 월 ${format.won(input.monthly_saving)} · ${period} · ${loan}`;
  };
  writeSub();
  if (listLoanProducts === null && input.loan_choice !== 'none') listLoanRequest.then(writeSub); // 이름이 오면 고쳐 쓴다
  box.append(sub);
  const edit = listEl('a', 'list__goal-edit', '수정');
  edit.href = 'profile.html';
  box.append(edit);
  return box;
}

// 웹의 구분 탭. 개수는 늘 서버가 준 전체 개수다. 고르면 store의 map.list_cats에 그 구분 하나(전체면 셋)를 둔다
function listTabs(counts, shown, onPick) {
  const tabs = listEl('div', 'list__tabs');
  tabs.setAttribute('role', 'tablist');
  tabs.setAttribute('aria-label', '구분');
  const current = shown.length === 1 ? shown[0] : 'all';
  [{ key: 'all', badge: '전체', count: counts.total }, ...LIST_GROUPS.map((g) => ({ ...g, count: counts[g.key] }))].forEach((t) => {
    const tab = listEl('button', `list__tab list__tab--${t.key}`);
    tab.type = 'button';
    tab.setAttribute('role', 'tab');
    tab.setAttribute('aria-selected', String(t.key === current));
    tab.disabled = t.count === 0; // 0곳인 구분은 고를 수 없다 (고르면 목록이 비기만 한다)
    tab.append(listEl('b', 'list__tab-count', format.comma(t.count)), listEl('span', 'list__tab-label', t.badge));
    tab.addEventListener('click', () => { if (t.key !== current) onPick(t.key === 'all' ? LIST_ALL_CATS : [t.key]); });
    tabs.append(tab);
  });
  return tabs;
}
const listViewMode = () => (store.get('map').list_view === 'gauge' ? 'gauge' : 'basic');

const LIST_TEXT = {
  info: '판매 중인 매물이 아니라 최근 1년 실거래 기록입니다. 금액은 가정에 따른 추정치입니다.',
  emptyTitle: '이 지역에 조건에 맞는 아파트가 없습니다.',
  emptyHelp: '면적이나 준공 연도 조건을 넓히거나 다른 동을 살펴보세요.',
  noTargetTitle: '이 동에는 지금 조건으로 목표할 수 있는 아파트가 없습니다.',
  noTargetHelp: '저축액이나 목표 기간을 바꾸거나 다른 동을 살펴보세요.',
  noTargetButton: '조건 수정',
  resetFilters: '조건 초기화',
  changeFilters: '조건 바꾸기',
  loadFail: '아파트를 불러오지 못했습니다. 잠시 후 다시 시도해 주세요.', // 지도 화면과 같은 문장 (와이어프레임 P-04 ⑩)
  retry: '다시 시도',
  loading: '아파트를 불러오는 중', // 와이어프레임 P-05 ⑯의 알림과 같은 말
  noCoord: '위치 없음',
  overCap: '상한 초과',
  overCapHelp: '평균가가 고른 대출 상품의 대상 주택 가격 상한을 넘습니다. 이 상품으로는 대출을 받기 어려울 수 있습니다.',
};

// 실거래 수집 기준일 (A-13). 화면을 연 동안 한 번만 받는다. 받지 못하거나 없으면 null
let listBaseDate = null;
function listTradesBaseDate() {
  if (!listBaseDate) {
    listBaseDate = api.get('/api/data-status')
      .then((status) => status.trades_base_date)
      .catch(() => {
        listBaseDate = null; // 다음에 그릴 때 다시 받아 본다
        return null;
      });
  }
  return listBaseDate;
}

// 요소 하나를 만든다. text는 textContent로 넣는다.
function listEl(tag, className, text) {
  const el = document.createElement(tag);
  if (className) el.className = className;
  if (text !== undefined && text !== null) el.textContent = text;
  return el;
}

// 오른쪽 금액 "+1억 2,667만" (여유) 또는 "−9,900만" (부족). 부족자금이 음수면 여유다. 화면 읽기에는 "여유 …원"으로
function listGapShort(area) {
  const surplus = area.shortage <= 0;
  const amount = format.won(Math.abs(area.shortage)).replace(/ ?원$/, '');
  const gap = listEl('strong', `list-card__gap list-card__gap--${area.category}`, `${surplus ? '+' : '−'}${amount}`);
  gap.setAttribute('aria-label', `${surplus ? '여유' : '부족'} ${format.won(Math.abs(area.shortage))}`);
  return gap;
}

// 게이지 한 줄. 쓸 수 있는 자금 = 평균가 − 부족자금 (부족자금이 음수면 여유). 둘 다 서버(A-05)가 준 값이다.
// 막대 길이 = 자금 ÷ 평균가의 절반 (200%면 가득). 너무 짧아 안 보이지 않게 4%는 둔다
function listGauge(area) {
  const box = listEl('div', `list-gauge list-gauge--${area.category}`);
  const funds = area.avg_price - area.shortage;
  const ratio = area.avg_price > 0 ? Math.max(funds, 0) / area.avg_price : 0;
  const bar = listEl('span', 'list-gauge__bar');
  const fill = listEl('span', 'list-gauge__fill');
  fill.style.width = `${Math.min(Math.max(ratio / 2, 0.04), 1) * 100}%`;
  // 검은 눈금 = 집값 (100%). 막대는 200%가 가득이므로 한가운데다. 막대가 눈금을 넘으면 여유, 못 미치면 부족
  bar.append(fill, listEl('span', 'list-gauge__mark'));
  bar.setAttribute('aria-hidden', 'true');
  const text = listEl('span', 'list-gauge__text', `집값의 ${format.comma(Math.round(ratio * 100))}%`);
  box.append(bar, text);
  return box;
}

// 게이지 보기의 기준 안내. "5년 뒤 자기자금 2억 7,000만 원 기준 · 검은 눈금" (시안 8번 문구 그대로)
// 기준 금액은 서버가 준 값에서 읽는다 (평균가 − 부족자금). 아파트마다 다르면(대출 한도가 집값에 따라 달라짐) 금액을 빼고 적는다
function listGaugeNote(apartments) {
  const input = store.get('input');
  const years = input.target_years;
  const when = years === 0 ? '지금' : years ? `${years}년 뒤` : '목표 시점';
  const what = input.loan_choice === 'none' ? '자기자금' : '쓸 수 있는 자금(자기자금 + 대출)';
  const funds = new Set();
  apartments.forEach((a) => a.areas.forEach((area) => funds.add(area.avg_price - area.shortage)));
  const note = listEl('p', 'list__gauge-note');
  note.append(document.createTextNode(`${when} ${what} `));
  if (funds.size === 1) note.append(listEl('b', null, format.won([...funds][0])), document.createTextNode(' '));
  note.append(document.createTextNode('기준 · 검은 눈금'));
  return note;
}

function listCard(apartment, handlers) {
  const group = LIST_GROUPS.find((g) => g.key === apartment.category);
  const card = listEl('article', `list-card list-card--${apartment.category}`);
  const body = listEl('button', 'list-card__body');
  body.type = 'button';
  card.append(body);

  let index = 0; // 보고 있는 면적. 첫째가 평균가가 가장 낮은 면적이다 (FR-APT-05)

  // 면적마다 한 장. 옆으로 늘어놓고 카드 밖은 가린다. 넘기면 옆으로 밀려 다음 면적이 들어온다 (list.css)
  const track = listEl('div', 'list-card__track');
  body.append(track);
  apartment.areas.forEach((area) => {
    const areaGroup = LIST_GROUPS.find((g) => g.key === area.category);
    const slide = listEl('div', 'list-card__slide');
    // 시안 5번 (iOS 그룹형, 2026-10-18): 구분 아이콘 | 이름, "평균 · 면적" | 여유/부족 금액 | ›
    slide.append(listEl('span', `badge badge--${area.category}`, areaGroup.badge)); // 글자는 화면 읽기용, 보이는 것은 집 아이콘
    const mid = listEl('div', 'list-card__mid');
    mid.append(listEl('h3', 'list-card__name', apartment.name));
    const meta = listEl('p', 'list-card__meta', `평균 ${format.won(area.avg_price).replace(/ ?원$/, '')} · ${format.area(area.supply_area, area.exclusive_area)}`);
    if (apartment.latitude === null || apartment.longitude === null) {
      meta.append(listEl('span', 'list-card__tag', LIST_TEXT.noCoord));
    }
    mid.append(meta);
    if (listViewMode() === 'gauge') mid.append(listGauge(area));
    slide.append(mid);
    slide.append(listGapShort(area));
    track.append(slide);
  });

  // 평균가가 상품의 대상 주택 가격 상한을 넘는 면적 (FR-LOAN-14). 알리기만 하고 빼지 않는다.
  // 카드 위 선에 걸쳐 금액 위 오른쪽에 하나만 둔다 (new-style.css, 2026-10-20 팀장 결정). 보고 있는 면적이 넘을 때만 보인다
  const cap = apartment.areas.some((a) => a.over_price_cap)
    ? listEl('span', 'list-card__tag list-card__tag--cap', LIST_TEXT.overCap)
    : null;
  if (cap) {
    cap.title = LIST_TEXT.overCapHelp;
    card.append(cap);
  }

  const show = () => {
    const area = apartment.areas[index];
    if (cap) cap.hidden = !area.over_price_cap;
    const areaGroup = LIST_GROUPS.find((g) => g.key === area.category);
    track.style.transform = `translateX(${-100 * index}%)`;
    body.setAttribute('aria-label', `${apartment.name}, ${format.area(area.supply_area, area.exclusive_area)}, ${areaGroup.badge}`);
  };

  body.addEventListener('click', () => handlers.onSelect && handlers.onSelect(apartment, index));

  if (apartment.areas.length > 1) {
    const next = listEl('button', 'list-card__next');
    next.type = 'button';
    next.setAttribute('aria-label', '다른 면적 보기');
    const arrow = listEl('span', 'list-card__arrow', '›');
    const page = listEl('span', 'list-card__page');
    next.append(arrow, page);
    next.addEventListener('click', () => {
      index = (index + 1) % apartment.areas.length;
      page.textContent = `${index + 1}/${apartment.areas.length}`;
      show();
    });
    page.textContent = `1/${apartment.areas.length}`;
    card.append(next);
  }

  show();
  card.dataset.category = group.key;
  return card;
}

function listHead(result, options) {
  const head = listEl('header', 'list__head');
  const where = options.where || {};
  const place = [where.gu, where.dong].filter(Boolean).join(' ');
  const count = `${format.comma(result.counts.total)}곳`;
  // 자리가 모자라면 지역 이름만 말줄임(…)으로 줄이고 "· 22곳"은 남긴다
  // "· 22곳" 앞의 빈칸은 붙는 빈칸(\u00a0)이다. 보통 빈칸은 flex 안에서 사라진다
  const title = listEl('h2', 'list__title');
  if (place) title.append(listEl('span', 'list__place', place), listEl('span', 'list__count', `\u00a0· ${count}`));
  else title.append(listEl('span', 'list__count', count));
  head.append(title);

  head.append(listInfo());

  // 오른쪽: 정렬 "구분순 ▾" (닫기 바로 옆). 보기 방식 아이콘(기본 | 게이지)은 칩 줄 오른쪽에 있다
  const side = listEl('div', 'list__side');
  if (LIST_WEB_QUERY.matches && options.onView) side.append(listViewToggle(listViewMode(), options.onView)); // 웹: 칩 줄이 없어 머리로 옮긴다 (1200px 이상에서만 보인다)
  if (options.onSort) side.append(listSortMenu(options.sort || LIST_DEFAULT_SORT, options.onSort));
  if (side.children.length > 0) head.append(side);

  head.append(listCloseButton(() => options.onClose && options.onClose()));
  return head;
}

function listCloseButton(onClose) {
  const close = listEl('button', 'list__close', '×');
  close.type = 'button';
  close.setAttribute('aria-label', '닫기');
  close.addEventListener('click', onClose);
  return close;
}

// 안내 아이콘 ( ! ). 누르거나 마우스를 올리면 실거래 기록 안내가 뜨고, 바깥을 누르면 닫힌다 (FR-COMMON-02, B5).
// 문구 끝에 실거래 수집 기준일을 적는다 (FR-DATA-05). 기준일이 없으면 그 문장만 뺀다
function listInfo() {
  const info = listEl('span', 'list__info-wrap');
  const button = listEl('button', 'list__info', '!');
  button.type = 'button';
  button.setAttribute('aria-label', '안내');
  const tip = listEl('span', 'list__tip', LIST_TEXT.info);
  tip.setAttribute('role', 'tooltip');
  listTradesBaseDate().then((date) => {
    if (date) tip.textContent = `${LIST_TEXT.info} 실거래 ${date} 기준.`;
  });
  button.addEventListener('click', () => info.classList.toggle('list__info-wrap--open'));
  const onOutside = (event) => {
    if (!info.isConnected) document.removeEventListener('click', onOutside); // 목록을 다시 그렸으면 치운다
    else if (!info.contains(event.target)) info.classList.remove('list__info-wrap--open');
  };
  document.addEventListener('click', onOutside);
  info.append(button, tip);
  return info;
}

// 정렬 버튼 "가격 낮은 순 ▾"과 작은 선택 창 (B1). 고르면 창을 닫고 onSort(sort)를 부른다
function listSortMenu(current, onSort) {
  return listPicker(LIST_SORTS, current, onSort, '정렬', 'list__sort');
}

// 글자 버튼과 작은 선택 창. items: [{ key, label }]. 고르면 창을 닫고 onPick(key)를 부른다 (같은 것을 고르면 닫기만)
function listPicker(items, current, onPick, name, className) {
  const wrap = listEl('div', `list__sort ${className}`);
  const now = items.find((s) => s.key === current) || items[0];
  const button = listEl('button', 'list__sort-button', now.label);
  button.type = 'button';
  button.setAttribute('aria-label', `${name}: ${now.label}`);
  button.setAttribute('aria-haspopup', 'listbox');
  button.setAttribute('aria-expanded', 'false');

  const menu = listEl('ul', 'list__sort-menu');
  menu.setAttribute('role', 'listbox');
  menu.setAttribute('aria-label', name);
  menu.hidden = true;

  const setOpen = (open) => {
    menu.hidden = !open;
    button.setAttribute('aria-expanded', String(open));
  };
  // 창 밖을 누르면 닫는다
  const onOutside = (event) => {
    if (!wrap.isConnected) document.removeEventListener('click', onOutside); // 목록을 다시 그렸으면 치운다
    else if (!wrap.contains(event.target)) setOpen(false);
  };
  document.addEventListener('click', onOutside);
  wrap.addEventListener('keydown', (event) => {
    if (event.key === 'Escape') {
      setOpen(false);
      button.focus();
    }
  });

  items.forEach((s) => {
    const item = listEl('li');
    const option = listEl('button', 'list__sort-option', s.label);
    option.type = 'button';
    option.setAttribute('role', 'option');
    option.setAttribute('aria-selected', String(s.key === now.key));
    if (s.key === now.key) option.append(listEl('span', 'list__sort-check', '✓'));
    option.addEventListener('click', () => {
      setOpen(false);
      if (s.key !== now.key) onPick(s.key);
    });
    item.append(option);
    menu.append(item);
  });

  button.addEventListener('click', () => setOpen(menu.hidden));
  wrap.append(button, menu);
  return wrap;
}

// buttons: [{ text, onClick }]. onClick이 없는 버튼은 그리지 않는다
function listEmpty(title, help, buttons = []) {
  const box = listEl('div', 'list__empty');
  box.append(listEl('p', 'list__empty-title', title));
  box.append(listEl('p', 'list__empty-help', help));
  const shown = buttons.filter((b) => b.onClick);
  if (shown.length > 0) {
    const row = listEl('div', 'list__empty-buttons');
    shown.forEach((b) => {
      const button = listEl('button', 'link-button list__empty-button', b.text);
      button.type = 'button';
      button.addEventListener('click', b.onClick);
      row.append(button);
    });
    box.append(row);
  }
  return box;
}

const listView = {
  renderSeq: 0, // 목록을 그린 차례. 나눠 붙이는 중에 다시 그리면 앞의 것을 멈춘다

  lastTarget: null, // 마지막으로 받은 A-05의 target_price. 불러오는 중 화면의 내 조건 상자에 쓴다
  last: null, // 마지막으로 그린 { container, result, options }. 웹 ↔ 모바일이 바뀌면 칩 · 탭을 바꿔 다시 그린다

  // A-05를 불러 그리고, 받은 결과를 돌려준다. 조건은 guard.conditions()가 만든다.
  async load(container, where, handlers = {}) {
    const sort = store.get('map').sort || LIST_DEFAULT_SORT;
    const onSort = (next) => {
      store.set('map', { sort: next });
      listView.load(container, where, handlers).catch(() => {}); // 실패하면 load가 오류 문구를 그린다
    };
    listView.renderLoading(container, { where, onClose: handlers.onClose });
    try {
      const result = await api.post('/api/apartments/search', { conditions: guard.conditions(), where, sort });
      listView.render(container, result, { ...handlers, where, sort, onSort });
      return result;
    } catch (error) {
      // 서버가 값을 거부했으면(422) 그 문장을, 아니면 불러오지 못했다는 문장을 보여 준다 (지도 화면과 같다)
      listView.renderError(container, {
        message: error.status === 422 ? error.detail : LIST_TEXT.loadFail,
        onRetry: () => listView.load(container, where, handlers).catch(() => {}),
        onClose: handlers.onClose,
      });
      throw error;
    }
  },

  // 불러오는 중. 머리(지역 이름, 닫기)와 회색 자리표시 카드 3장 (P-05 ⑯, FR-COMMON-10).
  // 받는 동안 빈 화면이나 앞의 목록이 보이지 않게 한다. 화면 읽기 프로그램에는 '불러오는 중'으로 알린다
  renderLoading(container, { where, onClose } = {}) {
    const root = listEl('section', 'list list--loading');
    root.setAttribute('aria-busy', 'true');
    // 웹: 지역만 바꿔 다시 받는 동안에도 내 조건 상자는 남긴다 (목표 가능 가격은 지역과 상관없다)
    if (LIST_WEB_QUERY.matches && listView.lastTarget != null) root.append(listGoal(listView.lastTarget));
    const head = listEl('header', 'list__head');
    const place = [where && where.gu, where && where.dong].filter(Boolean).join(' ');
    const title = listEl('h2', 'list__title');
    if (place) title.append(listEl('span', 'list__place', place));
    title.append(listEl('span', 'list__skeleton list__skeleton--count'));
    head.append(title);
    if (onClose) head.append(listCloseButton(onClose));
    root.append(head);
    const status = listEl('p', 'list__loading-text', LIST_TEXT.loading);
    status.setAttribute('role', 'status');
    root.append(status);

    const group = listEl('div', 'list__group');
    group.setAttribute('aria-hidden', 'true');
    for (let i = 0; i < 3; i += 1) {
      const card = listEl('div', 'list-card list-card--skeleton');
      const body = listEl('div', 'list-card__skeleton-body');
      const headLine = listEl('div', 'list-card__head');
      headLine.append(listEl('span', 'list__skeleton list__skeleton--name'), listEl('span', 'list__skeleton list__skeleton--badge'));
      body.append(headLine, listEl('span', 'list__skeleton list__skeleton--meta'), listEl('span', 'list__skeleton list__skeleton--money'));
      card.append(body);
      group.append(card);
    }
    root.append(group);
    container.replaceChildren(root);
  },

  // 불러오지 못함. 빨간 테두리 상자에 문장과 '다시 시도' (P-05 ⑰, 아파트 정보 탭과 같은 모양)
  renderError(container, { message = LIST_TEXT.loadFail, onRetry, onClose } = {}) {
    const box = listEl('div', 'notice notice--error list__fail');
    box.setAttribute('role', 'alert');
    box.append(listEl('p', 'list__fail-text', message));
    if (onRetry) {
      const retry = listEl('button', 'link-button list__fail-retry', LIST_TEXT.retry);
      retry.type = 'button';
      retry.addEventListener('click', onRetry);
      box.append(retry);
    }
    const root = listEl('section', 'list');
    if (onClose) {
      const head = listEl('header', 'list__head');
      head.append(listCloseButton(onClose));
      root.append(head);
    }
    root.append(box);
    container.replaceChildren(root);
  },

  // A-05 응답으로 목록을 그린다. options: { where, sort, onSort, onSelect, onClose } (모두 없어도 된다)
  render(container, result, options = {}) {
    // 보기 방식(기본 / 게이지)은 이 파일이 store에 두고, 바꾸면 같은 응답으로 다시 그린다
    const full = result; // 칩으로 걸러도 다시 그릴 때는 받은 응답 전체로
    const onView = (next) => {
      store.set('map', { list_view: next });
      listView.render(container, full, options);
    };
    options = { ...options, onView };
    listView.last = { container, result: full, options };
    listView.lastTarget = result.target_price;
    const root = listEl('section', `list list--${listViewMode()}`);
    if (LIST_WEB_QUERY.matches) root.append(listGoal(result.target_price)); // 웹: 내 조건 상자
    root.append(listHead(result, options));

    // 결과 없음 (P-05 ⑨, FR-APT-07). '조건 초기화', '조건 바꾸기'는 부르는 쪽이 넘겼을 때만
    if (result.counts.total === 0) {
      root.append(listEmpty(LIST_TEXT.emptyTitle, LIST_TEXT.emptyHelp, [
        { text: LIST_TEXT.resetFilters, onClick: options.onResetFilters },
        { text: LIST_TEXT.changeFilters, onClick: options.onChangeFilters },
      ]));
      container.replaceChildren(root);
      return;
    }

    // 칩: 지금 / 기간 내 / 부족. 누르면 그 구분을 목록에서 켜고 끈다 (2026-10-18). 하나는 늘 켜져 있다.
    // 고른 것은 store의 map.list_cats에 둔다. 개수는 늘 서버가 준 전체 개수다. 오른쪽 끝에 보기 방식 "기본 ▾"
    // 웹은 칩 대신 탭 네 칸 (listTabs). 보기 방식은 머리의 정렬 옆에 있다
    let shown = listShownCats();
    // 웹의 탭으로 고른 구분이 조건이 바뀌어 0곳이 되었으면 '전체'로 본다
    if (LIST_WEB_QUERY.matches && shown.length === 1 && result.counts[shown[0]] === 0) shown = LIST_ALL_CATS;
    if (LIST_WEB_QUERY.matches) {
      root.append(listTabs(result.counts, shown, (next) => {
        store.set('map', { list_cats: next });
        listView.render(container, full, options);
      }));
    }
    const chips = listEl('div', 'list__chips');
    LIST_GROUPS.forEach((g) => {
      const chip = listEl('button', `chip chip--${g.key}`, `${g.chip} ${format.comma(result.counts[g.key])}`);
      chip.type = 'button';
      chip.setAttribute('aria-pressed', String(shown.includes(g.key)));
      chip.addEventListener('click', () => {
        const next = shown.includes(g.key) ? shown.filter((k) => k !== g.key) : [...shown, g.key];
        if (next.length === 0) return; // 다 끄지는 않는다
        store.set('map', { list_cats: next });
        listView.render(container, full, options);
      });
      chips.append(chip);
    });
    chips.append(listViewToggle(listViewMode(), options.onView));
    // 웹은 칩을 숨기고 보기 방식만 남긴 줄을 둔다. 목록이 좁은 웹(1024 ~ 1199px)에서만 보인다 (넓으면 머리에 있다. list.css)
    if (LIST_WEB_QUERY.matches) chips.classList.add('list__chips--web');
    root.append(chips);
    result = { ...result, apartments: result.apartments.filter((a) => shown.includes(a.category)) };
    if (listViewMode() === 'gauge' && full.apartments.length > 0) root.append(listGaugeNote(full.apartments));

    // 아파트는 있지만 목표할 수 있는 곳이 없음 (A6). '조건 수정'은 저축 계획 단계로 간다
    if (result.counts.now === 0 && result.counts.within === 0) {
      root.append(listEmpty(LIST_TEXT.noTargetTitle, LIST_TEXT.noTargetHelp,
        [{ text: LIST_TEXT.noTargetButton, onClick: () => { location.href = 'plan.html'; } }]));
    }

    // 구분순이 아니면(가격 · 면적 · 세대수 · 준공 순) 구분별 제목 없이 서버가 준 순서로 잇는다. 구분은 카드의 배지로만 보인다 (B2)
    // 카드는 [넣을 칸, 아파트]의 줄로 모았다가 앞에서부터 그린다 (listFill)
    const cards = [];
    if (options.sort && options.sort !== 'category') {
      const section = listEl('div', 'list__group');
      result.apartments.forEach((a) => cards.push([section, a]));
      root.append(section);
    } else {
      LIST_GROUPS.forEach((g) => {
        const apartments = result.apartments.filter((a) => a.category === g.key);
        if (apartments.length === 0) return;
        const section = listEl('div', 'list__group');
        section.append(listEl('h3', 'list__group-title', `${g.title} · ${format.comma(apartments.length)}`));
        apartments.forEach((a) => cards.push([section, a]));
        root.append(section);
      });
    }
    listView.fill(cards, options, LIST_FIRST_CARDS); // 처음 몇 장은 화면에 붙이기 전에
    container.replaceChildren(root);
    const seq = ++listView.renderSeq;
    const more = () => {
      if (seq !== listView.renderSeq || cards.length === 0) return;
      listView.fill(cards, options, LIST_CHUNK_CARDS);
      if (cards.length > 0) setTimeout(more, 0);
    };
    if (cards.length > 0) setTimeout(more, 0);
  },

  // 모아 둔 카드 줄에서 앞의 count장을 만들어 각자의 칸에 붙인다
  fill(cards, options, count) {
    cards.splice(0, count).forEach(([section, apartment]) => section.append(listCard(apartment, options)));
  },
};

// 창 폭이 1024px을 넘나들면 구분 칩(모바일) ↔ 탭(웹)을 바꿔 같은 응답으로 다시 그린다
LIST_WEB_QUERY.addEventListener('change', () => {
  const last = listView.last;
  if (last && last.container.isConnected) listView.render(last.container, last.result, last.options);
});
