// 아파트 공유와 주소 복사 (3차, FR-APT-18. 와이어프레임 C6 "주소 복사해서 공유하기")
//
// 아파트 정보 탭에 끼워 넣는 부품이다. 끼워 넣는 일은 아파트 창 쪽에서 한다.
//
//   shareView.shareButton(() => target)       공유 아이콘 버튼. 누르면 공유 창을 연다
//   shareView.copyButton(() => text, label)   복사 아이콘 버튼. 누르면 글자를 클립보드에 넣고 "복사했습니다"를 띄운다
//   shareView.open(target)                    공유 창을 바로 연다
//   shareView.copy(text)                      클립보드에 넣는다. 되면 true
//   shareView.linkFor(target)                 공유 링크
//
//   target = { id, name, area_band, supply_area, exclusive_area } (A-05·A-06의 아파트와 고른 면적)
//
// 공유 창 (목업: 링크 화면 → "QR코드 보기" → QR 화면 → "링크로 돌아가기")
//   링크 화면: 아파트 이름과 면적, 공유 링크, [링크 복사], [QR코드 보기]
//   QR 화면 : 같은 링크의 QR코드. 휴대폰 카메라로 찍으면 링크가 열린다
//
// 공유 링크에는 아파트 번호와 면적만 넣는다. 재무정보(보유자산, 저축, 대출)는 넣지 않는다 (FR-APT-18).
//   예) http://localhost:8000/share.html?apt=623&area=84
//   링크를 연 사람은 공유받은 아파트 화면(share.html, share-page.js)을 본다. 입력이 없어도 열린다.
// 서버나 DB에서 온 글자는 textContent로만 넣는다. QR코드는 라이브러리 없이 이 파일에서 만든다 (qrCode 아래).

const SHARE_TEXT = {
  title: '아파트 공유하기',
  linkLead: '관심 있는 아파트를 공유해 보세요.',
  qrLead: 'QR코드를 스캔하면 아파트 정보로 이동해요.',
  linkLabel: '공유 링크',
  copyLink: '링크 복사',
  copied: '복사했습니다',
  showQr: 'QR코드 보기',
  backToLink: '링크로 돌아가기',
  close: '닫기',
  shareAria: '아파트 공유하기',
  copyFail: '복사하지 못했습니다. 길게 눌러 직접 복사해 주세요.',
  toastCopied: '복사했습니다.',
};

const SHARE_ICONS = {
  // 공유: 점 셋을 이은 모양 (목업의 머리 오른쪽)
  share: '<circle cx="18" cy="5" r="3"/><circle cx="6" cy="12" r="3"/><circle cx="18" cy="19" r="3"/><path d="M8.6 13.5l6.8 4M15.4 6.5l-6.8 4"/>',
  // 복사: 겹친 사각형 둘 (목업의 주소 오른쪽)
  copy: '<rect x="9" y="9" width="11" height="11" rx="2"/><path d="M5 15V6a2 2 0 0 1 2-2h8"/>',
  close: '<path d="M6 6l12 12M18 6L6 18"/>',
  home: '<path d="M4 11l8-7 8 7v8a1 1 0 0 1-1 1h-4v-6h-6v6H5a1 1 0 0 1-1-1z"/>',
  link: '<path d="M10 14a4 4 0 0 0 5.7 0l3-3a4 4 0 0 0-5.7-5.7l-1 1"/><path d="M14 10a4 4 0 0 0-5.7 0l-3 3a4 4 0 0 0 5.7 5.7l1-1"/>',
  check: '<path d="M5 12.5l4.5 4.5L19 7.5"/>',
  qr: '<rect x="4" y="4" width="6" height="6" rx="1"/><rect x="14" y="4" width="6" height="6" rx="1"/><rect x="4" y="14" width="6" height="6" rx="1"/><path d="M14 14h2v2h-2zM18 14h2M14 18h2M18 18h2v2"/>',
  back: '<path d="M19 12H5M11 6l-6 6 6 6"/>',
};

