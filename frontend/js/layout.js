// 화면의 공통 틀을 그린다 (FR-COMMON-04).
//
// 모바일에는 헤더가 없다 (확정 목업 v3). 웹(가로 1200px 이상)에서도 헤더 줄은 두지 않고,
// 로고만 왼쪽 위 회색 바탕에 띄운다 (2026-10-19 팀장 결정).
// HTML에 <header class="header" id="header"></header>가 있을 때만 아래가 동작한다. 지금은 입력 화면 여덟 개에 있다.
// 보이고 숨기는 것과 자리는 css/common.css의 "웹 배치"가 정한다.
//
//   로고와 서비스 이름. 누르면 시작 화면

function renderHeader() {
  const header = document.getElementById('header');
  if (!header) return;

  const home = document.createElement('a');
  home.className = 'header__home';
  home.href = 'index.html';

  const logo = document.createElement('img');
  logo.className = 'header__logo';
  logo.src = 'img/logo.svg?v=20261019-1';
  logo.alt = '';

  // 이름은 한 줄의 글자로 묶는다. 작은 "to"가 "머니", "홈"과 바닥선을 맞춰 앉는다.
  const name = document.createElement('span');
  name.className = 'header__name';
  const to = document.createElement('span');
  to.className = 'header__to';
  to.textContent = 'to';
  name.append('머니', to, '홈');

  home.append(logo, name);

  header.classList.add('header');
  header.replaceChildren(home);
}

document.addEventListener('DOMContentLoaded', renderHeader);
