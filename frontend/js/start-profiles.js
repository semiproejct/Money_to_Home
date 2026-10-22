// 로그인한 시작 화면: 재무정보 3칸 + 찜한 시나리오 (2026-10-21). 담당: 박채은
//
// 화면 설계서 4.3.1. 팀장님이 확인한 미리보기 시안 A를 실제 API로 옮겼다.
// index.js(김해원)가 로그인한 것을 확인한 뒤 startProfiles.show(아이디)를 부른다. 받지 못하면 오류를 던진다 (index.js가 ④를 그린다).
//
//   위   재무정보 칸 (A-29 목록, A-30 더하기, A-31 고치기, A-32 이름, A-33 지우기)
//        [선택한 정보로 지도 보기]: A-34로 고른 것을 남기고, 그 칸의 값을 store의 input에 넣어 지도로 간다
//   아래 찜한 시나리오 (A-22 목록, A-35 찜 해제, 다시 찜하면 A-21). 주소 끝 #saved로 오면 여기부터 보인다
//
// 지금 고른 재무정보는 store의 place.profile_id, profile_name에 둔다. 입력 단계의 저장(account.save)과
// 시나리오의 찜(scenario.js)이 이 번호를 쓴다.
// 주민등록번호 앞 7자리는 만 나이를 계산하는 데만 쓰고 바로 지운다 (NFR-25). 서버와 브라우저 저장소에 남기지 않는다.
// 서버에서 온 글자(재무정보 이름, 아파트 이름, 상품 이름)는 textContent로 넣는다.

const PROFILE_MAX = 3;
const PROFILE_NAME_MAX = 10;
const PROFILE_YEARS = [0, 3, 5, 10];
const PROFILE_MAX_MAN = 1000000; // 연 소득, 현재 보유자산: 100억 원 = 1,000,000만 원 (profile.js와 같다)
const PROFILE_MAX_SAVING_MAN = 100000; // 월 저축 가능액: 10억 원 = 100,000만 원 (plan.js와 같다)
const PROFILE_CATEGORY_NAMES = { now: '지금 가능', within: '기간 내 가능', lack: '자금 부족' };

const PROFILE_TEXT = {
  titleSome: '재무정보를 골라 주세요',
  titleNone: '재무정보를 입력해 주세요',
  subSome: '고른 재무정보로 지도를 보여 줍니다.',
  subNone: '재무정보는 3개까지 저장할 수 있습니다.',
  toSaved: '찜한 시나리오 보기 ↓',
  toSlots: '↑ 재무정보 보기',
  go: '선택한 정보로 지도 보기',
  deleteHelp: '찜한 시나리오는 그대로 남습니다.',
  rrnHelp: '만 나이를 계산하는 데만 쓰고 저장하지 않습니다.',
  rrnMissing: '주민등록번호 앞 7자리를 입력해 주세요.',
  failed: '저장하지 못했습니다. 잠시 후 다시 시도해 주세요.',
  savedTitle: '찜한 시나리오',
  savedSub: '찜했을 때의 조건과 평균가로 계산한 값입니다.',
  savedLoading: '불러오는 중입니다.',
  savedFailed: '찜한 시나리오를 불러오지 못했습니다.',
  savedNone: '아직 찜한 시나리오가 없습니다. 지도에서 아파트를 열고 ♡를 누르면 찜할 수 있습니다.',
  savedNoneHere: '이 재무정보로 찜한 시나리오가 없습니다.',
  deleted: '삭제된 재무정보',
  changed: '지금 조건과 다름',
  unsaveFailed: '찜을 해제하지 못했습니다. 잠시 후 다시 시도해 주세요.',
  resaveFailed: '다시 찜하지 못했습니다. 잠시 후 다시 시도해 주세요.',
  resaveNoApartment: '원래 아파트를 찾을 수 없어 다시 찜할 수 없습니다.',
};

// 금액 검사: 입력 화면(profile.js, plan.js)의 checkMoney와 같은 규칙과 문장 (API 명세서 5장)
const PROFILE_MONEY_MSG = {
  negative: '0 이상의 숫자만 입력할 수 있습니다.',
  decimal: '소수는 입력할 수 없습니다. 만 원 단위의 정수로 입력해 주세요.',
  notNumber: '숫자만 입력할 수 있습니다.',
  maxAsset: '100억 원(1,000,000만 원)까지 입력할 수 있습니다.',
  maxSaving: '10억 원(100,000만 원)까지 입력할 수 있습니다.',
};

// 고정된 그림만 innerHTML로 넣는다 (사용자 글자는 넣지 않는다)
const PROFILE_ICONS = {
  pencil: '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M4 20h4L18.5 9.5a2.1 2.1 0 0 0-3-3L5 17v3z"/></svg>',
  check: '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M5 12.5l4.5 4.5L19 7.5"/></svg>',
  close: '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.8" stroke-linecap="round" aria-hidden="true"><path d="M7 7l10 10M17 7L7 17"/></svg>',
  plus: '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.6" stroke-linecap="round" aria-hidden="true"><path d="M12 5v14M5 12h14"/></svg>',
  heart: '<svg width="22" height="22" viewBox="0 0 24 24" aria-hidden="true"><path d="M12 20.5s-7.5-4.4-7.5-10.1A4.3 4.3 0 0 1 12 7.6a4.3 4.3 0 0 1 7.5 2.8c0 5.7-7.5 10.1-7.5 10.1z" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linejoin="round"/></svg>',
  heartOn: '<svg width="22" height="22" viewBox="0 0 24 24" aria-hidden="true"><path d="M12 20.5s-7.5-4.4-7.5-10.1A4.3 4.3 0 0 1 12 7.6a4.3 4.3 0 0 1 7.5 2.8c0 5.7-7.5 10.1-7.5 10.1z" fill="currentColor"/></svg>',
};

