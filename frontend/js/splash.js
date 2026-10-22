// 스플래시. 탭을 처음 열 때만 파란 화면에 로고를 잠깐 보여 준다 (2026-10-19 팀장 결정).
//
// 봤다는 표시는 store의 place 묶음에 splash_seen으로 둔다. 탭을 닫으면 지워지므로 새 탭에서는 다시 뜬다.
// 같은 탭에서 시작 화면으로 돌아올 때(로그인 시간이 끝남, 다른 화면에서 돌아옴, 새로 고침)는 뜨지 않는다.
// 스플래시가 떠 있는 동안에도 시작 화면은 뒤에서 그대로 준비된다 (index.js).

(() => {
  const SHOW_MS = 1000; // 보여 주는 시간
  const FADE_MS = 300; // 사라지는 시간. index.css의 .splash transition과 같다

  const splash = document.getElementById('splash');
  if (!splash) return;

  if (store.get('place').splash_seen === true) {
    splash.remove();
    return;
  }

  store.set('place', { splash_seen: true });
  splash.hidden = false;

  setTimeout(() => {
    splash.classList.add('splash--leaving');
    setTimeout(() => splash.remove(), FADE_MS);
  }, SHOW_MS);
})();