const shareView = (() => {
  const SVG_NS = 'http://www.w3.org/2000/svg';
  let dialog = null; // 공유 창 (처음 열 때 한 번 만든다)
  let current = null; // 지금 창에 보이는 아파트
  let toastTimer = null;
  let copiedTimer = null;

  function icon(name, className) {
    const svg = document.createElementNS(SVG_NS, 'svg');
    svg.setAttribute('viewBox', '0 0 24 24');
    svg.setAttribute('aria-hidden', 'true');
    svg.setAttribute('class', className || 'share-icon');
    svg.innerHTML = SHARE_ICONS[name]; // 이 파일에 적은 고정 모양만 넣는다
    return svg;
  }

  function el(tag, className, text) {
    const node = document.createElement(tag);
    if (className) node.className = className;
    if (text !== undefined) node.textContent = text;
    return node;
  }

  function linkFor(target) {
    const base = `${location.origin}${location.pathname.replace(/[^/]*$/, '')}share.html`;
    const query = new URLSearchParams({ apt: String(target.id) });
    if (target.area_band !== undefined && target.area_band !== null) query.set('area', String(target.area_band));
    return `${base}?${query}`;
  }

  // 클립보드에 넣는다. https나 localhost가 아니면 navigator.clipboard가 없으므로 예전 방법으로 한 번 더 해 본다
  async function copy(text) {
    try {
      if (navigator.clipboard && window.isSecureContext) {
        await navigator.clipboard.writeText(text);
        return true;
      }
    } catch (error) {
      // 아래 방법으로 넘어간다
    }
    const area = document.createElement('textarea');
    area.value = text;
    area.setAttribute('readonly', '');
    area.style.position = 'fixed';
    area.style.opacity = '0';
    document.body.append(area);
    area.select();
    let done = false;
    try {
      done = document.execCommand('copy');
    } catch (error) {
      done = false;
    }
    area.remove();
    return done;
  }

  // 화면 아래의 짧은 안내 ("복사했습니다.")
  function toast(message) {
    let box = document.getElementById('share-toast');
    if (!box) {
      box = el('div', 'share-toast');
      box.id = 'share-toast';
      box.setAttribute('role', 'status');
      box.setAttribute('aria-live', 'polite');
      document.body.append(box);
    }
    box.textContent = message;
    box.classList.add('share-toast--on');
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => box.classList.remove('share-toast--on'), 1800);
  }

  function areaText(target) {
    if (target.supply_area === undefined && target.exclusive_area === undefined) return '';
    return format.area(target.supply_area, target.exclusive_area).replace(' (전용 ', ' · 전용 ').replace(/\)$/, '');
  }

  // ───────── 공유 창 ─────────

  function build() {
    dialog = el('dialog', 'share');
    dialog.setAttribute('aria-labelledby', 'share-title');

    const head = el('div', 'share__head');
    const title = el('h2', 'share__title', SHARE_TEXT.title);
    title.id = 'share-title';
    const close = el('button', 'share__close');
    close.type = 'button';
    close.setAttribute('aria-label', SHARE_TEXT.close);
    close.append(icon('close'));
    close.addEventListener('click', hide);
    head.append(title, close);

    // 두 화면을 겹쳐 두고 옆으로 밀어 바꾼다
    const stage = el('div', 'share__stage');

    // 링크 화면
    const linkPanel = el('section', 'share__panel share__panel--link');
    linkPanel.append(el('p', 'share__lead', SHARE_TEXT.linkLead));
    const card = el('div', 'share__card');
    const badge = el('span', 'share__badge');
    badge.append(icon('home'));
    const cardText = el('div', 'share__card-text');
    cardText.append(el('strong', 'share__name'), el('span', 'share__area'));
    card.append(badge, cardText);
    const label = el('p', 'share__label', SHARE_TEXT.linkLabel);
    label.id = 'share-link-label';
    const input = el('div', 'share__link'); // 보여 주기만 한다. 글자는 선택되지 않는다 (share.css)
    input.id = 'share-link';
    input.setAttribute('aria-labelledby', 'share-link-label');
    const copyButton = el('button', 'button button--primary share__button');
    copyButton.type = 'button';
    copyButton.dataset.role = 'copy-link';
    copyButton.addEventListener('click', copyLink);
    const qrButton = el('button', 'button share__button share__button--line');
    qrButton.type = 'button';
    qrButton.dataset.role = 'show-qr';
    qrButton.append(icon('qr', 'share-icon share-icon--button'), el('span', '', SHARE_TEXT.showQr));
    qrButton.addEventListener('click', () => showPanel('qr'));
    const fail = el('p', 'share__fail');
    fail.hidden = true;
    linkPanel.append(card, label, input, fail, copyButton, qrButton);

    // QR 화면
    const qrPanel = el('section', 'share__panel share__panel--qr');
    qrPanel.append(el('p', 'share__lead', SHARE_TEXT.qrLead));
    const qrHead = el('div', 'share__qr-head');
    qrHead.append(el('strong', 'share__name'), el('span', 'share__area'));
    const qrBox = el('div', 'share__qr');
    const backButton = el('button', 'button share__button share__button--line');
    backButton.type = 'button';
    backButton.dataset.role = 'back-to-link';
    backButton.append(icon('back', 'share-icon share-icon--button'), el('span', '', SHARE_TEXT.backToLink));
    backButton.addEventListener('click', () => showPanel('link'));
    qrPanel.append(qrHead, qrBox, backButton);

    stage.append(linkPanel, qrPanel);
    dialog.append(head, stage);

    // Esc는 브라우저가 바로 닫으므로 막고 움직임을 넣어 닫는다. 바깥(어두운 곳)을 눌러도 닫는다
    dialog.addEventListener('cancel', (event) => {
      event.preventDefault();
      hide();
    });
    // 창 안의 클릭이 페이지로 퍼지지 않게 한다. 지도 화면은 "빈 곳을 누르면 아래 창 닫기"를 하므로
    // 그대로 두면 공유 창의 바깥이나 글자를 누를 때 뒤의 아파트 창까지 닫힌다
    dialog.addEventListener('click', (event) => {
      event.stopPropagation();
      if (event.target === dialog) hide();
    });
    document.body.append(dialog);
  }

  function setCopyButton(done) {
    const button = dialog.querySelector('[data-role="copy-link"]');
    button.replaceChildren(icon(done ? 'check' : 'link', 'share-icon share-icon--button'), el('span', '', done ? SHARE_TEXT.copied : SHARE_TEXT.copyLink));
    button.classList.toggle('share__button--done', done);
  }

  async function copyLink() {
    const input = dialog.querySelector('#share-link');
    const fail = dialog.querySelector('.share__fail');
    const done = await copy(input.textContent);
    fail.hidden = done;
    fail.textContent = done ? '' : SHARE_TEXT.copyFail;
    if (!done) {
      // 복사가 안 되는 브라우저: 칸의 글자를 직접 선택할 수 있게 풀고 선택해 둔다
      input.classList.add('share__link--selectable');
      const range = document.createRange();
      range.selectNodeContents(input);
      const selection = window.getSelection();
      selection.removeAllRanges();
      selection.addRange(range);
      return;
    }
    setCopyButton(true);
    clearTimeout(copiedTimer);
    copiedTimer = setTimeout(() => setCopyButton(false), 1600);
  }

  function showPanel(which) {
    dialog.dataset.panel = which;
    const focus = dialog.querySelector(which === 'qr' ? '[data-role="back-to-link"]' : '[data-role="show-qr"]');
    setTimeout(() => focus.focus({ preventScroll: true }), 50);
  }

  function open(target) {
    if (!target || target.id === undefined || target.id === null) return;
    if (!dialog) build();
    current = target;
    const link = linkFor(target);
    dialog.querySelectorAll('.share__name').forEach((node) => { node.textContent = target.name || ''; });
    dialog.querySelectorAll('.share__area').forEach((node) => { node.textContent = areaText(target); });
    const linkBox = dialog.querySelector('#share-link');
    linkBox.textContent = link;
    linkBox.classList.remove('share__link--selectable');
    // QR코드는 열 때 미리 그려 둔다. 두 화면의 높이가 같아서 넘어갈 때 창이 들썩이지 않는다
    const box = dialog.querySelector('.share__qr');
    if (box.dataset.link !== link) {
      box.replaceChildren(qrSvg(link));
      box.dataset.link = link;
    }
    dialog.querySelector('.share__fail').hidden = true;
    setCopyButton(false);
    dialog.dataset.panel = 'link';
    if (!dialog.open) dialog.showModal();
    dialog.classList.remove('share--closing');
    requestAnimationFrame(() => dialog.classList.add('share--open'));
    dialog.querySelector('[data-role="copy-link"]').focus({ preventScroll: true });
  }

  function hide() {
    if (!dialog || !dialog.open) return;
    dialog.classList.remove('share--open');
    dialog.classList.add('share--closing');
    const done = () => {
      dialog.classList.remove('share--closing');
      if (dialog.open) dialog.close();
    };
    // 움직임을 끈 환경에서는 transitionend가 오지 않으므로 시간으로도 닫는다
    const timer = setTimeout(done, 260);
    dialog.addEventListener('transitionend', function end(event) {
      if (event.target !== dialog) return;
      clearTimeout(timer);
      dialog.removeEventListener('transitionend', end);
      done();
    });
  }

  function shareButton(getTarget) {
    const button = el('button', 'share-action share-action--share');
    button.type = 'button';
    button.setAttribute('aria-label', SHARE_TEXT.shareAria);
    button.append(icon('share'));
    button.addEventListener('click', (event) => {
      event.stopPropagation();
      open(getTarget());
    });
    return button;
  }

  function copyButton(getText, label) {
    const button = el('button', 'share-action share-action--copy');
    button.type = 'button';
    button.setAttribute('aria-label', label || '복사');
    button.append(icon('copy'));
    button.addEventListener('click', async (event) => {
      event.stopPropagation();
      const text = getText();
      if (!text) return;
      const done = await copy(text);
      toast(done ? SHARE_TEXT.toastCopied : SHARE_TEXT.copyFail);
    });
    return button;
  }

  // ───────── QR코드 (ISO/IEC 18004) ─────────
  // 바이트 모드, 오류 정정 M, 버전 1 ~ 10 (UTF-8로 213바이트까지). 링크는 60자 안팎이라 버전 4 ~ 5가 된다.

  // 버전마다 [블록당 정정 코드어 수, [블록 수, 블록당 데이터 코드어 수], ...] (오류 정정 M)
  const QR_BLOCKS = [null,
    [10, [1, 16]], [16, [1, 28]], [26, [1, 44]], [18, [2, 32]], [24, [2, 43]],
    [16, [4, 27]], [18, [4, 31]], [22, [2, 38], [2, 39]], [22, [3, 36], [2, 37]], [26, [4, 43], [1, 44]]];
  const QR_ALIGN = [null, [], [6, 18], [6, 22], [6, 26], [6, 30], [6, 34], [6, 22, 38], [6, 24, 42], [6, 26, 46], [6, 28, 50]];

  const GF_EXP = new Array(512);
  const GF_LOG = new Array(256);
  (() => {
    let x = 1;
    for (let i = 0; i < 255; i += 1) {
      GF_EXP[i] = x;
      GF_LOG[x] = i;
      x <<= 1;
      if (x & 0x100) x ^= 0x11d;
    }
    for (let i = 255; i < 512; i += 1) GF_EXP[i] = GF_EXP[i - 255];
  })();
  const gfMul = (a, b) => (a === 0 || b === 0 ? 0 : GF_EXP[GF_LOG[a] + GF_LOG[b]]);

  function rsRemainder(data, degree) {
    let gen = [1];
    for (let i = 0; i < degree; i += 1) {
      const next = new Array(gen.length + 1).fill(0);
      gen.forEach((coef, j) => {
        next[j] ^= coef;
        next[j + 1] ^= gfMul(coef, GF_EXP[i]);
      });
      gen = next;
    }
    const rem = new Array(degree).fill(0);
    data.forEach((byte) => {
      const factor = byte ^ rem.shift();
      rem.push(0);
      for (let i = 0; i < degree; i += 1) rem[i] ^= gfMul(gen[i + 1], factor);
    });
    return rem;
  }

  function bchFormat(mask) {
    const data = (0 << 3) | mask; // M = 00
    let rem = data;
    for (let i = 0; i < 10; i += 1) rem = (rem << 1) ^ ((rem >> 9) * 0x537);
    return ((data << 10) | rem) ^ 0x5412;
  }

  function bchVersion(version) {
    let rem = version;
    for (let i = 0; i < 12; i += 1) rem = (rem << 1) ^ ((rem >> 11) * 0x1f25);
    return (version << 12) | rem;
  }

  const MASKS = [
    (r, c) => (r + c) % 2 === 0,
    (r) => r % 2 === 0,
    (r, c) => c % 3 === 0,
    (r, c) => (r + c) % 3 === 0,
    (r, c) => (Math.floor(r / 2) + Math.floor(c / 3)) % 2 === 0,
    (r, c) => ((r * c) % 2) + ((r * c) % 3) === 0,
    (r, c) => (((r * c) % 2) + ((r * c) % 3)) % 2 === 0,
    (r, c) => (((r + c) % 2) + ((r * c) % 3)) % 2 === 0,
  ];

  // 글자를 QR코드의 칸(true = 검은 칸)으로 바꾼다. forceMask는 시험할 때만 쓴다
  function qrCode(text, forceMask) {
    const bytes = Array.from(new TextEncoder().encode(text));
    let version = 1;
    const capacity = (v) => QR_BLOCKS[v].slice(1).reduce((sum, [count, size]) => sum + count * size, 0);
    while (version <= 10 && 4 + (version < 10 ? 8 : 16) + bytes.length * 8 > capacity(version) * 8) version += 1;
    if (version > 10) throw new Error('QR 글자가 너무 깁니다');

    // 데이터 비트
    const bits = [];
    const put = (value, length) => { for (let i = length - 1; i >= 0; i -= 1) bits.push((value >> i) & 1); };
    put(0b0100, 4);
    put(bytes.length, version < 10 ? 8 : 16);
    bytes.forEach((byte) => put(byte, 8));
    const total = capacity(version) * 8;
    put(0, Math.min(4, total - bits.length));
    while (bits.length % 8) bits.push(0);
    const data = [];
    for (let i = 0; i < bits.length; i += 8) data.push(parseInt(bits.slice(i, i + 8).join(''), 2));
    for (let pad = 0; data.length < capacity(version); pad += 1) data.push(pad % 2 ? 0x11 : 0xec);

    // 블록으로 나누고 정정 코드어를 붙여 번갈아 늘어놓는다
    const [ecLen, ...groups] = QR_BLOCKS[version];
    const blocks = [];
    let offset = 0;
    groups.forEach(([count, size]) => {
      for (let i = 0; i < count; i += 1) {
        const chunk = data.slice(offset, offset + size);
        offset += size;
        blocks.push({ data: chunk, ec: rsRemainder(chunk, ecLen) });
      }
    });
    const codewords = [];
    const maxData = Math.max(...blocks.map((b) => b.data.length));
    for (let i = 0; i < maxData; i += 1) blocks.forEach((b) => { if (i < b.data.length) codewords.push(b.data[i]); });
    for (let i = 0; i < ecLen; i += 1) blocks.forEach((b) => codewords.push(b.ec[i]));

    // 고정 무늬
    const size = version * 4 + 17;
    const grid = Array.from({ length: size }, () => new Array(size).fill(false));
    const fixed = Array.from({ length: size }, () => new Array(size).fill(false));
    const set = (r, c, dark) => { grid[r][c] = dark; fixed[r][c] = true; };
    const finder = (r0, c0) => {
      for (let r = -1; r <= 7; r += 1) {
        for (let c = -1; c <= 7; c += 1) {
          const rr = r0 + r;
          const cc = c0 + c;
          if (rr < 0 || cc < 0 || rr >= size || cc >= size) continue;
          const ring = Math.max(Math.abs(r - 3), Math.abs(c - 3));
          set(rr, cc, ring !== 2 && ring !== 4);
        }
      }
    };
    finder(0, 0);
    finder(0, size - 7);
    finder(size - 7, 0);
    for (let i = 8; i < size - 8; i += 1) {
      set(6, i, i % 2 === 0);
      set(i, 6, i % 2 === 0);
    }
    const align = QR_ALIGN[version];
    const last = align.length - 1;
    align.forEach((r, i) => align.forEach((c, j) => {
      // 찾기 무늬와 겹치는 세 모서리만 뺀다 (타이밍 줄 위의 자리는 그린다)
      if ((i === 0 && j === 0) || (i === 0 && j === last) || (i === last && j === 0)) return;
      for (let dr = -2; dr <= 2; dr += 1) {
        for (let dc = -2; dc <= 2; dc += 1) set(r + dr, c + dc, Math.max(Math.abs(dr), Math.abs(dc)) !== 1);
      }
    }));
    // 형식 정보·버전 정보 자리를 먼저 잡아 둔다
    for (let i = 0; i < 9; i += 1) {
      if (!fixed[8][i]) set(8, i, false);
      if (!fixed[i][8]) set(i, 8, false);
    }
    for (let i = 0; i < 8; i += 1) {
      set(8, size - 1 - i, false);
      set(size - 1 - i, 8, false);
    }
    set(size - 8, 8, true); // 늘 검은 칸
    if (version >= 7) {
      const info = bchVersion(version);
      for (let i = 0; i < 18; i += 1) {
        const dark = ((info >> i) & 1) === 1;
        set(size - 11 + (i % 3), Math.floor(i / 3), dark);
        set(Math.floor(i / 3), size - 11 + (i % 3), dark);
      }
    }

    // 데이터 칸 (오른쪽 아래부터 두 줄씩 위아래로)
    const stream = [];
    codewords.forEach((byte) => { for (let i = 7; i >= 0; i -= 1) stream.push((byte >> i) & 1); });
    let index = 0;
    let upward = true;
    for (let right = size - 1; right >= 1; right -= 2) {
      if (right === 6) right = 5;
      for (let step = 0; step < size; step += 1) {
        const r = upward ? size - 1 - step : step;
        for (let k = 0; k < 2; k += 1) {
          const c = right - k;
          if (fixed[r][c]) continue;
          grid[r][c] = index < stream.length ? stream[index] === 1 : false;
          index += 1;
        }
      }
      upward = !upward;
    }

    const apply = (mask) => {
      const out = grid.map((row) => row.slice());
      for (let r = 0; r < size; r += 1) {
        for (let c = 0; c < size; c += 1) if (!fixed[r][c] && MASKS[mask](r, c)) out[r][c] = !out[r][c];
      }
      // 형식 정보 15비트를 두 군데에 적는다 (i = 0이 가장 낮은 비트)
      const info = bchFormat(mask);
      for (let i = 0; i < 15; i += 1) {
        const dark = ((info >> i) & 1) === 1;
        // 왼쪽 위: 세로(8열) 0 ~ 5, 7, 8행 → 가로(8행) 7, 5 ~ 0열
        if (i < 6) out[i][8] = dark;
        else if (i < 8) out[i + 1][8] = dark;
        else if (i === 8) out[8][7] = dark;
        else out[8][14 - i] = dark;
        // 오른쪽 위(8행)와 왼쪽 아래(8열)
        if (i < 8) out[8][size - 1 - i] = dark;
        else out[size - 15 + i][8] = dark;
      }
      return out;
    };

    const penalty = (m) => {
      let score = 0;
      for (let pass = 0; pass < 2; pass += 1) {
        for (let a = 0; a < size; a += 1) {
          let run = 1;
          for (let b = 1; b < size; b += 1) {
            const prev = pass ? m[b - 1][a] : m[a][b - 1];
            const cur = pass ? m[b][a] : m[a][b];
            if (cur === prev) {
              run += 1;
            } else {
              if (run >= 5) score += run - 2;
              run = 1;
            }
          }
          if (run >= 5) score += run - 2;
        }
      }
      for (let r = 0; r < size - 1; r += 1) {
        for (let c = 0; c < size - 1; c += 1) {
          const v = m[r][c];
          if (v === m[r][c + 1] && v === m[r + 1][c] && v === m[r + 1][c + 1]) score += 3;
        }
      }
      const pattern = [true, false, true, true, true, false, true];
      const at = (r, c, horizontal) => (horizontal ? m[r][c] : m[c][r]);
      for (let pass = 0; pass < 2; pass += 1) {
        for (let a = 0; a < size; a += 1) {
          for (let b = 0; b + 7 <= size; b += 1) {
            if (!pattern.every((v, k) => at(a, b + k, !pass) === v)) continue;
            const lightBefore = b >= 4 && [1, 2, 3, 4].every((k) => !at(a, b - k, !pass));
            const lightAfter = b + 11 <= size && [7, 8, 9, 10].every((k) => !at(a, b + k, !pass));
            if (lightBefore || lightAfter) score += 40;
          }
        }
      }
      const dark = m.reduce((sum, row) => sum + row.filter(Boolean).length, 0);
      score += Math.floor(Math.abs((dark * 100) / (size * size) - 50) / 5) * 10;
      return score;
    };

    if (forceMask !== undefined) return apply(forceMask);
    let best = null;
    let bestScore = Infinity;
    for (let mask = 0; mask < 8; mask += 1) {
      const m = apply(mask);
      const score = penalty(m);
      if (score < bestScore) {
        best = m;
        bestScore = score;
      }
    }
    return best;
  }

  // QR코드를 SVG로 그린다. 둘레에 흰 여백 4칸을 둔다
  function qrSvg(text) {
    const matrix = qrCode(text);
    const size = matrix.length;
    const quiet = 4;
    const svg = document.createElementNS(SVG_NS, 'svg');
    svg.setAttribute('viewBox', `0 0 ${size + quiet * 2} ${size + quiet * 2}`);
    svg.setAttribute('class', 'share__qr-svg');
    svg.setAttribute('role', 'img');
    svg.setAttribute('aria-label', 'QR코드');
    svg.setAttribute('shape-rendering', 'crispEdges');
    let path = '';
    matrix.forEach((row, r) => row.forEach((dark, c) => {
      if (dark) path += `M${c + quiet} ${r + quiet}h1v1h-1z`;
    }));
    const bg = document.createElementNS(SVG_NS, 'rect');
    bg.setAttribute('width', '100%');
    bg.setAttribute('height', '100%');
    bg.setAttribute('fill', '#fff');
    const dots = document.createElementNS(SVG_NS, 'path');
    dots.setAttribute('d', path);
    dots.setAttribute('fill', 'currentColor');
    svg.append(bg, dots);
    return svg;
  }

  return { shareButton, copyButton, open, hide, copy, linkFor, toast, qrCode };
})();
