// 공유받은 아파트 화면 (share.html, 3차 FR-APT-18). 담당: 김목산
//
// 공유 링크(share.html?apt=623&area=59)로 들어온 사람이 본다. 입력(재무정보·대출·저축 계획)이 없어도 열린다.
//   아파트 정보: A-06(GET /api/apartments/{id})의 값. 지번·도로명 주소 옆에 복사 버튼 (share.js)
//   시나리오   : 입력을 다 넣은 사람이면 내 조건으로 계산한다 (박채은의 scenario.js, A-07).
//                입력이 없으면 예시 값(CLAUDE.md "예시 값")으로 그린 것을 흐리게 덮고 [내 조건 넣기]를 보여 준다.
//                흐린 부분은 읽을 수 없고 누를 수 없다 (예시 값이라 실제 사람의 정보가 아니다).
//   구분 배지  : 입력이 있을 때만. A-05로 그 동을 찾아 이 아파트의 구분을 읽는다.
//   아래 버튼  : 입력이 있으면 [지도에서 보기], 없으면 [내 조건 넣고 비교하기]. 어느 쪽이든 이 아파트의 구·동을
//                store의 map 묶음에 남겨 지도가 그 동에서 열리게 한다.
// 계산하지 않는다. 숫자는 모두 서버가 준 값이다. 서버 글자는 textContent로만 넣는다.

const SHARE_PAGE_TEXT = {
  lockTitle: '내 조건으로 계산해 보세요',
  lockText: '보유자산과 저축 계획을 넣으면 이 아파트까지 얼마가 필요한지 바로 보여 드려요.',
  lockButton: '내 조건 넣기',
  toMap: '지도에서 보기',
  toStart: '내 조건 넣고 비교하기',
  failed: '아파트 정보를 불러오지 못했습니다.',
  retry: '다시 시도',
};
const SHARE_PAGE_BADGE = { now: '지금 가능', within: '기간 내 가능', lack: '자금 부족' };

// 입력이 없을 때 흐리게 그릴 예시 조건 (CLAUDE.md의 예시 값)
const SHARE_PAGE_SAMPLE = {
  current_assets: 50000000,
  monthly_saving: 1000000,
  target_years: 5,
  loan_choice: 'product',
  loan_product_id: 1,
  repayment_years: 30,
};

