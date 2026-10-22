// P-01 시작 화면. 담당: 김해원
//
// 로그인 상태에 따라 보여 준다 (와이어프레임 P-01).
//   ① 로그인하지 않음            "로그인 없이 시작하기", "로그인 | 회원가입"
//   로그인                       재무정보 3칸 + 찜한 시나리오 (2026-10-21, 박채은의 js/start-profiles.js. 화면 설계서 4.3.1)
//                                예전의 ② 저장한 정보 일곱 줄과 ③ "시작하기"를 대신한다
//   ④ 저장한 정보를 불러오지 못함  "다시 시도", "새로 입력하기"
//   ⑤ 로그인 시간이 끝남         ①과 같고 로고 자리에 안내. account.js가 표시를 남기고 이 화면으로 보낸다
//
// "로그인 없이 시작하기"는 이 탭에서 입력하던 값이 있으면 보던 자리로 보낸다 (FR-PROFILE-11).
//   값이 없으면 재무정보, 재무정보만 있으면 대출상품, 대출 선택까지 있으면 저축 계획, 다 있으면 지도.
// 값은 탭을 닫으면 사라진다. 서버에서 온 글자는 textContent로 넣는다.

(() => {
  const $ = (id) => document.getElementById(id);
  const startButton = $('start-button');

  // 화면의 부품을 보이고 숨긴다. names에 있는 것만 보인다.
  const PARTS = ['start-logo', 'start-switch-row', 'start-error', 'start-steps', 'start-notice', 'start-button',
    'start-retry', 'start-restart', 'start-auth', 'start-hint'];
  function showOnly(names) {
    PARTS.forEach((id) => { $(id).hidden = !names.includes(id); });
  }

  // 제목. "home2026님," 다음 줄에 문장을 둔다
  function setTitle(lines) {
    const title = $('start-title');
    title.replaceChildren();
    lines.forEach((line, i) => {
      if (i > 0) title.append(document.createElement('br'));
      title.append(document.createTextNode(line));
    });
  }

  // 처음부터 다시: 이 탭의 값을 지우고 재무정보의 첫 질문부터. 저장한 값은 새 값을 저장할 때 바뀐다.
  function restart() {
    store.clear('input');
    store.clear('map');
    store.set('place', { restart: true, profile_step: null, summary_edit: false });
    location.href = 'profile.html';
  }

  // ① 로그인하지 않음 (⑤면 로고 자리에 안내)
  function showGuest(expired) {
    startProfiles.hide();
    showOnly(['start-logo', 'start-steps', 'start-notice', 'start-button', 'start-auth', 'start-hint']);
    $('start-expired').hidden = !expired;
    $('start-logo').hidden = expired;
    startButton.textContent = '로그인 없이 시작하기';
    startButton.href = guard.resumePage();
    startButton.onclick = null;
  }

  // ④ 불러오지 못함
  function showLoadFail() {
    startProfiles.hide();
    showOnly(['start-error', 'start-retry', 'start-restart']);
    $('start-expired').hidden = true;
    setTitle(['저장한 정보를 불러오지 못했습니다']);
    $('start-subtitle').textContent = '';
    $('start-restart').textContent = '새로 입력하기';
  }

  // 로그인: 재무정보 3칸 + 찜한 시나리오 (2026-10-21). 받지 못하면 ④
  async function showMember(loginId) {
    showOnly(['start-switch-row']);
    $('start-expired').hidden = true;
    try {
      await startProfiles.show(loginId);
    } catch (error) {
      if (error.status === 401) {
        showGuest(false); // 그사이 로그인이 풀렸다
        return;
      }
      showLoadFail();
    }
  }

  async function start() {
    const expired = account.takeExpired();
    showGuest(expired); // 물어보는 동안에는 기본 화면을 둔다
    const loginId = await account.me();
    if (loginId) await showMember(loginId);
    else showGuest(expired || account.takeExpired());
  }

  $('start-retry').addEventListener('click', () => start());
  $('start-restart').addEventListener('click', restart);
  start();
})();
