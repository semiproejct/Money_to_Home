// 용어 설명 (FR-COMMON-06, T-COMMON-10, 3차). 담당: 박채은
//
// 금융 용어 옆에 작은 ? 버튼을 두고, 누르면 아래에 검은 말풍선으로 짧은 설명을 띄운다 (와이어프레임 C8).
// 바깥을 누르거나 Esc를 누르거나 화면을 스크롤하면 닫힌다.
//
//   const button = glossary.button('ltv');   // ? 버튼을 만든다. 용어 옆에 붙인다
//
// 붙일 용어는 요구사항 명세서 부록 C의 목록이다: 대출 비율, 대상 주택 가격 상한, 원리금균등 상환,
// 자기자금, 허용 상승률, 공급면적과 전용면적.
// 대출 비율의 문장은 와이어프레임 C8의 것이다. 나머지는 요구사항의 계산 규칙(C-03, C-07, C-12, FR-LOAN-14)과
// 화면 설계서 8장(면적)을 풀어 쓴 것이다.

const GLOSSARY_TERMS = {
  ltv: {
    title: '대출 비율',
    text: '집값 가운데 대출로 낼 수 있는 비율입니다. 70%면 3억 원짜리 집에 2억 1,000만 원까지 빌릴 수 있습니다.',
  },
  cap: {
    title: '대상 주택 가격 상한',
    text: '이 상품으로 대출을 받을 수 있는 집값의 한도입니다. 평균가가 한도를 넘으면 안내만 하고 계산에는 그대로 넣습니다.',
  },
  repayment: {
    title: '원리금균등 상환',
    text: '빌린 돈과 이자를 합쳐 매달 같은 금액으로 갚는 방식입니다. 예상 월 상환액은 이 방식으로 계산했습니다.',
  },
  ownFunds: {
    title: '자기자금',
    text: '대출 없이 내 돈으로 낼 수 있는 금액입니다. 현재 보유자산에 목표 기간 동안 모은 저축액을 더한 값입니다.',
  },
  growth: {
    title: '허용 상승률',
    text: '목표 기간 동안 집값이 해마다 이 비율보다 덜 오르면 여전히 목표할 수 있다는 뜻입니다. 집값을 예측한 값은 아닙니다.',
  },
  area: {
    title: '공급면적과 전용면적',
    text: '전용면적은 집 안에서 혼자 쓰는 넓이이고, 공급면적은 여기에 계단과 복도 같은 함께 쓰는 넓이를 더한 것입니다.',
  },
};

const glossary = {
  opened: null, // { button, bubble }

  // ? 버튼. 카드나 라벨 안에 있어도 그 카드가 골라지지 않게 한다.
  button(key) {
    const term = GLOSSARY_TERMS[key];
    const button = document.createElement('button');
    button.type = 'button';
    button.className = 'glossary__button';
    button.textContent = '?';
    button.setAttribute('aria-label', `${term.title} 설명`);
    button.setAttribute('aria-expanded', 'false');
    button.addEventListener('click', (event) => {
      event.preventDefault();
      event.stopPropagation();
      glossary.toggle(button, key);
    });
    return button;
  },

  toggle(button, key) {
    const same = glossary.opened && glossary.opened.button === button;
    glossary.close();
    if (!same) glossary.open(button, key);
  },

  open(button, key) {
    const term = GLOSSARY_TERMS[key];
    const bubble = document.createElement('div');
    bubble.className = 'glossary__bubble';
    bubble.id = 'glossary-bubble';
    bubble.setAttribute('role', 'tooltip');
    const title = document.createElement('strong');
    title.className = 'glossary__title';
    title.textContent = term.title;
    const text = document.createElement('p');
    text.className = 'glossary__text';
    text.textContent = term.text;
    bubble.append(title, text);
    document.body.append(bubble);

    // 버튼 바로 아래. 화면 밖으로 나가지 않게 좌우를 맞춘다
    const rect = button.getBoundingClientRect();
    const gap = 16;
    const width = Math.min(bubble.offsetWidth, window.innerWidth - gap * 2);
    const left = Math.min(Math.max(rect.left + rect.width / 2 - width / 2, gap), window.innerWidth - width - gap);
    bubble.style.left = `${left + window.scrollX}px`;
    bubble.style.top = `${rect.bottom + window.scrollY + 8}px`;

    button.setAttribute('aria-expanded', 'true');
    button.setAttribute('aria-describedby', bubble.id);
    glossary.opened = { button, bubble };
  },

  close() {
    if (!glossary.opened) return;
    const { button, bubble } = glossary.opened;
    bubble.remove();
    button.setAttribute('aria-expanded', 'false');
    button.removeAttribute('aria-describedby');
    glossary.opened = null;
  },
};

document.addEventListener('click', (event) => {
  if (glossary.opened && !glossary.opened.bubble.contains(event.target)) glossary.close();
});
document.addEventListener('keydown', (event) => {
  if (event.key === 'Escape') glossary.close();
});
// 아래 창 안의 스크롤도 받도록 capture로 듣는다
document.addEventListener('scroll', () => glossary.close(), true);
window.addEventListener('resize', () => glossary.close());