const startProfiles = {
  loginId: null,
  profiles: [], // A-29의 재무정보 (칸 번호 순)
  selectedId: null,
  products: [], // A-01 대출 상품
  renaming: null, // 이름을 바꾸는 칸의 재무정보 번호
  draft: '',
  saved: null, // A-22의 찜 목록. null이면 받는 중, 'failed'면 받지 못함
  savedFilter: null, // 'all', 'deleted', 또는 재무정보 번호
  offIds: new Set(), // ♡로 바꾼(해제한) 찜 번호. 새로 고치기 전까지 카드는 그 자리에 남는다
  toastTimer: null,
  lockedTop: 0, // 창을 열 때 보던 스크롤 위치

  $: (id) => document.getElementById(id),

  // ───────── 부르는 쪽 (index.js) ─────────

  async show(loginId) {
    startProfiles.loginId = loginId;
    startProfiles.products = await api.get('/api/loan-products').then((data) => data.products || []).catch(() => []);
    await startProfiles.load(); // 받지 못하면 오류를 던진다
    if (!startProfiles.profiles.length) await startProfiles.seedFromInput();
    startProfiles.bind();
    startProfiles.$('start-profiles-part').hidden = false;
    startProfiles.$('saved-band').hidden = false;
    startProfiles.$('saved').hidden = false;
    startProfiles.render();
    startProfiles.loadSaved().then(() => {
      // 마이페이지의 [찜한 시나리오]나 찜 알림의 [보기]로 왔으면 찜 목록부터
      if (location.hash === '#saved') startProfiles.scrollTo('saved', false);
    });
    if (location.hash === '#saved') requestAnimationFrame(() => startProfiles.scrollTo('saved', false));
  },

  hide() {
    ['start-profiles-part', 'saved-band', 'saved'].forEach((id) => { startProfiles.$(id).hidden = true; });
    startProfiles.$('start-go').hidden = true;
  },

  async load() {
    const data = await api.get('/api/profiles');
    startProfiles.profiles = data.profiles;
    // 이 탭에서 고르고 있던 재무정보가 있으면 그것, 없으면 마지막으로 고른 재무정보 (A-29의 selected_id)
    const inTab = store.get('place').profile_id;
    startProfiles.selectedId = data.profiles.some((p) => p.id === inTab) ? inTab : data.selected_id;
  },

  // 재무정보가 하나도 없는데 이 탭에 다 넣은 값이 있으면(로그인 전에 입력을 마침) 재무정보 1로 저장해 둔다
  async seedFromInput() {
    const input = store.get('input');
    const keys = ['age', 'annual_income', 'current_assets', 'loan_choice', 'monthly_saving', 'target_years'];
    const has = (key) => input[key] !== null && input[key] !== undefined;
    if (!keys.every(has)) return;
    const product = input.loan_choice === 'product';
    if (product && !(has('loan_product_id') && has('repayment_years'))) return;
    try {
      await api.post('/api/profiles', startProfiles.body(input));
      await startProfiles.load();
    } catch (error) {
      // 저장하지 못했으면 빈 칸으로 둔다. 사용자가 직접 더할 수 있다
    }
  },

  // 서버에 보내는 일곱 값
  body: (v) => ({
    age: v.age,
    annual_income: v.annual_income,
    current_assets: v.current_assets,
    loan_choice: v.loan_choice,
    loan_product_id: v.loan_choice === 'product' ? v.loan_product_id : null,
    repayment_years: v.loan_choice === 'product' ? v.repayment_years : null,
    monthly_saving: v.monthly_saving,
    target_years: v.target_years,
  }),

  bound: false,
  bind() {
    if (startProfiles.bound) return;
    startProfiles.bound = true;
    startProfiles.$('start-go').addEventListener('click', startProfiles.goMap);
    startProfiles.$('start-to-saved').addEventListener('click', () => startProfiles.scrollTo('saved'));
    if ('scrollRestoration' in history) history.scrollRestoration = 'manual';
  },

  // 재무정보 ↔ 찜한 시나리오: 한 페이지 안에서 스크롤로 오간다.
  // 두 부분이 각각 한 화면을 채워서, 맨 위에 맞추면 그 부분만 보인다. 손으로 스크롤해도 이어서 보인다
  scrollTo(part, smooth = true) {
    const behavior = smooth ? 'smooth' : 'instant';
    if (part === 'saved') startProfiles.$('saved').scrollIntoView({ block: 'start', behavior });
    else window.scrollTo({ top: 0, behavior });
    history.replaceState(null, '', `${location.pathname}${location.search}${part === 'saved' ? '#saved' : ''}`);
  },

  selected() {
    const { profiles, selectedId } = startProfiles;
    return profiles.find((p) => p.id === selectedId) || profiles[0] || null;
  },

  freeSlot() {
    const used = new Set(startProfiles.profiles.map((p) => p.slot));
    for (let slot = 1; slot <= PROFILE_MAX; slot += 1) if (!used.has(slot)) return slot;
    return null;
  },

  // ───────── 위: 재무정보 칸 ─────────

  render() {
    const { profiles, loginId } = startProfiles;
    const current = startProfiles.selected();

    const title = startProfiles.$('start-title');
    title.replaceChildren(`${loginId}님,`, document.createElement('br'), profiles.length ? PROFILE_TEXT.titleSome : PROFILE_TEXT.titleNone);
    startProfiles.$('start-subtitle').textContent = profiles.length ? PROFILE_TEXT.subSome : PROFILE_TEXT.subNone;

    const list = startProfiles.el('div', 'profile-slots');
    profiles.forEach((p) => list.append(startProfiles.card(p, current && p.id === current.id)));
    if (profiles.length < PROFILE_MAX) {
      const add = startProfiles.el('button', 'profile-add');
      add.type = 'button';
      add.innerHTML = PROFILE_ICONS.plus;
      add.append(`재무정보 ${startProfiles.freeSlot()} 추가`);
      add.addEventListener('click', () => startProfiles.openForm(null));
      list.append(add);
    }
    startProfiles.$('start-profiles').replaceChildren(list);
    startProfiles.$('start-go').hidden = profiles.length === 0;
    startProfiles.drawSaved();

    if (startProfiles.renaming !== null) {
      const input = list.querySelector('.profile-card__input');
      if (input) {
        input.focus();
        input.setSelectionRange(input.value.length, input.value.length);
      }
    }
  },

  // 칸의 글자. 아직 마치지 않은 단계(입력 화면에서 중간까지 저장)는 "-"
  text: {
    loan: (p) => (p.loan_choice === 'none' ? '대출 없이 계산' : (p.loan_choice === 'product' ? p.loan_product_name || '-' : '-')),
    term: (p) => (p.loan_choice === 'product' && p.repayment_years ? `${p.repayment_years}년` : '-'),
    goal: (p) => (p.target_years === null || p.target_years === undefined ? '-' : (p.target_years === 0 ? '지금' : `${p.target_years}년`)),
    won: (amount) => (amount === null || amount === undefined ? '-' : format.won(amount)),
  },

  card(p, on) {
    const card = startProfiles.el('div', `profile-card${on ? ' profile-card--on' : ''}`);
    const head = startProfiles.el('div', 'profile-card__head');
    head.append(startProfiles.el('span', 'profile-card__no', String(p.slot)));

    if (startProfiles.renaming === p.id) {
      head.append(startProfiles.renameBox(p));
    } else {
      const pencil = startProfiles.iconButton('pencil', `${p.name} 이름 바꾸기`);
      pencil.addEventListener('click', () => {
        startProfiles.renaming = p.id;
        startProfiles.draft = p.name;
        startProfiles.render();
      });
      // 칸 오른쪽 위: 수정  삭제
      const tools = startProfiles.el('span', 'profile-card__tools');
      const edit = startProfiles.el('button', 'profile-card__tool', '수정');
      edit.type = 'button';
      edit.setAttribute('aria-label', `${p.name} 수정`);
      edit.addEventListener('click', () => startProfiles.openForm(p));
      const remove = startProfiles.el('button', 'profile-card__tool', '삭제');
      remove.type = 'button';
      remove.setAttribute('aria-label', `${p.name} 삭제`);
      remove.addEventListener('click', () => startProfiles.askDelete(p));
      tools.append(edit, remove);
      head.append(startProfiles.el('span', 'profile-card__name', p.name), pencil, tools);
    }
    card.append(head);

    const t = startProfiles.text;
    const body = startProfiles.el('button', 'profile-card__body');
    body.type = 'button';
    body.setAttribute('aria-pressed', String(on));
    body.addEventListener('click', () => startProfiles.select(p.id));
    const grid = startProfiles.el('span', 'profile-card__grid');
    [['대출 상품', t.loan(p)], ['상환 기간', t.term(p)], ['월 저축 가능액', t.won(p.monthly_saving)], ['목표 기간', t.goal(p)]]
      .forEach(([label, value]) => {
        const cell = startProfiles.el('span', 'profile-card__cell');
        cell.append(startProfiles.el('span', 'profile-card__label', label), startProfiles.el('span', 'profile-card__value', value));
        grid.append(cell);
      });
    body.append(grid, startProfiles.el('span', 'profile-card__minor',
      `만 ${p.age}세 · 연 소득 ${format.won(p.annual_income)} · 보유자산 ${format.won(p.current_assets)}`));
    card.append(body);
    return card;
  },

  renameBox(p) {
    const wrap = startProfiles.el('div', 'profile-card__rename');
    const input = startProfiles.el('input', 'profile-card__input');
    input.type = 'text';
    input.maxLength = PROFILE_NAME_MAX;
    input.value = startProfiles.draft;
    input.setAttribute('aria-label', `재무정보 ${p.slot} 이름`);
    const cancel = () => {
      startProfiles.renaming = null;
      startProfiles.render();
    };
    const save = async () => {
      const name = input.value.trim().slice(0, PROFILE_NAME_MAX);
      if (!name || name === p.name) {
        cancel();
        return;
      }
      try {
        const saved = (await api.put(`/api/profiles/${p.id}/name`, { name })).profile;
        startProfiles.replace(saved);
        if (store.get('place').profile_id === saved.id) store.set('place', { profile_name: saved.name });
      } catch (error) {
        startProfiles.toast(error.status >= 400 && error.status < 500 ? error.detail : PROFILE_TEXT.failed);
      }
      cancel();
    };
    input.addEventListener('input', () => { startProfiles.draft = input.value; });
    input.addEventListener('keydown', (event) => {
      if (event.key === 'Enter') save();
      if (event.key === 'Escape') cancel();
    });
    const ok = startProfiles.iconButton('check', '이름 저장', 'profile-icon-button profile-icon-button--ok');
    ok.addEventListener('click', save);
    const no = startProfiles.iconButton('close', '이름 바꾸기 취소', 'profile-icon-button profile-icon-button--cancel');
    no.addEventListener('click', cancel);
    wrap.append(input, ok, no);
    return wrap;
  },

  // 받은 재무정보 하나로 목록의 그 줄을 바꾼다 (없으면 더하고 칸 번호 순으로)
  replace(profile) {
    const rest = startProfiles.profiles.filter((p) => p.id !== profile.id);
    startProfiles.profiles = [...rest, profile].sort((a, b) => a.slot - b.slot);
  },

  select(id) {
    startProfiles.selectedId = id;
    startProfiles.savedFilter = id; // 아래 찜 목록도 고른 재무정보로
    startProfiles.render();
  },

  // [선택한 정보로 지도 보기]: 고른 것을 남기고(A-34), 그 칸의 값을 이 탭에 채워 지도로.
  // 덜 채운 단계가 있으면(입력 화면에서 중간까지 저장한 재무정보) 그 단계로 간다
  async goMap() {
    const p = startProfiles.selected();
    if (!p) return;
    const input = {};
    ['age', 'annual_income', 'current_assets', 'loan_choice', 'loan_product_id', 'repayment_years', 'monthly_saving', 'target_years']
      .forEach((key) => {
        if (p[key] !== null && p[key] !== undefined) input[key] = p[key];
      });
    store.clear('input');
    store.set('input', input);
    store.set('place', { profile_id: p.id, profile_name: p.name, restart: false, summary_edit: false });
    try {
      await api.put(`/api/profiles/${p.id}/select`);
    } catch (error) {
      // 남기지 못해도 지도로 간다. 다음 로그인 때 처음 고른 칸만 달라진다
    }
    location.href = guard.resumePage();
  },

  // ───────── 아래에서 올라오는 창 ─────────
  // keepOpen: 입력 창(수정 · 추가)은 바깥을 누르거나 Esc를 눌러도 닫히지 않는다. [취소]나 [저장]으로만 닫는다
  layer(sheet, keepOpen = false) {
    const dim = startProfiles.el('div', 'profile-dim');
    if (!keepOpen) {
      dim.addEventListener('click', (event) => { if (event.target === dim) startProfiles.closeLayer(); });
      document.addEventListener('keydown', startProfiles.onEsc);
    }
    dim.append(sheet);
    startProfiles.$('start-layer').replaceChildren(dim);
    startProfiles.lock();
  },

  // 창이 열린 동안 뒤 화면은 스크롤되지 않는다.
  // 뒤 화면(body)의 너비와 높이를 부모(html, 곧 화면)의 100%로 고정하고 넘치는 부분은 숨긴다.
  // 보던 위치는 body 안에서 그대로 보여 주고, 창을 닫으면 그 위치로 돌아간다
  lock() {
    const root = document.documentElement;
    if (root.classList.contains('profile-lock')) return;
    const top = window.scrollY;
    startProfiles.lockedTop = top;
    root.classList.add('profile-lock');
    document.body.scrollTop = top;
  },

  unlock() {
    const root = document.documentElement;
    if (!root.classList.contains('profile-lock')) return;
    root.classList.remove('profile-lock');
    window.scrollTo({ top: startProfiles.lockedTop || 0, behavior: 'instant' });
  },

  closeLayer() {
    startProfiles.$('start-layer').replaceChildren();
    startProfiles.unlock();
    document.removeEventListener('keydown', startProfiles.onEsc);
  },

  onEsc(event) {
    if (event.key === 'Escape') startProfiles.closeLayer();
  },

  askDelete(p) {
    const sheet = startProfiles.el('div', 'profile-sheet');
    sheet.setAttribute('role', 'dialog');
    sheet.setAttribute('aria-label', '삭제 확인');
    sheet.append(startProfiles.el('div', 'profile-sheet__handle'),
      startProfiles.el('h2', 'profile-sheet__title', `${p.name}을(를) 삭제할까요?`),
      startProfiles.el('p', 'profile-sheet__help', PROFILE_TEXT.deleteHelp));
    const error = startProfiles.el('p', 'profile-sheet__error');
    error.setAttribute('role', 'alert');
    const buttons = startProfiles.el('div', 'profile-sheet__buttons');
    const cancel = startProfiles.el('button', 'button', '취소');
    cancel.type = 'button';
    cancel.addEventListener('click', startProfiles.closeLayer);
    const remove = startProfiles.el('button', 'button button--primary profile-sheet__delete', '삭제');
    remove.type = 'button';
    remove.addEventListener('click', async () => {
      remove.disabled = true;
      try {
        await api.delete(`/api/profiles/${p.id}`);
      } catch (e) {
        if (e.status !== 404) {
          error.textContent = e.status >= 400 && e.status < 500 ? e.detail : PROFILE_TEXT.failed;
          remove.disabled = false;
          return;
        }
      }
      // 그 재무정보로 한 찜은 서버가 "삭제된 재무정보"로 돌렸다. 화면에 받아 둔 목록도 맞춘다
      startProfiles.profiles = startProfiles.profiles.filter((x) => x.id !== p.id);
      if (Array.isArray(startProfiles.saved)) {
        startProfiles.saved = startProfiles.saved.map((r) => (r.profile_id === p.id ? { ...r, profile_id: null } : r));
      }
      if (store.get('place').profile_id === p.id) store.set('place', { profile_id: null, profile_name: null });
      if (startProfiles.selectedId === p.id) startProfiles.selectedId = startProfiles.profiles.length ? startProfiles.profiles[0].id : null;
      startProfiles.closeLayer();
      startProfiles.render();
    });
    buttons.append(cancel, remove);
    sheet.append(error, buttons);
    startProfiles.layer(sheet);
    remove.focus();
  },

  // 수정(p) 또는 추가(null).
  // 추가는 바로 앞 번호의 재무정보(2를 더하면 1, 3을 더하면 2)의 값을 아주 흐린 글자로만 보여 준다.
  // 빈 칸에서 Tab을 누르면 그 값이 들어간다. 고르는 값(대출, 상환 기간, 목표 기간)은 앞 재무정보의 값으로 골라 둔다
  openForm(p) {
    const slot = p ? p.slot : startProfiles.freeSlot();
    const before = p ? null : ([...startProfiles.profiles].filter((x) => x.slot < slot).sort((a, b) => b.slot - a.slot)[0]
      || startProfiles.profiles[0] || null);
    const hint = before || {};
    const base = p || hint;
    const form = { loan_choice: base.loan_choice, loan_product_id: base.loan_product_id, repayment_years: base.repayment_years, target_years: base.target_years };
    const titleText = p ? `${p.name} 수정` : `재무정보 ${slot} 추가`;

    const sheet = startProfiles.el('form', 'profile-sheet');
    sheet.noValidate = true;
    sheet.setAttribute('aria-label', titleText);
    sheet.append(startProfiles.el('div', 'profile-sheet__handle'), startProfiles.el('h2', 'profile-sheet__title', titleText));

    const man = (won) => (won === undefined || won === null ? '' : String(Math.round(won / 10000)));
    const money = (key, label, max) => startProfiles.numberField(key, label, p ? man(p[key]) : '', p ? '' : man(hint[key]), max);
    const rrn = startProfiles.rrnField(p ? p.age : null, p ? null : hint.age);
    const fields = {
      annual_income: money('annual_income', '연 소득', PROFILE_MAX_MAN),
      current_assets: money('current_assets', '현재 보유자산', PROFILE_MAX_MAN),
      monthly_saving: money('monthly_saving', '월 저축 가능액', PROFILE_MAX_SAVING_MAN),
    };

    // 대출 상품: 상품 목록(A-01) + 대출 없이 계산
    const loanField = startProfiles.el('div', 'profile-field');
    const loanLabel = startProfiles.el('label', 'profile-field__label', '대출 상품');
    loanLabel.htmlFor = 'profile-loan';
    const loanBox = startProfiles.el('div', 'profile-field__box');
    const select = startProfiles.el('select', 'profile-field__select');
    select.id = 'profile-loan';
    startProfiles.products.forEach((product) => {
      const option = startProfiles.el('option', '', product.name);
      option.value = String(product.id);
      select.append(option);
    });
    const none = startProfiles.el('option', '', '대출 없이 계산');
    none.value = 'none';
    select.append(none);
    const firstProduct = startProfiles.products[0];
    select.value = form.loan_choice === 'none' || !firstProduct ? 'none'
      : String(startProfiles.products.some((x) => x.id === form.loan_product_id) ? form.loan_product_id : firstProduct.id);
    loanBox.append(select);
    loanField.append(loanLabel, loanBox);

    const termField = startProfiles.el('div', 'profile-field');
    termField.append(startProfiles.el('span', 'profile-field__label', '상환 기간'));
    const termSegment = startProfiles.el('div', 'profile-segment');
    termField.append(termSegment);
    const drawTerms = () => {
      const product = startProfiles.products.find((x) => String(x.id) === select.value);
      termField.hidden = !product;
      if (!product) return;
      const options = product.repayment_years_options || [];
      if (!options.includes(form.repayment_years)) form.repayment_years = options[options.length - 1];
      termSegment.replaceChildren(...options.map((years) => startProfiles.segmentButton(`${years}년`, form.repayment_years === years, () => {
        form.repayment_years = years;
        drawTerms();
      })));
    };
    select.addEventListener('change', drawTerms);
    drawTerms();

    const goalField = startProfiles.el('div', 'profile-field');
    goalField.append(startProfiles.el('span', 'profile-field__label', '목표 기간'));
    const goalSegment = startProfiles.el('div', 'profile-segment');
    goalField.append(goalSegment);
    if (!PROFILE_YEARS.includes(form.target_years)) form.target_years = 3;
    const drawGoal = () => {
      goalSegment.replaceChildren(...PROFILE_YEARS.map((years) => startProfiles.segmentButton(years === 0 ? '지금' : `${years}년`,
        form.target_years === years, () => {
          form.target_years = years;
          drawGoal();
        })));
    };
    drawGoal();

    const error = startProfiles.el('p', 'profile-sheet__error');
    error.setAttribute('role', 'alert');
    const buttons = startProfiles.el('div', 'profile-sheet__buttons');
    const cancel = startProfiles.el('button', 'button', '취소');
    cancel.type = 'button';
    cancel.addEventListener('click', startProfiles.closeLayer);
    const ok = startProfiles.el('button', 'button button--primary', p ? '저장' : '추가');
    ok.type = 'submit';
    buttons.append(cancel, ok);

    sheet.append(rrn.node, fields.annual_income.node, fields.current_assets.node, loanField, termField,
      fields.monthly_saving.node, goalField, error, buttons);

    // 입력 화면처럼: 값이 비었거나 틀린 칸이 있으면 [저장 · 추가]를 끈다
    let sending = false;
    const refresh = () => {
      const moneyOk = Object.values(fields).every((field) => field.check().value !== null);
      ok.disabled = sending || !(moneyOk && rrn.age() !== null);
      error.textContent = '';
    };
    Object.values(fields).forEach((field) => field.input.addEventListener('input', refresh));
    rrn.node.addEventListener('input', refresh);
    rrn.node.addEventListener('profile-age', refresh);
    refresh();

    sheet.addEventListener('submit', async (event) => {
      event.preventDefault();
      if (ok.disabled) return;
      const age = rrn.age();
      if (age === null) {
        error.textContent = PROFILE_TEXT.rrnMissing;
        return;
      }
      const product = startProfiles.products.find((x) => String(x.id) === select.value);
      const values = {
        age,
        annual_income: format.manToWon(fields.annual_income.check().value),
        current_assets: format.manToWon(fields.current_assets.check().value),
        loan_choice: product ? 'product' : 'none',
        loan_product_id: product ? product.id : null,
        repayment_years: product ? form.repayment_years : null,
        monthly_saving: format.manToWon(fields.monthly_saving.check().value),
        target_years: form.target_years,
      };
      sending = true;
      refresh();
      try {
        const saved = p
          ? (await api.put(`/api/profiles/${p.id}`, values)).profile
          : (await api.post('/api/profiles', values)).profile;
        startProfiles.replace(saved);
        startProfiles.selectedId = saved.id;
        startProfiles.savedFilter = null;
        startProfiles.closeLayer();
        startProfiles.render();
        return;
      } catch (e) {
        // 서버가 거부한 값은 그 칸 아래에, 나머지는 버튼 위에 (API 명세서 2.5의 field)
        const field = fields[e.field];
        if (e.status === 422 && field) field.showError(e.detail);
        else error.textContent = e.status >= 400 && e.status < 500 ? e.detail : PROFILE_TEXT.failed;
      }
      sending = false;
      refresh();
    });

    startProfiles.layer(sheet, true);
    (rrn.age() === null ? rrn.front : select).focus();
  },

  // 만 나이: 재무정보 화면(profile.js)처럼 주민등록번호 앞 7자리로 계산한다.
  // 7자리는 계산에만 쓰고 바로 지운다. 남기는 것은 만 나이뿐이다. 고칠 때는 [다시 입력]을 누르지 않으면 그 나이를 그대로 쓴다
  rrnField(startAge, hintAge = null) {
    let age = startAge === undefined || startAge === null ? null : startAge;
    const node = startProfiles.el('div', 'profile-field');
    const label = startProfiles.el('span', 'profile-field__label', '주민등록번호 앞 7자리');
    label.id = 'profile-rrn-label';
    const box = startProfiles.el('div', 'profile-field__box');
    const front = startProfiles.el('input', 'profile-field__input');
    front.inputMode = 'numeric';
    front.maxLength = 6;
    front.autocomplete = 'off';
    front.placeholder = '생년월일 6자리';
    const hasHint = hintAge !== null && hintAge !== undefined;
    if (hasHint) {
      front.placeholder = `만 ${hintAge}세`; // 앞 재무정보의 나이를 흐리게. 빈 채로 Tab을 누르면 그 나이를 쓴다
      front.classList.add('profile-field__input--hint');
    }
    front.setAttribute('aria-labelledby', 'profile-rrn-label');
    const back = startProfiles.el('input', 'profile-field__input profile-field__input--one');
    back.inputMode = 'numeric';
    back.maxLength = 1;
    back.autocomplete = 'off';
    back.setAttribute('aria-label', '주민등록번호 뒤 첫째 자리');
    box.append(front, startProfiles.el('span', 'profile-field__unit', '-'), back, startProfiles.el('span', 'profile-field__unit', '●●●●●●'));
    const help = startProfiles.el('p', 'profile-sheet__help profile-rrn-help');
    const show = (errorText) => {
      help.classList.toggle('profile-rrn-help--error', Boolean(errorText));
      help.textContent = errorText || (age === null ? PROFILE_TEXT.rrnHelp : `만 ${age}세 · 7자리는 저장하지 않습니다.`);
    };

    // 이미 입력한 상태: 7자리는 남아 있지 않으므로 가린 모양으로 "입력함"을 보여 준다 (NFR-25). [다시 입력]을 누르면 빈 입력란
    const filled = startProfiles.el('div', 'profile-field__box profile-rrn-filled');
    const dots = startProfiles.el('span', 'profile-rrn-filled__dots', '●●●●●● - ●');
    dots.setAttribute('aria-hidden', 'true');
    const ageTag = startProfiles.el('span', 'profile-rrn-filled__age');
    const again = startProfiles.el('button', 'profile-rrn-filled__again', '다시 입력');
    again.type = 'button';
    filled.append(dots, ageTag, again);
    const showFilled = (on) => {
      filled.hidden = !on;
      box.hidden = on;
      ageTag.textContent = age === null ? '' : `만 ${age}세`;
      filled.setAttribute('aria-label', age === null ? '' : `주민등록번호 입력함, 만 ${age}세`);
    };
    again.addEventListener('click', () => {
      showFilled(false);
      front.focus();
    });
    const changed = () => node.dispatchEvent(new Event('profile-age'));
    const check = () => {
      const result = startProfiles.checkRrn(front.value, back.value);
      if (result.age !== null) {
        age = result.age;
        front.value = '';
        back.value = '';
        showFilled(true);
        changed();
      }
      show(result.error);
    };
    if (hasHint) {
      front.addEventListener('keydown', (event) => {
        if (event.key !== 'Tab' || event.shiftKey || front.value !== '' || back.value !== '') return;
        event.preventDefault();
        age = hintAge;
        showFilled(true);
        show(null);
        changed();
        again.focus();
      });
    }
    front.addEventListener('input', () => {
      if (front.value.length === 6) back.focus();
      check();
    });
    back.addEventListener('input', check);
    show(null);
    node.append(label, filled, box, help);
    showFilled(age !== null);
    return { node, front: age === null ? front : again, age: () => age };
  },

  // profile.js의 checkRrn과 같은 규칙 (만 15 ~ 100세)
  checkRrn(frontText, backText) {
    if (/\D/.test(frontText) || /\D/.test(backText)) return { age: null, error: PROFILE_MONEY_MSG.notNumber };
    if (frontText.length < 6 || backText.length < 1) return { age: null, error: null };
    const century = '1256'.includes(backText) ? 1900 : '3478'.includes(backText) ? 2000 : 1800;
    const year = century + Number(frontText.slice(0, 2));
    const month = Number(frontText.slice(2, 4));
    const day = Number(frontText.slice(4, 6));
    const birth = new Date(year, month - 1, day);
    const real = birth.getFullYear() === year && birth.getMonth() === month - 1 && birth.getDate() === day;
    const today = new Date();
    if (!real || birth > today) return { age: null, error: '생년월일을 다시 확인해 주세요.' };
    const hadBirthday = today.getMonth() > birth.getMonth() || (today.getMonth() === birth.getMonth() && today.getDate() >= birth.getDate());
    const years = today.getFullYear() - year - (hadBirthday ? 0 : 1);
    if (years < 15 || years > 100) return { age: null, error: '만 15세부터 100세까지 입력할 수 있습니다.' };
    return { age: years, error: null };
  },

  // 금액 칸 (만 원). 입력 화면의 checkMoney와 같은 규칙. 쉼표는 지우고 본다
  checkMoney(text, max) {
    const raw = text.replace(/,/g, '').trim();
    if (raw === '') return { value: null, error: null };
    if (/^-/.test(raw)) return { value: null, error: PROFILE_MONEY_MSG.negative };
    if (/^\d+\.\d*$|^\.\d+$/.test(raw)) return { value: null, error: PROFILE_MONEY_MSG.decimal };
    if (!/^\d+$/.test(raw)) return { value: null, error: PROFILE_MONEY_MSG.notNumber };
    const value = Number(raw);
    if (value > max) return { value: null, error: max === PROFILE_MAX_SAVING_MAN ? PROFILE_MONEY_MSG.maxSaving : PROFILE_MONEY_MSG.maxAsset };
    return { value, error: null };
  },

  // hint: 추가할 때 흐리게 보여 줄 앞 재무정보의 값(만 원). 빈 채로 Tab을 누르면 그 값이 들어가고 다음 칸으로 간다
  numberField(key, labelText, value, hint, max) {
    const node = startProfiles.el('div', 'profile-field');
    const label = startProfiles.el('label', 'profile-field__label', labelText);
    label.htmlFor = `profile-${key}`;
    const box = startProfiles.el('div', 'profile-field__box');
    const input = startProfiles.el('input', 'profile-field__input');
    input.id = `profile-${key}`;
    input.inputMode = 'numeric';
    input.autocomplete = 'off';
    input.value = value;
    if (hint !== '') {
      input.placeholder = Number(hint).toLocaleString('ko-KR');
      input.classList.add('profile-field__input--hint');
      input.addEventListener('keydown', (event) => {
        if (event.key !== 'Tab' || event.shiftKey || input.value !== '') return;
        input.value = hint; // 기본 동작(다음 칸으로)은 그대로
        input.dispatchEvent(new Event('input'));
      });
    }
    box.append(input, startProfiles.el('span', 'profile-field__unit', '만 원'));
    const message = startProfiles.el('p', 'profile-field__message');
    message.id = `profile-${key}-message`;
    input.setAttribute('aria-describedby', message.id);
    const showError = (text) => {
      message.textContent = text || '';
      node.classList.toggle('profile-field--error', Boolean(text));
    };
    const check = () => startProfiles.checkMoney(input.value, max);
    input.addEventListener('input', () => showError(check().error));
    node.append(label, box, message);
    return { node, input, check, showError };
  },

  segmentButton(text, on, onClick) {
    const button = startProfiles.el('button', 'profile-segment__option', text);
    button.type = 'button';
    button.setAttribute('aria-pressed', String(on));
    button.addEventListener('click', onClick);
    return button;
  },

  // ───────── 아래: 찜한 시나리오 ─────────

  async loadSaved() {
    try {
      startProfiles.saved = (await api.get('/api/saved-results')).results;
    } catch (error) {
      startProfiles.saved = 'failed';
    }
    startProfiles.drawSaved();
  },

  // 찜할 때의 조건이 그 재무정보의 지금 값과 같은가
  sameConditions(r, p) {
    const product = r.loan.choice === 'product';
    return p.current_assets === r.current_assets && p.monthly_saving === r.monthly_saving && p.target_years === r.target_years
      && p.loan_choice === r.loan.choice
      && (!product || (p.loan_product_id === r.loan.product_id && p.repayment_years === r.loan.repayment_years));
  },

  drawSaved() {
    const box = startProfiles.$('saved');
    const switchRow = startProfiles.el('div', 'start-switch-row');
    const back = startProfiles.el('button', 'start-switch', PROFILE_TEXT.toSlots);
    back.type = 'button';
    back.addEventListener('click', () => startProfiles.scrollTo('slots'));
    switchRow.append(back);
    const head = [switchRow, startProfiles.el('h1', 'title title--display saved-section__title', PROFILE_TEXT.savedTitle),
      startProfiles.el('p', 'saved-section__sub', PROFILE_TEXT.savedSub)];
    if (startProfiles.saved === null) {
      box.replaceChildren(...head, startProfiles.el('p', 'saved-empty', PROFILE_TEXT.savedLoading));
      return;
    }
    if (startProfiles.saved === 'failed') {
      box.replaceChildren(...head, startProfiles.el('p', 'saved-empty', PROFILE_TEXT.savedFailed));
      return;
    }

    const { profiles } = startProfiles;
    const items = startProfiles.saved.map((r) => {
      const profile = profiles.find((p) => p.id === r.profile_id) || null;
      return { r, profile, changed: Boolean(profile && !startProfiles.sameConditions(r, profile)) };
    });
    // 처음에는 고른 재무정보로 거른다. 그 재무정보로 찜한 것이 없으면 전체
    const current = startProfiles.selected();
    const keys = ['all', 'deleted', ...profiles.map((p) => p.id)];
    if (startProfiles.savedFilter === null || !keys.includes(startProfiles.savedFilter)) {
      startProfiles.savedFilter = current && items.some((it) => it.profile && it.profile.id === current.id) ? current.id : 'all';
    }
    const filter = startProfiles.savedFilter;
    const matches = (it, key) => key === 'all' || (key === 'deleted' ? !it.profile : Boolean(it.profile && it.profile.id === key));

    const chips = startProfiles.el('div', 'saved-chips');
    const chipList = [{ key: 'all', label: '전체' }, ...profiles.map((p) => ({ key: p.id, label: p.name }))];
    if (items.some((it) => !it.profile)) chipList.push({ key: 'deleted', label: PROFILE_TEXT.deleted });
    chipList.forEach((c) => {
      const chip = startProfiles.el('button', 'saved-chip');
      chip.type = 'button';
      chip.setAttribute('aria-pressed', String(filter === c.key));
      chip.append(c.label, startProfiles.el('span', 'saved-chip__count', String(items.filter((it) => matches(it, c.key)).length)));
      chip.addEventListener('click', () => {
        startProfiles.savedFilter = c.key;
        startProfiles.drawSaved();
      });
      chips.append(chip);
    });

    const shown = items.filter((it) => matches(it, filter));
    const parts = [...head, chips];
    if (!shown.length) {
      parts.push(startProfiles.el('p', 'saved-empty', items.length ? PROFILE_TEXT.savedNoneHere : PROFILE_TEXT.savedNone));
    } else {
      const list = startProfiles.el('ul', 'saved__list');
      shown.forEach((it) => {
        const li = startProfiles.el('li', 'saved-section__item');
        li.append(startProfiles.savedCard(it), startProfiles.heart(it.r));
        list.append(li);
      });
      parts.push(list);
    }
    box.replaceChildren(...parts);
  },

  // 찜 카드: 위 줄(꼬리표 | 꼬리표 … 구분 배지), 이름, 면적 · 여유/부족, 선 아래 조건 한 줄과 그 아래 찜한 날짜
  savedCard({ r, profile, changed }) {
    const el = startProfiles.el;
    const short = (amount) => (amount === 0 ? '0원' : format.won(amount).replace(/ 원$/, ''));
    const link = el('a', 'saved__card');
    link.href = `saved.html?id=${r.id}`;
    const tags = el('div', 'saved-tags');
    tags.append(el('span', 'saved-tag', profile ? profile.name : PROFILE_TEXT.deleted));
    if (changed) tags.append(el('span', 'saved-tag', PROFILE_TEXT.changed));
    tags.append(el('span', `badge badge--${r.category} saved-badge`, PROFILE_CATEGORY_NAMES[r.category]));
    const result = el('p', 'saved__card-result');
    result.append(`${format.area(r.apartment.supply_area, r.apartment.exclusive_area, 'm2')} · `,
      el('span', `amount--${r.category}`, r.shortage > 0 ? `부족 ${format.won(r.shortage)}` : `여유 ${format.won(-r.shortage)}`));
    const years = r.target_years === 0 ? '지금' : `${r.target_years}년`;
    const loan = r.loan.choice === 'product' ? `${r.loan.product_name} ${r.loan.repayment_years}년` : '대출 없이';
    const conditions = el('p', 'saved__card-conditions');
    conditions.append(el('span', 'saved-cond', `보유 ${short(r.current_assets)} · 월 ${short(r.monthly_saving)} · ${years} · ${loan}`),
      el('span', 'saved-date', `${r.created_at.slice(0, 10)} 찜`));
    link.append(tags, el('strong', 'saved__card-name', r.apartment.name), result, conditions);
    return link;
  },

  // ♥ 를 누르면 찜 해제(A-35)하고 ♡ 로 바꾼다. 카드는 새로 고치거나 다른 화면에 다녀올 때까지 그 자리에 둔다.
  // ♡ 를 다시 누르면 같은 아파트 · 면적 · 조건으로 다시 찜한다 (A-21. 그때의 평균가로 다시 계산된다)
  heart(r) {
    const heart = startProfiles.el('button', 'saved-heart');
    heart.type = 'button';
    const off = startProfiles.offIds.has(r.id);
    heart.setAttribute('aria-pressed', String(!off));
    heart.setAttribute('aria-label', off ? `${r.apartment.name} 다시 찜하기` : `${r.apartment.name} 찜 해제하기`);
    heart.innerHTML = off ? PROFILE_ICONS.heart : PROFILE_ICONS.heartOn;
    heart.addEventListener('click', () => (off ? startProfiles.resave(r) : startProfiles.unsave(r)));
    return heart;
  },

  async unsave(r) {
    try {
      await api.delete(`/api/saved-results/${r.id}`);
    } catch (error) {
      if (error.status !== 404) {
        startProfiles.toast(error.status >= 400 && error.status < 500 ? error.detail : PROFILE_TEXT.unsaveFailed);
        return;
      }
    }
    startProfiles.offIds.add(r.id);
    startProfiles.drawSaved();
  },

  async resave(r) {
    if (r.apartment.id === null) {
      startProfiles.toast(PROFILE_TEXT.resaveNoApartment);
      return;
    }
    const product = r.loan.choice === 'product';
    const body = {
      conditions: {
        current_assets: r.current_assets, monthly_saving: r.monthly_saving, target_years: r.target_years,
        loan_choice: r.loan.choice, loan_product_id: product ? r.loan.product_id : null,
        repayment_years: product ? r.loan.repayment_years : null,
      },
      apartment_id: r.apartment.id,
      area_band: r.apartment.area_band,
    };
    if (startProfiles.profiles.some((p) => p.id === r.profile_id)) body.profile_id = r.profile_id;
    try {
      const saved = await api.post('/api/saved-results', body);
      // 같은 자리에 새 찜으로 바꿔 둔다
      startProfiles.saved = startProfiles.saved.map((x) => (x.id === r.id ? saved : x));
      startProfiles.offIds.delete(r.id);
    } catch (error) {
      startProfiles.toast(error.status >= 400 && error.status < 500 ? error.detail : PROFILE_TEXT.resaveFailed);
      return;
    }
    startProfiles.drawSaved();
  },

  toast(text) {
    let bar = startProfiles.$('start-toast');
    if (!bar) {
      bar = startProfiles.el('p', 'snackbar start-toast');
      bar.id = 'start-toast';
      bar.setAttribute('role', 'alert');
      document.body.append(bar);
    }
    bar.textContent = text;
    bar.hidden = false;
    clearTimeout(startProfiles.toastTimer);
    startProfiles.toastTimer = setTimeout(() => { bar.hidden = true; }, 4000);
  },

  // ───────── 작은 도구 ─────────

  iconButton(icon, label, className = 'profile-icon-button') {
    const button = startProfiles.el('button', className);
    button.type = 'button';
    button.setAttribute('aria-label', label);
    button.innerHTML = PROFILE_ICONS[icon]; // 고정된 그림
    return button;
  },

  el(tag, className, text) {
    const node = document.createElement(tag);
    if (className) node.className = className;
    if (text !== undefined) node.textContent = text;
    return node;
  },
};
