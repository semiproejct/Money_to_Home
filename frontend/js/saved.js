// 찜한 시나리오 하나 열어 보기 (P-09, 3차). 담당: 박채은
//
//   saved.html?id=3   하나 열어 보기 (C3). A-23 GET /api/saved-results/3
//   saved.html        목록은 로그인한 시작 화면 아래로 옮겼다 (2026-10-21). index.html#saved로 보낸다
//
// 로그인해야 볼 수 있다. 401일 때
//   - 로그인한 채 쓰다가 30분이 지나 풀렸으면 시작 화면에 "로그아웃되었습니다" 안내를 띄운다 (P-01 ⑤, js/account.js)
//   - 처음부터 로그인하지 않았으면 로그인 화면으로 보낸다
// 찜한 그대로 보여 주고 다시 계산하지 않는다. 결과 상자와 값 줄은 시나리오 탭(scenario.js)의 함수로 그린다.
// 이름 줄 오른쪽 끝의 ♥를 누르면 찜 해제(A-35), ♡를 다시 누르면 같은 조건으로 다시 찜한다(A-21) (2026-10-21).
// 받는 동안은 회색 자리 표시(스켈레톤)를 둔다 (FR-COMMON-10).
// 글자는 textContent로 넣는다. 금액은 format.won으로 보여 준다.

const SAVED_TEXT = {
  failed: '찜한 시나리오를 불러오지 못했습니다.',
  notFound: '저장한 결과를 찾을 수 없습니다.', // 서버의 404 문장과 같다 (backend/services/saved_result.py)
  retry: '다시 시도',
  loading: '불러오는 중',
  detailNote: '찜했을 때의 조건과 평균가로 계산한 값입니다. 지금의 평균가와 다를 수 있습니다.',
  toMap: '지도에서 이 아파트 보기',
  heartOn: '찜 해제하기',
  heartOff: '다시 찜하기',
  unsaveFailed: '찜을 해제하지 못했습니다. 잠시 후 다시 시도해 주세요.',
  resaveFailed: '다시 찜하지 못했습니다. 잠시 후 다시 시도해 주세요.',
};
const SAVED_CATEGORY_NAMES = { now: '지금 가능', within: '기간 내 가능', lack: '자금 부족' };
const SAVED_LIST_PAGE = 'index.html#saved'; // 찜 목록 (로그인한 시작 화면 아래)