const sharePage = {
  detail: null, // A-06 응답
  areaIndex: 0,
  tab: 'info',
  hasInput: false,

  init() {
    const query = new URLSearchParams(location.search);
    const id = Number(query.get('apt'));
    if (!Number.isInteger(id) || id <= 0) {
      sharePage.missing();
      return;
    }
    sharePage.hasInput = guard.missingStep() === null;
    sharePage.wantedArea = Number(query.get('area')) || null;
    document.getElementById('share-tab-info').addEventListener('click', () => sharePage.showTab('info'));
    document.getElementById('share-tab-scenario').addEventListener('click', () => sharePage.showTab('scenario'));
    // ㎡/평. 지도 화면과 같은 값(store의 map.area_unit)을 쓴다
    document.querySelectorAll('.share-page__unit-option').forEach((button) => {
      button.addEventListener('click', () => {
        if (button.dataset.unit === sharePage.unit()) return;
        store.set('map', { area_unit: button.dataset.unit });
        sharePage.renderUnit();
        if (sharePage.detail) {
          sharePage.renderAreas();
          sharePage.renderInfo();
        }
      });
    });
    sharePage.renderUnit();
    sharePage.load(id);
  },

  async load(id) {
    const info = document.getElementById('share-info');
    info.replaceChildren(sharePage.el('p', 'share-page__loading', '불러오는 중'));
    try {
      sharePage.detail = await api.get(`/api/apartments/${id}`);
    } catch (error) {
      if (error.status === 404 || error.status === 422) {
        sharePage.missing();
        return;
      }
      const box = sharePage.el('div', 'share-page__fail');
      const retry = sharePage.el('button', 'button share-page__retry', SHARE_PAGE_TEXT.retry);
      retry.type = 'button';
      retry.addEventListener('click', () => sharePage.load(id));
      box.append(sharePage.el('p', '', SHARE_PAGE_TEXT.failed), retry);
      info.replaceChildren(box);
      return;
    }
    const { areas } = sharePage.detail;
    if (!areas.length) {
      sharePage.missing();
      return;
    }
    const wanted = areas.findIndex((area) => area.area_band === sharePage.wantedArea);
    sharePage.areaIndex = wanted >= 0 ? wanted : 0;
    sharePage.renderHead();
    sharePage.renderAll();
    sharePage.renderBottom();
    if (sharePage.hasInput) sharePage.loadBadge();
  },

  missing() {
    document.getElementById('share-page').hidden = true;
    document.getElementById('share-missing').hidden = false;
  },

  el(tag, className, text) {
    const node = document.createElement(tag);
    if (className) node.className = className;
    if (text !== undefined) node.textContent = text;
    return node;
  },

  area() {
    return sharePage.detail.areas[sharePage.areaIndex];
  },

  unit: () => (store.get('map').area_unit === 'pyeong' ? 'pyeong' : 'm2'),

  renderUnit() {
    document.querySelectorAll('.share-page__unit-option').forEach((button) => {
      button.setAttribute('aria-pressed', String(button.dataset.unit === sharePage.unit()));
    });
  },

  shareTarget() {
    const d = sharePage.detail;
    const a = sharePage.area();
    return { id: d.id, name: d.name, area_band: a.area_band, supply_area: a.supply_area, exclusive_area: a.exclusive_area };
  },

  renderHead() {
    const d = sharePage.detail;
    document.title = `${d.name} · 머니 to 홈`;
    format.keepWords(document.getElementById('share-name'), d.name); // 띄어쓰기에서만 줄바꿈 (아파트 창과 같다)
    document.getElementById('share-place').textContent = `${d.gu} ${d.dong}`;
    document.getElementById('share-actions').replaceChildren(shareView.shareButton(() => sharePage.shareTarget()));
    sharePage.renderAreas();
  },

  renderAreas() {
    const box = document.getElementById('share-areas');
    box.replaceChildren(...sharePage.detail.areas.map((area, index) => {
      const chip = sharePage.el('button', 'share-page__area', format.area(area.supply_area, area.exclusive_area, sharePage.unit()));
      chip.type = 'button';
      chip.setAttribute('aria-pressed', String(index === sharePage.areaIndex));
      chip.addEventListener('click', () => {
        if (index === sharePage.areaIndex) return;
        sharePage.areaIndex = index;
        box.querySelectorAll('.share-page__area').forEach((node, i) => node.setAttribute('aria-pressed', String(i === index)));
        sharePage.renderAll();
        if (sharePage.hasInput) sharePage.loadBadge();
      });
      return chip;
    }));
  },

  renderAll() {
    sharePage.renderInfo();
    sharePage.scenarioKey = null; // 면적이 바뀌면 시나리오를 다시 그린다
    if (sharePage.tab === 'scenario') sharePage.renderScenario();
  },

  // 아파트 창(apartment.js)의 정보 여덟 줄과 같은 순서와 문장
  renderInfo() {
    const d = sharePage.detail;
    const area = sharePage.area();
    const month = (text) => {
      const [year, mm] = String(text).split('-');
      return `${year}년 ${Number(mm)}월`;
    };
    const trade = `${format.comma(area.trade_count)}건${area.period_start && area.period_end ? ` (${month(area.period_start)} ~ ${month(area.period_end)})` : ''}`;
    let households = null;
    if (d.households !== null && d.households !== undefined) {
      households = `${format.comma(d.households)}세대`;
      if (d.households_base_date) households += ` (${month(d.households_base_date)} 기준)`;
    }
    const range = `${format.won(area.min_price).replace(/ 원$/, '')} ~ ${format.won(area.max_price)}`;
    const rows = [
      ['지번 주소', `${d.dong} ${d.jibun}`, true], // 화면은 동부터. 복사하면 시도와 구까지 (format.fullAddress)
      ['도로명 주소', d.road_address, true],
      ['준공 연도', d.built_year === null ? null : `${d.built_year}년`],
      ['면적', format.area(area.supply_area, area.exclusive_area, sharePage.unit())],
      ['실거래 평균가', format.won(area.avg_price)],
      ['최근 1년 거래', trade],
      ['세대수', households],
      ['가격 범위', range],
    ];
    const list = sharePage.el('dl', 'share-page__info');
    rows.filter(([, value]) => value !== null && value !== undefined && value !== '').forEach(([label, value, copy]) => {
      const row = sharePage.el('div', 'share-page__row');
      const desc = sharePage.el('dd', 'share-page__value');
      desc.append(sharePage.el('span', '', value));
      if (copy) desc.append(shareView.copyButton(() => format.fullAddress(d.gu, value), `${label} 복사`));
      row.append(sharePage.el('dt', 'share-page__label', label), desc);
      list.append(row);
    });
    document.getElementById('share-info').replaceChildren(list);
  },

  showTab(which) {
    sharePage.tab = which;
    const info = which === 'info';
    document.getElementById('share-tab-info').setAttribute('aria-selected', String(info));
    document.getElementById('share-tab-scenario').setAttribute('aria-selected', String(!info));
    document.getElementById('share-info').hidden = !info;
    document.getElementById('share-scenario-wrap').hidden = info;
    document.querySelector('.share-page__tabs').dataset.tab = which;
    if (!info) sharePage.renderScenario();
  },

  renderScenario() {
    if (typeof scenarioView === 'undefined') return;
    const key = `${sharePage.detail.id}:${sharePage.area().area_band}`;
    if (sharePage.scenarioKey === key) return;
    sharePage.scenarioKey = key;
    const wrap = document.getElementById('share-scenario-wrap');
    const root = document.getElementById('share-scenario');
    const conditions = sharePage.hasInput ? guard.conditions() : SHARE_PAGE_SAMPLE;
    scenarioView.render(root, { apartment: sharePage.detail, area: sharePage.area(), conditions });
    wrap.classList.toggle('share-page__locked', !sharePage.hasInput);
    root.toggleAttribute('inert', !sharePage.hasInput); // 흐린 부분은 누르거나 읽을 수 없다
    root.setAttribute('aria-hidden', String(!sharePage.hasInput));
    let lock = wrap.querySelector('.share-page__lock');
    if (sharePage.hasInput) {
      if (lock) lock.remove();
      return;
    }
    if (!lock) {
      lock = sharePage.el('div', 'share-page__lock');
      const card = sharePage.el('div', 'share-page__lock-card');
      const icon = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
      icon.setAttribute('viewBox', '0 0 24 24');
      icon.setAttribute('class', 'share-icon share-page__lock-icon');
      icon.setAttribute('aria-hidden', 'true');
      icon.innerHTML = '<rect x="5" y="10" width="14" height="10" rx="2"/><path d="M8 10V7a4 4 0 0 1 8 0v3"/>';
      const button = sharePage.el('button', 'button button--primary share-page__lock-button', SHARE_PAGE_TEXT.lockButton);
      button.type = 'button';
      button.addEventListener('click', () => sharePage.goInput());
      card.append(icon, sharePage.el('strong', 'share-page__lock-title', SHARE_PAGE_TEXT.lockTitle),
        sharePage.el('p', 'share-page__lock-text', SHARE_PAGE_TEXT.lockText), button);
      lock.append(card);
      wrap.append(lock);
    }
  },

  renderBottom() {
    const bottom = document.getElementById('share-bottom');
    const button = sharePage.el('button', `button ${sharePage.hasInput ? '' : 'button--primary'} share-page__go`,
      sharePage.hasInput ? SHARE_PAGE_TEXT.toMap : SHARE_PAGE_TEXT.toStart);
    button.type = 'button';
    button.addEventListener('click', () => (sharePage.hasInput ? sharePage.goMap() : sharePage.goInput()));
    bottom.replaceChildren(button);
  },

  // 지도가 이 아파트의 동에서 열리게 남긴다
  rememberPlace() {
    store.set('map', { gu: sharePage.detail.gu, dong: sharePage.detail.dong, open_region: true }); // 광주 전체가 아니라 이 동으로 연다
  },

  goMap() {
    sharePage.rememberPlace();
    location.href = 'map.html';
  },

  goInput() {
    sharePage.rememberPlace();
    location.href = guard.isBlank() ? 'index.html' : guard.resumePage();
  },

  // 구분 배지. 그 동을 내 조건으로 찾아 이 아파트·면적의 구분을 읽는다 (A-05). 못 받으면 배지를 숨긴다
  async loadBadge() {
    const badge = document.getElementById('share-badge');
    const d = sharePage.detail;
    const band = sharePage.area().area_band;
    try {
      const result = await api.post('/api/apartments/search', { conditions: guard.conditions(), where: { gu: d.gu, dong: d.dong } });
      const found = result.apartments.find((item) => item.id === d.id);
      const area = found && found.areas.find((item) => item.area_band === band);
      if (!area || band !== sharePage.area().area_band) {
        badge.hidden = !area ? true : badge.hidden;
        return;
      }
      badge.className = `share-page__badge share-page__badge--${area.category}`;
      badge.textContent = SHARE_PAGE_BADGE[area.category];
      badge.hidden = false;
    } catch (error) {
      badge.hidden = true;
    }
  },
};

document.addEventListener('DOMContentLoaded', () => sharePage.init());
