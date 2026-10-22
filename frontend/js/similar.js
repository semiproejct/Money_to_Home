// 비슷한 아파트 (FR-APT-17, 3차). 담당: 김목산
//
// 아파트 정보 탭의 기본 정보 아래(와이어프레임 C6)에 고른 아파트와 가격이 비슷한 아파트를 여섯 곳씩 보여 준다 (2026-10-18, 예전에는 세 곳).
// 아파트 창에 묶이지 않는다. 그릴 요소를 받아 그 안에만 그린다. 카드 모양은 목록의 것(list.css의 .list-card)을 같이 쓴다.
//
//   <div id="apt-similar"></div>   (아파트 정보 탭. 기본 정보 아래)
//
//   similarView.load(요소, { apartmentId, areaBand }, { onPick });
//     apartmentId : 고른 아파트 번호
//     areaBand    : 고른 면적대. 이 면적의 평균가가 기준 가격이다
//     onPick      : 카드를 누르면 부른다. (apartment, areaBand) — apartment는 A-24 응답의 아파트 하나 그대로이고,
//                   areaBand는 카드에 보이던 면적대다. 그 아파트로 옮겨 가는 데 쓴다
//   similarView.clear(요소);   그린 것을 지운다 (다른 아파트로 옮겨 갈 때)
//
// A-24 POST /api/apartments/{id}/similar 를 부른다. 조건은 guard.conditions()가 만든다.
// 순서는 서버가 정한다: 같은 동 먼저, 그다음 같은 구의 다른 동. 그 안에서 고른 정렬(가격 · 면적 · 준공 연도)이 비슷한 순.
// '다른 곳 보기'를 누르면 다음 여섯 곳(next_offset)을 부르고, 끝까지 보면 처음 여섯 곳으로 돌아간다.
// 후보가 한 번에 보이는 수 이하면 '다른 곳 보기'를 두지 않는다.
// 서버에서 온 글자는 textContent로 넣는다. innerHTML을 쓰지 않는다.

const SIMILAR_TEXT = {
  title: '이 아파트와 비슷한 아파트', // "매물"은 쓰지 않는다 (판매 중인 매물이 아니라 실거래 기록이다)
  // 설명 줄. 정렬마다 다르다 (A-24의 sort)
  help: {
    similar: '같은 동부터 가장 비슷한 아파트순입니다.',
    area: '같은 동부터 면적이 가장 비슷한 아파트순입니다.',
    newest: '같은 동부터 새로 지은 아파트순입니다.',
  },
  more: '다른 곳 보기',
  sortArea: '면적순',
  sortNewest: '신축순',
  empty: '같은 구에 비교할 아파트가 없습니다.',
  loadFail: '비슷한 아파트를 불러오지 못했습니다.',
  retry: '다시 시도',
  noCoord: '위치 없음',
  overCap: '상한 초과',
  overCapHelp: '평균가가 고른 대출 상품의 대상 주택 가격 상한을 넘습니다. 이 상품으로는 대출을 받기 어려울 수 있습니다.',
};

const SIMILAR_BADGE = { now: '지금 가능', within: '기간 내 가능', lack: '자금 부족' };