const saved = {
  main: document.getElementById('saved-main'),
  item: null, // 지금 보는 찜 (A-23 응답)
  off: false, // ♡로 바꿨는가 (찜 해제함)

  start() {
    const id = new URLSearchParams(location.search).get('id');
    if (id === null) {
      location.replace(SAVED_LIST_PAGE);
      return;
    }
    document.getElementById('saved-back').href = SAVED_LIST_PAGE; // ‹ 는 찜 목록으로
    // 번호가 아닌 값(?id=abc, ?id=)은 서버에 묻지 않고 "찾을 수 없습니다"로 둔다
    if (!/^\d+$/.test(id)) {
      saved.main.replaceChildren(saved.failBox({ status: 404 }));
      return;
    }
    saved.load(`/api/saved-results/${id}`);
  },

  // 받는 동안은 자리 표시, 받지 못하면 오류 상자
  async load(path) {
    saved.main.replaceChildren(...saved.oneSkeleton());
    try {
      saved.item = await api.get(path);
      saved.drawOne(saved.item);
    } catch (error) {
      if (error.status === 401) {
        saved.toLogin();
        return;
      }
      saved.main.replaceChildren(saved.failBox(error, () => saved.load(path)));
    }
  },

  // 401. 로그인한 채 쓰다가 풀렸는지는 account.js가 안다 (place.login_id).
  // 풀렸으면 account.me()가 시작 화면으로 보내고 안내 표시(place.expired)를 남긴다 (P-01 ⑤). 아니면 로그인 화면으로
  async toLogin() {
    await account.me();
    if (store.get('place').expired === true) return;
    // 로그인한 뒤 보던 이 화면(?id=번호)으로 돌아오게 넘긴다 (auth.js의 next)
    location.href = `login.html?next=${encodeURIComponent(location.pathname.slice(1) + location.search)}`;
  },

  // ───────── 하나 열어 보기 (C3) ─────────

  drawOne(item) {
    const head = saved.make('div', 'saved__head');
    const titleRow = saved.make('div', 'saved__title-row');
    titleRow.append(
      saved.make('h1', 'title saved__name', item.apartment.name),
      saved.make('span', `badge badge--${item.category}`, SAVED_CATEGORY_NAMES[item.category]),
      saved.heart(),
    );
    head.append(titleRow, saved.make('p', 'saved__meta', `${saved.area(item.apartment)} · ${saved.day(item.created_at)}에 찜`));

    const parts = [head, scenarioView.resultBox(item), scenarioView.rows(item)];
    parts.push(saved.make('p', 'saved__note', SAVED_TEXT.detailNote));

    // 원래 아파트가 지워졌으면 지도로 갈 수 없다
    if (item.apartment.id !== null) {
      const toMap = saved.make('button', 'button button--primary saved__to-map', SAVED_TEXT.toMap);
      toMap.type = 'button';
      toMap.addEventListener('click', () => {
        // 지금의 조건으로 그 아파트가 있는 동을 지도에 연다 (C3). 아파트 창을 여는 것은 지도 화면의 일이다
        store.set('map', { gu: item.apartment.gu, dong: item.apartment.dong, open_region: true }); // 광주 전체가 아니라 이 동으로 연다
        location.href = 'map.html';
      });
      parts.push(toMap);
    }
    saved.main.replaceChildren(...parts);
  },

  // 이름 줄 오른쪽 끝의 ♥ (2026-10-21). 누르면 ♡ (찜 해제), 다시 누르면 같은 조건으로 다시 찜.
  // ♡인 채로 ‹ 를 눌러 목록에 가면 그 카드는 빠져 있다
  heart() {
    const heart = saved.make('button', 'saved__heart');
    heart.type = 'button';
    heart.setAttribute('aria-pressed', String(!saved.off));
    heart.setAttribute('aria-label', saved.off ? SAVED_TEXT.heartOff : SAVED_TEXT.heartOn);
    heart.innerHTML = saved.off ? SCENARIO_ICONS.heart : SCENARIO_ICONS.heartOn; // 고정된 그림 (scenario.js)
    heart.addEventListener('click', async () => {
      heart.disabled = true;
      if (saved.off) await saved.resave();
      else await saved.unsave();
      heart.replaceWith(saved.heart());
    });
    return heart;
  },

  async unsave() {
    try {
      await api.delete(`/api/saved-results/${saved.item.id}`);
    } catch (error) {
      if (error.status !== 404) {
        scenarioView.toast(error.status >= 400 && error.status < 500 ? error.detail : SAVED_TEXT.unsaveFailed);
        return;
      }
    }
    saved.off = true;
  },

  // 같은 아파트 · 면적 · 조건 · 재무정보로 다시 찜한다. 새 번호가 생기므로 주소도 바꿔 둔다
  async resave() {
    const item = saved.item;
    const product = item.loan.choice === 'product';
    const body = {
      conditions: {
        current_assets: item.current_assets, monthly_saving: item.monthly_saving, target_years: item.target_years,
        loan_choice: item.loan.choice, loan_product_id: product ? item.loan.product_id : null,
        repayment_years: product ? item.loan.repayment_years : null,
      },
      apartment_id: item.apartment.id,
      area_band: item.apartment.area_band,
    };
    if (item.profile_id !== null) body.profile_id = item.profile_id;
    try {
      const again = await api.post('/api/saved-results', body);
      saved.item = { ...item, id: again.id, profile_id: again.profile_id };
      history.replaceState(null, '', `saved.html?id=${again.id}`);
      saved.off = false;
    } catch (error) {
      scenarioView.toast(error.status >= 400 && error.status < 500 ? error.detail : SAVED_TEXT.resaveFailed);
    }
  },

  // ───────── 받는 중 (회색 자리 표시), 받지 못함 ─────────

  // 이름·배지와 찜한 날짜 자리, 그 아래 결과 상자와 값 줄 자리 (시나리오 탭의 자리 표시)
  oneSkeleton() {
    const head = saved.make('div', 'saved__head');
    head.setAttribute('aria-hidden', 'true');
    head.append(saved.bone('saved__bone--title'), saved.bone('saved__bone--meta'));
    return [head, scenarioView.skeleton(SAVED_TEXT.loading)];
  },

  bone(className) {
    return saved.make('span', `scenario__bone ${className}`);
  },

  // 404(없거나 남의 것)는 다시 시도해도 같으므로 "다시 시도"를 두지 않는다.
  // 서버 오류와 연결 문제는 안의 사정을 보이지 않고 한 문장으로 알린다 (FR-COMMON-07)
  failBox(error, retryFn) {
    const box = saved.make('div', 'notice notice--error saved__fail');
    box.setAttribute('role', 'alert');
    const notFound = error.status === 404 || error.status === 422;
    box.append(saved.make('span', '', notFound ? SAVED_TEXT.notFound : SAVED_TEXT.failed));
    if (!notFound) {
      const retry = saved.make('button', 'link-button', SAVED_TEXT.retry);
      retry.type = 'button';
      retry.addEventListener('click', retryFn);
      box.append(retry);
    }
    return box;
  },

  // ───────── 작은 도구 ─────────

  day: (createdAt) => createdAt.slice(0, 10), // "2026-10-14T11:20:00" → "2026-10-14"

  area: (apartment) => format.area(apartment.supply_area, apartment.exclusive_area, 'm2'),

  make: (tag, className, text) => scenarioView.make(tag, className, text),
};

saved.start();
