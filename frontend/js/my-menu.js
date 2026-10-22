// 지도 화면의 마이페이지 메뉴 (2026-10-21). 담당: 박채은
//
// 모바일에는 헤더가 없으므로, 로그인했으면 내 조건 줄의 "로그인" 자리에 "마이페이지 ▾"를 둔다 (화면 설계서 2.2).
// 안세환의 map-view.js가 로그인한 것을 확인한 뒤 myMenu.attach(로그인 링크)를 부른다.
//
//   내 조건      지금 고른 재무정보 이름 ›   → 시작 화면(재무정보 3칸)
//   찜한 시나리오                           → 시작 화면 아래의 찜 목록 (index.html#saved)
//   로그아웃 (빨간 글자)                     → 로그아웃하고 시작 화면
//
// 내 조건 줄의 문장 앞에도 지금 고른 재무정보 이름을 붙인다 ("재무정보 1 · 3년 뒤 목표 가능 가격 …").
// 재무정보 이름은 사용자가 지은 글자라 textContent로 넣는다.

const MY_MENU_START_PAGE = 'index.html';
const MY_MENU_CARET = '<svg width="10" height="10" viewBox="0 0 12 12" aria-hidden="true"><path d="M1.5 3.5h9L6 9z" fill="currentColor"/></svg>';

const myMenu = {
  button: null,
  menu: null,

  attach(link) {
    if (!link || myMenu.button) return;
    const name = store.get('place').profile_name;
    const sentence = document.getElementById('condition-sentence');
    if (sentence && name) {
      const label = myMenu.make('span', 'condition-bar__profile', `${name} ·`);
      sentence.before(label);
    }

    link.hidden = true;
    const button = myMenu.make('button', 'condition-bar__link my-menu__button');
    button.type = 'button';
    button.setAttribute('aria-haspopup', 'menu');
    button.setAttribute('aria-expanded', 'false');
    button.append('마이페이지');
    button.insertAdjacentHTML('beforeend', MY_MENU_CARET); // 고정된 그림
    button.addEventListener('click', (event) => {
      event.stopPropagation();
      if (myMenu.menu) myMenu.close();
      else myMenu.open();
    });
    link.after(button);
    myMenu.button = button;
  },

  open() {
    const name = store.get('place').profile_name;
    const menu = myMenu.make('nav', 'my-menu');
    menu.setAttribute('aria-label', '마이페이지');
    const rect = myMenu.button.getBoundingClientRect();
    menu.style.top = `${rect.bottom + 4}px`;
    menu.style.right = `${Math.max(8, window.innerWidth - rect.right)}px`;

    const cond = myMenu.item('내 조건', () => { location.href = MY_MENU_START_PAGE; });
    if (name) cond.append(myMenu.make('span', 'my-menu__now', `${name} ›`));
    const saved = myMenu.item('찜한 시나리오', () => { location.href = `${MY_MENU_START_PAGE}#saved`; });
    const out = myMenu.item('로그아웃', async () => {
      await account.logout();
      location.href = MY_MENU_START_PAGE;
    });
    out.classList.add('my-menu__item--out');
    menu.append(cond, saved, out);
    document.body.append(menu);
    myMenu.menu = menu;
    myMenu.button.setAttribute('aria-expanded', 'true');
    document.addEventListener('click', myMenu.onOutside);
    document.addEventListener('keydown', myMenu.onOutside);
  },

  close() {
    if (myMenu.menu) myMenu.menu.remove();
    myMenu.menu = null;
    if (myMenu.button) myMenu.button.setAttribute('aria-expanded', 'false');
    document.removeEventListener('click', myMenu.onOutside);
    document.removeEventListener('keydown', myMenu.onOutside);
  },

  // 메뉴 밖을 누르거나 Esc를 누르면 닫는다
  onOutside(event) {
    if (event.type === 'keydown' && event.key !== 'Escape') return;
    if (event.type === 'click' && myMenu.menu && myMenu.menu.contains(event.target)) return;
    myMenu.close();
  },

  item(text, onClick) {
    const button = myMenu.make('button', 'my-menu__item');
    button.type = 'button';
    button.append(myMenu.make('span', '', text));
    button.addEventListener('click', onClick);
    return button;
  },

  make(tag, className, text) {
    const node = document.createElement(tag);
    if (className) node.className = className;
    if (text !== undefined) node.textContent = text;
    return node;
  },
};