const similarView = (() => {
  // 요소마다 지금 부르는 요청의 번호. 늦게 온 앞의 응답이 뒤의 결과를 덮지 않게 한다
  const seqs = new WeakMap();

  function el(tag, className, text) {
    const node = document.createElement(tag);
    if (className) node.className = className;
    if (text !== undefined && text !== null) node.textContent = text;
    return node;
  }

  // 정렬 (2026-10-18). 서버(A-24의 sort)가 후보 전체를 그 순서로 줄 세워 여섯 곳씩 준다.
  // 그래서 '다른 곳 보기'(↻)를 누르면 같은 순서로 다음 여섯 곳이 이어 나온다. 모두 같은 동이 먼저다.
  //   기본(아무것도 누르지 않음, similar): 이 아파트와 가격이 가장 비슷한 순
  //   면적순(area): 이 아파트의 고른 면적과 전용면적이 가장 비슷한 순
  //   신축순(newest): 준공 연도가 최근인 순 (모르는 곳은 뒤로)
  //   누른 버튼을 다시 누르면 기본으로 돌아간다. 다른 아파트로 옮겨 가도 고른 정렬은 남는다
  const sorts = new WeakMap(); // 요소 → 'similar' | 'area' | 'newest'
  const current = new WeakMap(); // 요소 → { target, handlers } (정렬을 바꾸면 처음부터 다시 부른다)
  const sortOf = (container) => sorts.get(container) || 'similar';

  function paintList(container, apartments, onPick) {
    const body = container.querySelector('.similar__body');
    if (!body) return;
    const list = el('ul', 'similar__list');
    list.setAttribute('aria-label', SIMILAR_TEXT.title);
    apartments.forEach((apartment) => list.append(card(apartment, onPick)));
    body.replaceChildren(list);
  }

  // 면적순 | 신축순. '다른 곳 보기'(↻)는 load()가 이 뒤에 붙인다
  function sortButtons(container) {
    const box = el('div', 'similar__sort');
    box.setAttribute('role', 'group');
    box.setAttribute('aria-label', '정렬');
    const mark = () => box.querySelectorAll('.similar__sort-option')
      .forEach((b) => b.setAttribute('aria-pressed', String(b.dataset.sort === sortOf(container))));
    [['area', SIMILAR_TEXT.sortArea], ['newest', SIMILAR_TEXT.sortNewest]].forEach(([value, text]) => {
      const button = el('button', 'similar__sort-option', text);
      button.type = 'button';
      button.dataset.sort = value;
      button.addEventListener('click', () => {
        sorts.set(container, sortOf(container) === value ? 'similar' : value);
        mark();
        const now = current.get(container);
        if (now) load(container, now.target, now.handlers, 0); // 그 순서의 처음 여섯 곳
      });
      box.append(button);
    });
    mark();
    return box;
  }

  // "평균 3억 원 · 여유 2,000만 원" 또는 "부족 2,500만 원". 부족자금이 음수면 여유다 (목록 카드와 같다)
  function moneyLine(area) {
    const line = el('p', 'list-card__money');
    line.append(el('span', null, `평균 ${format.won(area.avg_price)} · `));
    const gap = area.shortage > 0 ? `부족 ${format.won(area.shortage)}` : `여유 ${format.won(-area.shortage)}`;
    line.append(el('strong', `list-card__gap list-card__gap--${area.category}`, gap));
    return line;
  }

  // 카드 한 장. "109㎡ (전용 84㎡) · 서구 치평동" (와이어프레임 C6)
  function card(apartment, onPick) {
    const area = apartment.areas[0];
    const item = el('li', `list-card list-card--${area.category} similar__card`);
    const body = el('button', 'list-card__body');
    body.type = 'button';

    const head = el('div', 'list-card__head');
    head.append(el('h4', 'list-card__name', apartment.name));
    head.append(el('span', `badge badge--${area.category}`, SIMILAR_BADGE[area.category]));
    body.append(head);

    // "광산구 도천동 · 77㎡ (전용 59㎡) · 1997년 준공". 준공 연도를 모르면 그 칸을 뺀다
    const built = apartment.built_year ? ` · ${apartment.built_year}년 준공` : '';
    const meta = el('p', 'list-card__meta', `${apartment.gu} ${apartment.dong} · ${format.area(area.supply_area, area.exclusive_area)}${built}`);
    if (apartment.latitude === null || apartment.longitude === null) {
      meta.append(el('span', 'list-card__tag', SIMILAR_TEXT.noCoord));
    }
    if (area.over_price_cap) {
      const cap = el('span', 'list-card__tag list-card__tag--cap', SIMILAR_TEXT.overCap);
      cap.title = SIMILAR_TEXT.overCapHelp;
      meta.append(cap);
    }
    body.append(meta, moneyLine(area));
    body.setAttribute('aria-label', `${apartment.name}, ${apartment.gu} ${apartment.dong}, ${SIMILAR_BADGE[area.category]}`);
    body.addEventListener('click', () => onPick && onPick(apartment, area.area_band));
    item.append(body);
    return item;
  }

  function load(container, target, handlers = {}, offset = 0) {
    const mine = (seqs.get(container) || 0) + 1;
    seqs.set(container, mine);
    container.classList.add('similar');

    // 머리는 처음 한 번만 그린다. 다시 부를 때는 '다른 곳 보기'만 잠깐 끈다
    current.set(container, { target, handlers });
    let head = container.querySelector('.similar__head');
    if (!head) {
      head = el('div', 'similar__head');
      head.append(el('h3', 'similar__title', SIMILAR_TEXT.title), sortButtons(container));
      container.replaceChildren(head, el('p', 'similar__help'), el('div', 'similar__body'));
    }
    container.querySelector('.similar__help').textContent = SIMILAR_TEXT.help[sortOf(container)];
    const more = head.querySelector('.similar__more');
    if (more) more.disabled = true;
    const body = container.querySelector('.similar__body');
    container.setAttribute('aria-busy', 'true');

    api.post(`/api/apartments/${target.apartmentId}/similar`, {
      conditions: guard.conditions(),
      area_band: target.areaBand,
      offset,
      sort: sortOf(container),
    }).then((result) => {
      if (seqs.get(container) !== mine) return;
      container.removeAttribute('aria-busy');

      // 후보가 한 번에 보이는 것보다 많을 때만 '다른 곳 보기'
      let button = head.querySelector('.similar__more');
      if (result.total > result.apartments.length) {
        if (!button) {
          button = el('button', 'similar__more');
          button.type = 'button';
          button.setAttribute('aria-label', SIMILAR_TEXT.more);
          button.title = SIMILAR_TEXT.more;
          button.append(el('span', 'similar__more-icon', '↻'));
          head.querySelector('.similar__sort').append(button);
        }
        button.disabled = false;
        button.onclick = () => load(container, target, handlers, Number(button.dataset.next));
        button.dataset.next = String(result.next_offset);
      } else if (button) {
        button.remove();
      }

      if (result.apartments.length === 0) {
        body.replaceChildren(el('p', 'similar__empty', SIMILAR_TEXT.empty));
        return;
      }
      paintList(container, result.apartments, handlers.onPick);
    }).catch(() => {
      if (seqs.get(container) !== mine) return;
      container.removeAttribute('aria-busy');
      const box = el('div', 'similar__error');
      box.setAttribute('role', 'alert');
      const retry = el('button', 'similar__retry', SIMILAR_TEXT.retry);
      retry.type = 'button';
      retry.addEventListener('click', () => load(container, target, handlers, offset));
      box.append(el('p', 'similar__error-text', SIMILAR_TEXT.loadFail), retry);
      body.replaceChildren(box);
      const button = head.querySelector('.similar__more');
      if (button) button.disabled = false;
    });
  }

  return {
    load: (container, target, handlers) => load(container, target, handlers, 0),
    clear(container) {
      seqs.set(container, (seqs.get(container) || 0) + 1);
      current.delete(container);
      container.replaceChildren();
      container.removeAttribute('aria-busy');
    },
  };
})();
