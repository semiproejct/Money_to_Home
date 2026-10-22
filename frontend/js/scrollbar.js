// 모든 화면의 스크롤바 (2026-10-20 팀장).
// 브라우저 스크롤바는 자리를 차지해서 숨기고(common.css), 대신 스크롤하는 상자의 오른쪽 가장자리 위에 얇은 손잡이를 띄운다.
//   - 내용 위에 겹쳐 그려서 폭을 먹지 않는다
//   - 스크롤하거나 마우스를 가장자리에 올리면 보이고, 5초 동안 가만히 있으면 서서히 사라진다
//   - 손잡이를 끌어서 옮길 수도 있다
// 손잡이 하나(.scrollbar-thumb)를 화면에 고정해 두고, 지금 움직이는 상자에 맞춰 자리와 길이를 바꾼다.
// 웹은 화면 전체를 90%로 그리므로(common.css zoom) 잰 값(화면 px)을 zoom으로 나눠 CSS px로 쓴다.
(() => {
  const HIDE_MS = 5000; // 가만히 있으면 5초 뒤 사라진다 (2026-10-20 팀장)
  const EDGE = 12; // 오른쪽 끝에서 이만큼 안이면 마우스를 올린 것으로 본다
  const MIN = 24; // 손잡이 최소 길이

  const thumb = document.createElement('div');
  thumb.className = 'scrollbar-thumb';
  thumb.setAttribute('aria-hidden', 'true');
  let target = null; // 지금 손잡이가 붙은 스크롤 상자
  let timer = null;
  let drag = null;

  const zoom = () => parseFloat(getComputedStyle(document.documentElement).zoom) || 1;
  const isPage = (el) => el === document.scrollingElement || el === document.documentElement || el === document.body;

  const scrollable = (el) => {
    if (!el || el.nodeType !== 1) return false;
    if (el.scrollHeight - el.clientHeight < 2) return false;
    if (isPage(el)) return true;
    const y = getComputedStyle(el).overflowY;
    return y === 'auto' || y === 'scroll';
  };

  const frame = (el) => {
    if (isPage(el)) return { top: 0, left: 0, right: window.innerWidth, height: window.innerHeight };
    const r = el.getBoundingClientRect();
    return { top: r.top, left: r.left, right: r.right, height: r.height };
  };

  const place = () => {
    if (!target || !target.isConnected) return;
    const el = isPage(target) ? document.scrollingElement : target;
    const z = zoom();
    const box = frame(target);
    // 부모가 접혀 상자가 안 보이면 바로 숨긴다
    if (box.height < 1 || box.right - box.left < 1 || !scrollable(target)) {
      thumb.classList.add('scrollbar-thumb--gone'); // 서서히가 아니라 바로
      thumb.classList.remove('scrollbar-thumb--on');
      return;
    }
    thumb.classList.remove('scrollbar-thumb--gone');
    const ratio = el.clientHeight / el.scrollHeight;
    const length = Math.max(MIN * z, box.height * ratio);
    const room = box.height - length;
    const max = el.scrollHeight - el.clientHeight;
    const offset = max > 0 ? (el.scrollTop / max) * room : 0;
    thumb.style.top = `${(box.top + offset) / z}px`;
    thumb.style.left = `${(box.right - 8 * z) / z}px`;
    thumb.style.height = `${length / z}px`;
  };

  // 손잡이가 보이는 동안(사라지는 중 포함)은 매 프레임 상자를 따라간다.
  // 패널이 접히거나 펼쳐지며 상자가 움직여도 손잡이가 그 자리에 남지 않는다 (2026-10-20)
  let following = false;
  const follow = () => {
    place();
    if (thumb.classList.contains('scrollbar-thumb--on') || getComputedStyle(thumb).opacity !== '0') requestAnimationFrame(follow);
    else following = false;
  };

  const show = (el) => {
    if (!scrollable(el)) return;
    target = el;
    if (!thumb.isConnected) document.body.appendChild(thumb);
    place();
    thumb.classList.add('scrollbar-thumb--on');
    if (!following) {
      following = true;
      requestAnimationFrame(follow);
    }
    clearTimeout(timer);
    if (!drag) timer = setTimeout(() => thumb.classList.remove('scrollbar-thumb--on'), HIDE_MS);
  };

  document.addEventListener('scroll', (event) => {
    const el = event.target === document ? document.scrollingElement : event.target;
    show(el);
  }, { capture: true, passive: true });

  // 마우스를 상자의 오른쪽 가장자리에 올리면 보인다
  document.addEventListener('mousemove', (event) => {
    if (drag) return;
    let el = event.target;
    while (el && el.nodeType === 1) {
      if (scrollable(el)) {
        const box = frame(el);
        if (event.clientX >= box.right - EDGE && event.clientX <= box.right) show(el);
        return;
      }
      el = el.parentElement;
    }
    if (scrollable(document.scrollingElement) && event.clientX >= window.innerWidth - EDGE) show(document.scrollingElement);
  }, { passive: true });

  // 끌기
  thumb.addEventListener('pointerdown', (event) => {
    if (!target) return;
    event.preventDefault();
    const el = isPage(target) ? document.scrollingElement : target;
    drag = { y: event.clientY, top: el.scrollTop, el };
    thumb.setPointerCapture(event.pointerId);
    thumb.classList.add('scrollbar-thumb--drag');
    clearTimeout(timer);
  });
  thumb.addEventListener('pointermove', (event) => {
    if (!drag) return;
    const { el } = drag;
    const box = frame(target);
    const length = thumb.getBoundingClientRect().height;
    const room = box.height - length;
    const max = el.scrollHeight - el.clientHeight;
    if (room > 0) el.scrollTop = drag.top + ((event.clientY - drag.y) / room) * max;
  });
  const endDrag = () => {
    if (!drag) return;
    drag = null;
    thumb.classList.remove('scrollbar-thumb--drag');
    timer = setTimeout(() => thumb.classList.remove('scrollbar-thumb--on'), HIDE_MS);
  };
  thumb.addEventListener('pointerup', endDrag);
  thumb.addEventListener('pointercancel', endDrag);

  window.addEventListener('resize', place);
  // 접기 · 펴기는 html이나 패널의 속성(class · hidden · data-*)을 바꾼다. 바뀌는 즉시 맞춘다 (프레임을 기다리지 않는다)
  // 손잡이 자신의 class가 바뀐 것은 무시한다. 무시하지 않으면 place()가 class를 바꾸고 → 다시 불리는 것이 끝없이 돌아 화면이 멈춘다
  new MutationObserver((records) => {
    if (records.every((record) => record.target === thumb)) return;
    if (thumb.classList.contains('scrollbar-thumb--on')) place();
  }).observe(document.documentElement, { attributes: true, subtree: true, attributeFilter: ['class', 'hidden', 'data-map-web-fold', 'data-map-web-apt-fold', 'data-map-web-panel', 'data-sheet', 'data-stage'] });
  document.addEventListener('transitionend', () => {
    if (thumb.classList.contains('scrollbar-thumb--on')) place();
  }, true);
})();
