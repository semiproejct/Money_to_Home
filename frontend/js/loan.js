// P-03 대출상품 선택. 담당: 박채은
//
// 상품 두 개와 "대출 없이 계산" 가운데 하나를 고른다.
//   상품을 고름 → 그 상품의 상환 기간을 고름 → "다음"이 켜진다
//   대출 없이 계산을 고름 → 바로 "다음"이 켜진다 (상환 기간을 묻지 않는다)
//
// 상품 목록은 A-01, 예상 대출금액과 월 상환액은 A-03에서 받는다. 화면은 받은 값을 보여 주기만 한다 (NFR-13).
// "다음"을 누르면 대출 선택을 저장하고(A-10) 저축 계획 화면으로 간다.
//
// 저장소에는 loan_choice, loan_product_id, repayment_years로 둔다 (store.js). 대출 없이 계산이면 뒤의 둘은 null이다.

(function () {
  const MSG = {
    pick: '상품과 상환 기간, 또는 대출 없이 계산을 골라 주세요.',
    pickWhenFailed: '대출 없이 계산은 지금도 고를 수 있습니다.',
    pickYears: '상환 기간을 고르면 표시됩니다',
    estimate: '현재 보유자산 기준 · 자격을 충족한다고 가정한 추정치',
    zeroAssets: '보유자산이 0원이라 지금 기준으로는 0원입니다. 대출 없이 계산으로 바꿀 수도 있습니다.',
    noLoan: '예상 대출금액과 월 상환액은 계산하지 않습니다. 보유자산과 저축으로만 구분합니다.',
    saveFailed: '입력한 정보를 저장하지 못했습니다. 인터넷 연결을 확인하고 다시 시도해 주세요.',
  };

  // 재무정보가 빠졌으면 그 화면으로 보낸다. 값이 하나도 없으면 시작 화면으로 간다 (guard.js).
  if (!guard.requireStep('loan')) return;
  const currentAssets = store.get('input').current_assets;

  const $ = (id) => document.getElementById(id);
  const form = $('loan-form');
  const submit = $('loan-submit');
  const hint = $('loan-hint');
  const errorBar = $('loan-error');
  const productList = $('product-list');
  const noneCard = $('none-card');
  const noneRadio = noneCard.querySelector('input');
  const yearsField = $('years-field');
  const yearsOptions = $('years-options');
  const result = $('loan-result');
  const calcError = $('calc-error');

  let products = []; // A-01에서 받은 상품
  let loadState = 'loading'; // 'loading', 'done', 'failed'
  let choice = null; // { loan_choice: 'product' | 'none', loan_product_id, repayment_years }
  let calculated = null; // 서버가 계산해 준 값 { loan_product_id, repayment_years, max_loan_amount, monthly_payment }
  let calcFailed = false;
  let calcCount = 0; // 늦게 온 응답을 버리려고 요청마다 번호를 붙인다
  let busy = false; // 저장하는 중

  // ── 표기 ─────────────────────────────────────────────
  // 서버가 준 조건을 글자로 바꾸기만 한다. 계산은 하지 않는다.

  const money = (won) => (won === 0 ? '0원' : format.won(won));
  const percent = (ratio) => `${Math.round(ratio * 100)}%`; // 0.7 → "70%"
  // 연 5.2 → "5.2%", 5.42 → "5.42%", 4.0 → "4.0%"
  const rate = (pct) => {
    const text = pct.toFixed(2);
    return `${text.endsWith('0') ? text.slice(0, -1) : text}%`;
  };
  const yearsText = (options) => `${options.join('·')}년`; // [10, 15, 20, 30] → "10·15·20·30년"
  const capText = (cap) => (cap === null ? '상한 없음' : `${format.won(cap)} 이하`);

  const findProduct = (id) => products.find((product) => product.id === id) || null;

  // ── 상품 카드 ────────────────────────────────────────
  // 서버에서 온 글자는 textContent로만 넣는다 (CLAUDE.md 11).

  function element(tag, className, text) {
    const node = document.createElement(tag);
    if (className) node.className = className;
    if (text !== undefined) node.textContent = text;
    return node;
  }

  // 글자 사이에 용어 설명 ? 를 끼운다 (3차, 와이어프레임 C8). "집값의 70%까지 (?) · 연 4.0%"
  // glossary.js가 없으면 글자만 둔다.
  function withTerm(className, before, term, after) {
    const span = element('span', className);
    span.append(document.createTextNode(before));
    if (typeof glossary !== 'undefined') span.append(glossary.button(term));
    span.append(document.createTextNode(after));
    return span;
  }

  function productCard(product) {
    const card = element('label', 'loan-card');
    card.dataset.productId = String(product.id);

    const radio = element('input');
    radio.type = 'radio';
    radio.name = 'loan';
    radio.value = `product:${product.id}`;

    const head = element('span', 'loan-card__head');
    head.append(element('span', 'loan-card__dot'), element('span', 'loan-card__name', product.name));

    // 펼쳤을 때 (고르기 전, 또는 고른 카드)
    // 높이가 부드럽게 바뀌도록 내용을 한 겹 더 싼다 (loan.css의 .loan-card__detail)
    const detail = element('span', 'loan-card__detail');
    const detailInner = element('span', 'loan-card__detail-inner');
    detail.append(detailInner);
    detailInner.append(
      element('span', 'loan-card__institution', product.institution),
      element('span', 'loan-card__limit', `최대 ${format.won(product.max_limit)}`),
      withTerm('loan-card__terms', `집값의 ${percent(product.ltv_ratio)}까지`, 'ltv', ` · 연 ${rate(product.annual_rate_pct)}`),
      withTerm('loan-card__sub', `대상 주택 ${capText(product.max_house_price)}`, 'cap', ` · 상환 ${yearsText(product.repayment_years_options)}`),
    );
    const foot = element('span', 'loan-card__foot');
    const more = element('button', 'loan-card__more', '자세히');
    more.type = 'button';
    more.addEventListener('click', (event) => {
      event.preventDefault(); // 카드를 고른 것으로 치지 않는다 (P-03 ⑥)
      event.stopPropagation();
      openSheet(product);
    });
    foot.append(element('span', 'loan-card__eligibility', `자격: ${product.eligibility_summary} · 기준일 ${product.base_date}`), more);
    detailInner.append(foot);

    // 접었을 때 (다른 선택지를 골랐을 때) 한 줄
    const line = element(
      'span',
      'loan-card__line',
      `${product.institution} · 최대 ${format.won(product.max_limit)} · 집값의 ${percent(product.ltv_ratio)} · 연 ${rate(product.annual_rate_pct)}`,
    );

    card.append(radio, head, detail, line);
    radio.addEventListener('change', () => pickProduct(product.id));
    return card;
  }

  function renderProducts() {
    $('product-loading').hidden = loadState !== 'loading';
    $('product-error').hidden = loadState !== 'failed';
    productList.replaceChildren(...products.map(productCard));
  }

  // ── 상환 기간 ────────────────────────────────────────

  function renderYearsOptions(product) {
    const options = product.repayment_years_options.map((years) => {
      const option = element('label', 'years__option');
      const radio = element('input');
      radio.type = 'radio';
      radio.name = 'repayment_years';
      radio.value = String(years);
      radio.addEventListener('change', () => pickYears(years));
      option.append(radio, element('span', '', `${years}년`));
      return option;
    });
    yearsOptions.replaceChildren(...options);
  }

  // ── 그리기 ───────────────────────────────────────────

  // 결과 상자의 값이 지금 고른 상품과 기간으로 계산한 것인지 본다.
  function isFresh() {
    return (
      choice !== null &&
      calculated !== null &&
      calculated.loan_product_id === choice.loan_product_id &&
      calculated.repayment_years === choice.repayment_years
    );
  }

  function renderCards() {
    const pickedValue = choice === null ? null : choice.loan_choice === 'none' ? 'none' : `product:${choice.loan_product_id}`;
    for (const card of form.querySelectorAll('.loan-card')) {
      const radio = card.querySelector('input');
      radio.checked = radio.value === pickedValue;
      card.classList.toggle('loan-card--picked', radio.checked);
      // 하나를 고르면 나머지는 한 줄로 접힌다 (P-03 ②, ⑤)
      card.classList.toggle('loan-card--folded', pickedValue !== null && !radio.checked);
    }
  }

  function renderYears() {
    const product = choice && choice.loan_choice === 'product' ? findProduct(choice.loan_product_id) : null;
    yearsField.hidden = product === null;
    for (const radio of yearsOptions.querySelectorAll('input')) {
      radio.checked = product !== null && Number(radio.value) === choice.repayment_years;
    }
  }

  function renderResult() {
    const none = choice !== null && choice.loan_choice === 'none';
    const product = choice !== null && choice.loan_choice === 'product';
    // 계산하지 못했으면 결과 자리에 오류 상자를 둔다 (P-03 ⑨)
    calcError.hidden = !(product && calcFailed);
    // 같은 상품의 기간만 바꿔 다시 계산하는 동안에는 앞의 대출금액을 그대로 둔다.
    const sameProduct = product && calculated !== null && calculated.loan_product_id === choice.loan_product_id;
    result.hidden = !(none || (sameProduct && !calcFailed));
    if (result.hidden) return;

    $('result-rows').hidden = none;
    $('result-title').hidden = !none;
    if (none) {
      $('result-note').textContent = MSG.noLoan;
      return;
    }
    $('result-max').textContent = money(calculated.max_loan_amount);
    const monthly = isFresh() ? calculated.monthly_payment : null;
    $('result-monthly').textContent = monthly === null ? MSG.pickYears : money(monthly);
    $('result-monthly').classList.toggle('loan-result__wait', monthly === null);
    $('result-note').textContent = currentAssets === 0 ? MSG.zeroAssets : MSG.estimate;
  }

  function canGoOn() {
    if (busy || choice === null) return false;
    if (choice.loan_choice === 'none') return true;
    // 상품이면 상환 기간까지 고르고, 그 값으로 계산이 끝나야 넘어간다 (P-03 ③, ⑨)
    return choice.repayment_years !== null && isFresh() && !calcFailed;
  }

  function render() {
    renderCards();
    renderYears();
    renderResult();
    submit.disabled = !canGoOn();
    // 아무것도 고르지 않았을 때만 버튼이 꺼진 이유를 적는다 (P-03 ①, ⑧)
    hint.hidden = choice !== null;
    hint.textContent = loadState === 'failed' ? MSG.pickWhenFailed : MSG.pick;
  }

  // 새로 나타나는 요소가 오른쪽에서 왼쪽으로 밀려 들어온다. 모양은 common.css의 .field--enter
  function slideIn(target) {
    target.classList.remove('field--enter');
    void target.offsetWidth;
    target.classList.add('field--enter');
  }

  // ── 고르기 ───────────────────────────────────────────

  function remember() {
    store.set('input', {
      loan_choice: choice.loan_choice,
      loan_product_id: choice.loan_product_id,
      repayment_years: choice.repayment_years,
    });
  }

  // 상품을 고르거나 바꾸면 상환 기간 선택이 풀린다 (P-03 ④, FR-LOAN-11)
  function pickProduct(id, animate = true) {
    if (choice && choice.loan_choice === 'product' && choice.loan_product_id === id) return;
    choice = { loan_choice: 'product', loan_product_id: id, repayment_years: null };
    errorBar.hidden = true;
    renderYearsOptions(findProduct(id));
    remember();
    render();
    if (animate) slideIn(yearsField);
    calculate();
  }

  function pickYears(years) {
    choice = { ...choice, repayment_years: years };
    errorBar.hidden = true;
    remember();
    render();
    calculate();
  }

  function pickNone() {
    choice = { loan_choice: 'none', loan_product_id: null, repayment_years: null };
    calcFailed = false;
    errorBar.hidden = true;
    remember();
    render();
  }

  noneRadio.addEventListener('change', pickNone);

  // ── 계산 ─────────────────────────────────────────────

  // 서버에 계산을 맡긴다 (A-03). 대출 없이 계산이면 부르지 않는다. 늦게 온 응답은 버린다.
  async function calculate() {
    if (choice === null || choice.loan_choice !== 'product') return;
    if (isFresh()) {
      // 이미 계산한 값이다. 앞의 실패 표시를 지우고, 아직 오는 중인 다른 응답은 버린다.
      calcCount += 1;
      calcFailed = false;
      render();
      return;
    }
    const asked = { loan_product_id: choice.loan_product_id, repayment_years: choice.repayment_years };
    const mine = ++calcCount;
    calcFailed = false;
    render();
    try {
      const data = await api.post('/api/calc/loan', { current_assets: currentAssets, ...asked });
      if (mine !== calcCount) return;
      calculated = { ...asked, ...data };
    } catch (error) {
      if (mine !== calcCount) return;
      calcFailed = true;
    }
    render();
  }

  $('calc-retry').addEventListener('click', calculate);

  // ── 저장 ─────────────────────────────────────────────

  // "다음": 대출 선택을 저장하고(A-10) 저축 계획으로 간다. 실패하면 이 화면에 머물고 선택은 그대로 둔다.
  async function save() {
    const values = { ...choice };
    busy = true;
    errorBar.hidden = true;
    render();
    try {
      await account.save('/api/profile/loan', values); // 로그인했을 때만 저장한다 (account.js, 팀장)
    } catch (error) {
      busy = false;
      // 재무정보가 서버에 없을 때처럼 서버가 이유를 알려 주면 그 문장을, 아니면 저장 실패 문장을 보여 준다.
      errorBar.textContent = error.status === 422 ? error.detail : MSG.saveFailed;
      errorBar.hidden = false;
      render();
      return;
    }
    store.set('input', values);
    // 입력 요약의 "수정"으로 왔으면 이 화면만 고치고 요약으로 돌아간다 (팀장)
    location.href = store.get('place').return_to === 'summary' ? 'summary.html' : 'plan.html';
  }

  form.addEventListener('submit', (event) => {
    event.preventDefault();
    if (canGoOn()) save();
  });

  // ── 조건 자세히 ──────────────────────────────────────

  const sheet = $('terms-sheet');
  const backdrop = $('sheet-backdrop');
  let sheetOpener = null;

  function openSheet(product) {
    sheetOpener = document.activeElement;
    $('sheet-title').textContent = product.name;
    $('sheet-institution').textContent = product.institution;
    $('sheet-limit').textContent = format.won(product.max_limit);
    $('sheet-ltv').textContent = percent(product.ltv_ratio);
    $('sheet-cap').textContent = capText(product.max_house_price);
    $('sheet-rate').textContent = `연 ${rate(product.annual_rate_pct)}`;
    $('sheet-years').textContent = yearsText(product.repayment_years_options);
    const lines = product.eligibility_text.split('\n').map((line) => line.trim()).filter(Boolean);
    $('sheet-eligibility').replaceChildren(...lines.map((line) => element('li', '', line)));
    $('sheet-date').textContent = `기준일 ${product.base_date}`;
    // 출처는 http(s) 주소일 때만 링크로 연다.
    const source = $('sheet-source');
    const safe = /^https?:\/\//.test(product.source_url);
    source.hidden = !safe;
    if (safe) source.href = product.source_url;
    sheet.hidden = false;
    backdrop.hidden = false;
    $('sheet-close').focus();
  }

  function closeSheet() {
    sheet.hidden = true;
    backdrop.hidden = true;
    if (sheetOpener) sheetOpener.focus();
  }

  $('sheet-close').addEventListener('click', closeSheet);
  backdrop.addEventListener('click', closeSheet);
  document.addEventListener('keydown', (event) => {
    if (event.key === 'Escape' && !sheet.hidden) closeSheet();
  });

  // ── 시작 ─────────────────────────────────────────────

  // 상품 목록을 받는다 (A-01). 못 받아도 "대출 없이 계산"은 고를 수 있다 (P-03 ⑧).
  async function loadProducts() {
    loadState = 'loading';
    renderProducts();
    render();
    try {
      const data = await api.get('/api/loan-products');
      products = data.products;
      loadState = 'done';
    } catch (error) {
      loadState = 'failed';
    }
    renderProducts();
    restore();
    guard.showNotice(); // 다른 화면에서 보내져 왔으면 한 줄로 알린다 (한 번만 보인다)
  }

  $('product-retry').addEventListener('click', loadProducts);

  // 결과의 "예상 월 상환액" 옆에 원리금균등 상환 설명 (3차, C8)
  if (typeof glossary !== 'undefined') $('result-monthly-label').append(glossary.button('repayment'));

  // 새로 고치거나 다시 들어왔을 때 보관해 둔 선택으로 시작한다.
  function restore() {
    const input = store.get('input');
    if (choice === null && input.loan_choice === 'none') {
      pickNone();
      return;
    }
    if (choice === null && input.loan_choice === 'product') {
      const product = findProduct(input.loan_product_id);
      if (product) {
        pickProduct(product.id, false);
        if (product.repayment_years_options.includes(input.repayment_years)) pickYears(input.repayment_years);
        return;
      }
    }
    if (choice !== null && choice.loan_choice === 'product') {
      // 다시 불러온 뒤에도 고른 상품이 있으면 카드와 기간을 다시 그린다.
      const product = findProduct(choice.loan_product_id);
      if (product) renderYearsOptions(product);
    }
    render();
  }

  loadProducts();
})();
