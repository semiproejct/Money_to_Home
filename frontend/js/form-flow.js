// 입력 화면에서 휴대폰 키보드와 아래 버튼을 다루는 공통 동작 (2026-10-21, 팀장 요청)
//
// 기종마다 키보드가 다르게 떠서(갤럭시는 화면이 줄고, 아이폰은 키보드가 화면을 덮는다) 아래와 같이 맞춘다.
//   - 아래 버튼은 키보드 위로 따라 올라오지 않고 화면 맨 아래에 남는다 (css/common.css의 .form-page--keys .bottom-action).
//     화면 높이는 키보드가 없을 때의 높이(--app-height)로 잡아, 키보드가 떠서 화면이 줄어도 버튼이 입력란을 가리지 않는다.
//   - 키보드의 "다음"(Enter)을 누르면 다음 칸으로 간다. 아이폰 숫자 키패드에는 "다음"이 없어 ✓(키보드 닫기)로 간다 (onDone).
//   - 마지막 칸까지 넣으면 키보드를 내리고 버튼이 보이게 조금 내려 준다 (revealSubmit).
//
//   formFlow.onDone(input, callback, submit)  터치 화면에서 입력란을 떠날 때(✓) callback. submit 버튼을 눌러 떠난 것은 빼고 부른다
//   formFlow.revealSubmit(button)             키보드를 내리고 button이 화면에 들어오게 내린다
//   formFlow.enterToNext(inputs)              입력란에서 "다음"(Enter)을 누르면 보이는 다음 입력란으로. 마지막 칸의 Enter는 폼을 보낸다
//   formFlow.placeOf(el)                      el의 지금 화면 위치(위쪽 끝). 다음 칸으로 넘어가기 전에 잰다
//   formFlow.keepPlace(top, el)               새로 열린 칸 el이 방금 입력한 칸의 자리(top)에 오게 화면을 올린다.
//                                             키보드에 가려지지 않게 한다 (2026-10-21 팀장 요청)

const formFlow = (() => {
  const touch = window.matchMedia('(pointer: coarse)');
  let width = window.innerWidth;
  let height = window.innerHeight;

  // 키보드가 없을 때의 화면 높이. 키보드가 떠서 줄어든 높이는 쓰지 않는다. 폭이 바뀌면(가로·세로 돌림) 새로 잰다
  function measure() {
    if (window.innerWidth !== width) {
      width = window.innerWidth;
      height = window.innerHeight;
    } else {
      height = Math.max(height, window.innerHeight);
    }
    document.documentElement.style.setProperty('--app-height', `${height}px`);
  }
  measure();
  window.addEventListener('resize', measure);

  function onDone(input, callback, submit) {
    input.addEventListener('blur', (event) => {
      if (!touch.matches || document.visibilityState !== 'visible') return;
      if (submit && event.relatedTarget === submit) return; // 버튼을 눌렀으면 버튼이 처리한다
      callback();
    });
  }

  // 올릴 만큼 아래가 모자라면 화면 맨 아래에 빈 자리를 잠깐 더한다 (body의 아래 여백). 다 넣으면(revealSubmit) 뺀다
  let extra = 0;
  function placeOf(el) {
    return el.getBoundingClientRect().top;
  }
  function keepPlace(top, el) {
    if (!touch.matches) return;
    // 브라우저가 커서를 둔 칸을 먼저 제 나름대로 보이게 옮기므로, 그 뒤에 잰다
    setTimeout(() => moveTo(top, el), 60);
  }
  function moveTo(top, el) {
    // 그 자리에 와도 입력란이 키보드에 걸치면 조금 더 올린다 (보이는 높이는 visualViewport. 아이폰은 키보드가 화면을 덮는다)
    const input = el.querySelector('input') || el;
    const visible = window.visualViewport ? window.visualViewport.height : window.innerHeight;
    const distance = Math.max(el.getBoundingClientRect().top - top, input.getBoundingClientRect().bottom + 16 - visible);
    if (distance <= 0) return;
    const root = document.documentElement;
    const room = root.scrollHeight - root.clientHeight - window.scrollY; // 더 내릴 수 있는 길이 (레이아웃 높이 기준)
    if (room < distance) {
      extra += Math.ceil(distance - room);
      document.body.style.paddingBottom = `${extra}px`;
    }
    window.scrollBy({ top: distance, behavior: 'smooth' });
  }

  function revealSubmit(button) {
    extra = 0;
    document.body.style.paddingBottom = '';
    if (document.activeElement && document.activeElement !== document.body) document.activeElement.blur();
    // 키보드가 내려가 화면 높이가 돌아온 뒤에 내린다
    setTimeout(() => button.scrollIntoView({ block: 'end', behavior: 'smooth' }), 250);
  }

  function enterToNext(inputs) {
    inputs.forEach((input, index) => {
      input.setAttribute('enterkeyhint', index === inputs.length - 1 ? 'go' : 'next');
      input.addEventListener('keydown', (event) => {
        if (event.key !== 'Enter' || event.isComposing) return;
        const following = inputs.slice(index + 1).find((next) => next.offsetParent !== null && !next.disabled);
        if (!following) return; // 다음 칸이 없으면 폼을 보낸다
        event.preventDefault();
        following.focus();
      });
    });
  }

  return { onDone, revealSubmit, enterToNext, placeOf, keepPlace };
})();
