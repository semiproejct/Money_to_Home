// 이름 검색 (P-05 ⑭ 검색 결과, ⑮ 검색 결과 없음). 담당: 김목산
//
// 지도의 검색창에 아파트 이름을 적으면 광주 5개 구 전체에서 찾아 검색창 아래에 결과를 보여 준다 (FR-MAP-08).
// 지도 화면에 묶이지 않는다. 결과를 그릴 요소와 검색창을 받아 그 안에만 그린다.
//
//   <div id="search-results" hidden></div>   (map.html. 검색 줄과 같은 부모 안에. 모양과 자리는 search.css가 붙인다)
//
//   searchView.open(요소, (apartment) => { ... }, { input: 검색창 });
//     요소     : 결과를 그릴 자리
//     onPick   : 결과를 누르면 결과 창을 닫고 부른다. apartment는 A-05 응답의 아파트 하나 그대로다
//                (id, name, gu, dong, latitude, longitude, category, areas ...). 지도를 옮기고 30% 창을 여는 데 쓴다
//     input    : 검색창 (<input>). 없으면 document.querySelector('.search-box__input')
//   searchView.close();     결과 창을 닫고 검색창에서 손을 뗀다 (검색창의 글자는 그대로 둔다)
//   searchView.isOpen();
//
// 검색창에 글자를 적을 때마다 잠깐 기다렸다가 A-05를 keyword로 부른다 (where: { keyword }).
// 조건은 guard.conditions()가 만든다. 면적·가격·준공 연도 조건은 보내지 않는다 (이름으로만 찾는다).
// 서버에서 온 글자는 textContent로 넣는다. innerHTML을 쓰지 않는다.

const SEARCH_TEXT = {
  noneTitle: '검색 결과가 없습니다.',
  noneHelp: '아파트 이름을 다시 확인해 주세요. 최근 1년 거래가 없는 아파트는 나오지 않습니다.',
  loadFail: '아파트를 불러오지 못했습니다. 잠시 후 다시 시도해 주세요.', // 지도 화면과 같은 문장 (와이어프레임 P-04 ⑩)
  noCoord: '위치 없음',
};

const SEARCH_BADGE = { now: '지금 가능', within: '기간 내 가능', lack: '자금 부족' };

const SEARCH_WAIT = 250; // 글자를 적고 이만큼(ms) 멈추면 찾는다

const searchView = (() => {
  let container = null;
  let input = null;
  let onPick = null;
  let timer = null;
  let seq = 0; // 늦게 온 앞의 응답이 뒤의 결과를 덮지 않게 요청마다 번호를 붙인다
  let listeners = [];

  function el(tag, className, text) {
    const node = document.createElement(tag);
    if (className) node.className = className;
    if (text !== undefined && text !== null) node.textContent = text;
    return node;
  }

  function on(target, type, handler) {
    target.addEventListener(type, handler);
    listeners.push(() => target.removeEventListener(type, handler));
  }

  function show(...children) {
    container.replaceChildren(...children);
    container.hidden = children.length === 0;
  }

  // 결과 창을 닫는다. 기다리는 검색과 오고 있는 응답도 버린다 (닫은 뒤에 결과가 다시 뜨지 않게)
  function hide() {
    clearTimeout(timer);
    seq += 1;
    show();
  }

  function row(apartment) {
    const item = el('li', 'search-view__item');
    const button = el('button', 'search-view__row');
    button.type = 'button';
    const text = el('span', 'search-view__text');
    text.append(el('span', 'search-view__name', apartment.name));
    const place = el('span', 'search-view__place', `${apartment.gu} ${apartment.dong}`);
    if (apartment.latitude === null || apartment.longitude === null) {
      place.append(el('span', 'search-view__tag', SEARCH_TEXT.noCoord));
    }
    text.append(place);
    button.append(text, el('span', `badge badge--${apartment.category}`, SEARCH_BADGE[apartment.category]));
    // 누르면 결과 창만 닫는다. 검색창은 계속 쓸 수 있다
    button.addEventListener('click', () => {
      hide();
      input.blur();
      if (onPick) onPick(apartment);
    });
    item.append(button);
    return item;
  }

  function message(title, help, error) {
    const box = el('div', error ? 'search-view__box search-view__box--error' : 'search-view__box');
    box.setAttribute('role', error ? 'alert' : 'status');
    box.append(el('p', 'search-view__title', title));
    if (help) box.append(el('p', 'search-view__help', help));
    return box;
  }

  async function find(keyword) {
    const mine = ++seq;
    try {
      const result = await api.post('/api/apartments/search', { conditions: guard.conditions(), where: { keyword } });
      if (mine !== seq || !container) return;
      if (result.apartments.length === 0) {
        show(message(SEARCH_TEXT.noneTitle, SEARCH_TEXT.noneHelp));
        return;
      }
      const list = el('ul', 'search-view__list');
      list.setAttribute('aria-label', '검색 결과');
      result.apartments.forEach((apartment) => list.append(row(apartment)));
      show(list);
      list.scrollTop = 0;
    } catch (error) {
      if (mine !== seq || !container) return;
      // 서버가 값을 거부했으면(422) 그 문장을, 아니면 불러오지 못했다는 문장을 보여 준다
      show(message(error.status === 422 ? error.detail : SEARCH_TEXT.loadFail, null, true));
    }
  }

  // 검색창의 글자가 바뀜. 앞뒤 빈칸을 빼고 비었으면 결과 창을 닫는다 (빈칸만 보내면 서버가 422로 거부한다)
  function onInput() {
    clearTimeout(timer);
    const keyword = input.value.trim();
    if (keyword === '') {
      hide();
      return;
    }
    timer = setTimeout(() => find(keyword), SEARCH_WAIT);
  }

  const view = {
    open(target, callback, options = {}) {
      if (container) view.close();
      container = target;
      container.classList.add('search-view');
      input = options.input || document.querySelector('.search-box__input');
      onPick = callback;
      container.hidden = true;

      on(input, 'input', onInput);
      // 검색창을 다시 누르면 적어 둔 글자로 다시 찾는다
      on(input, 'focus', () => { if (input.value.trim() !== '' && container.hidden) onInput(); });
      on(input, 'keydown', (event) => {
        if (event.key === 'Escape') {
          hide();
          input.blur();
        } else if (event.key === 'Enter') {
          event.preventDefault(); // 기다리지 않고 바로 찾는다
          clearTimeout(timer);
          const keyword = input.value.trim();
          if (keyword !== '') find(keyword);
        }
      });
      // 검색창과 결과 밖을 누르면 결과 창만 닫는다
      on(document, 'click', (event) => {
        if (!container.contains(event.target) && event.target !== input) hide();
      });
      if (input.value.trim() !== '') onInput();
    },

    close() {
      if (!container) return;
      clearTimeout(timer);
      seq += 1;
      listeners.forEach((off) => off());
      listeners = [];
      container.hidden = true;
      container.replaceChildren();
      container = null;
      input = null;
      onPick = null;
    },

    isOpen: () => Boolean(container) && !container.hidden,
  };
  return view;
})();
