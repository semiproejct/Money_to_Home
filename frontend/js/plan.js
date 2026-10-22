// P-04 저축 계획. 담당: 김해원
//
// 값 두 개를 한 번에 하나씩 묻는다.
//   saving(월 저축 가능액) → term(목표 기간: 지금, 3년, 5년, 10년)
//
// 기간을 고르면 결과 상자가 나온다. 계산은 서버가 한다 (A-04). 화면은 받은 값을 보여 주기만 한다 (NFR-13).
// "지도에서 보기"를 누르면 저축 계획을 저장하고(A-11) 지도로 간다.
//
// 금액은 화면에서 만 원으로 받고, 저장소와 서버에는 원으로 넣는다 (C-01).

(function () {
  const MAX_MAN = 100000; // 월 저축 가능액의 상한: 10억 원 = 100,000만 원
  const CALC_DELAY = 250; // 입력이 잠깐 멈췄을 때 계산을 부른다 (API 명세서 A-04)

  const MSG = {
    negative: '0 이상의 숫자만 입력할 수 있습니다.',
    decimal: '소수는 입력할 수 없습니다. 만 원 단위의 정수로 입력해 주세요.',
    notNumber: '숫자만 입력할 수 있습니다.',
    max: '10억 원(100,000만 원)까지 입력할 수 있습니다.',
    help: '0도 입력할 수 있습니다.',
    saveFailed: '입력한 정보를 저장하지 못했습니다. 인터넷 연결을 확인하고 다시 시도해 주세요.',
  };

  const TITLES = {
    saving: ['매달 얼마를 모을 수 있나요?', '만 원 단위로 입력합니다.'],
    term: ['언제를 목표로 할까요?', '지금, 3년, 5년, 10년 중에서 고릅니다.'],
  };

  const NOTES = {
    later: '이자와 소득 증가는 반영하지 않습니다. 집값은 지금의 실거래 평균가 그대로 계산합니다.',
    now: '지금 목표할 수 있는지만 구분합니다. 필요한 월 저축액은 표시하지 않습니다.',
  };

  // 재무정보나 대출 선택이 빠졌으면 그 화면으로 보낸다. 값이 하나도 없으면 시작 화면으로 간다.
  if (!guard.requireStep('plan')) return;
  const currentAssets = store.get('input').current_assets;

  const $ = (id) => document.getElementById(id);
  const form = $('plan-form');
  const submit = $('plan-submit');
  const errorBar = $('plan-error');
  const hint = $('plan-hint');
  const saving = { field: $('saving-field'), input: $('saving-input'), message: $('saving-message'), read: $('saving-read') };
  const termField = $('term-field');
  const termOptions = [...form.querySelectorAll('input[name="target_years"]')];
  const result = { box: $('result'), note: $('result-note') };

  let step = 'saving';
  let calculated = null; // 서버가 계산해 준 값 { monthly_saving, target_years, accumulated_saving, own_funds }
  let calcTimer = null;
  let calcCount = 0; // 늦게 온 응답을 버리려고 요청마다 번호를 붙인다
  let busy = false; // 저장하는 중
  let serverError = null; // 서버가 월 저축 가능액을 거부했을 때의 문장

  // ── 검사 ─────────────────────────────────────────────

  // 입력란의 글자를 검사한다. { value: 만 원 정수 또는 null, error: 문장 또는 null }
  function checkMoney(text) {
    const raw = text.replace(/,/g, '').trim();
    if (raw === '') return { value: null, error: null };
    if (/^-/.test(raw)) return { value: null, error: MSG.negative };
    if (/^\d+\.\d*$|^\.\d+$/.test(raw)) return { value: null, error: MSG.decimal };
    if (!/^\d+$/.test(raw)) return { value: null, error: MSG.notNumber };
    const value = Number(raw);
    if (value > MAX_MAN) return { value: null, error: MSG.max };
    return { value, error: null };
  }

  // 고른 목표 기간(년). 고르지 않았으면 null
  function pickedYears() {
    const picked = termOptions.find((option) => option.checked);
    return picked ? Number(picked.value) : null;
  }

  // 지금 화면의 값. 월 저축 가능액은 원이다.
  function currentValues() {
    const man = checkMoney(saving.input.value).value;
    return { monthly_saving: man === null ? null : format.manToWon(man), target_years: pickedYears() };
  }

  // 결과 상자의 값이 지금 화면의 값으로 계산한 것인지 본다.
  function isFresh(values) {
    return calculated !== null && calculated.monthly_saving === values.monthly_saving && calculated.target_years === values.target_years;
  }

  // ── 그리기 ───────────────────────────────────────────

  // 월 저축 가능액 입력란을 다시 그린다. 값이 맞으면 만 원 정수를 돌려준다.
  function renderSaving() {
    const { value, error } = checkMoney(saving.input.value);
    const shown = error || serverError;
    if (value !== null) saving.input.value = format.comma(value); // 천 단위 쉼표
    else if (error === MSG.max) {
      // 상한을 넘어도 쉼표는 바른 자리에 ("100,0001" → "1,000,001"). 자릿수가 많아도 숫자를 바꾸지 않게 글자로 다룬다
      saving.input.value = saving.input.value.replace(/,/g, '').trim().replace(/\B(?=(\d{3})+(?!\d))/g, ',');
    }
    saving.read.textContent = value === null ? '' : value === 0 ? '0원' : format.won(format.manToWon(value));
    saving.field.classList.toggle('field--error', Boolean(shown));
    saving.message.textContent = shown || MSG.help;
    return shown ? null : value;
  }

  function renderResult(values) {
    // 값을 바꿔 다시 계산하는 동안에는 앞의 결과를 그대로 둔다. 새 값이 오면 그 자리에서 숫자만 바뀐다.
    const show = step === 'term' && calculated !== null && values.monthly_saving !== null && values.target_years !== null;
    result.box.hidden = !show;
    result.note.hidden = !show;
    if (!show) return;

    const now = calculated.target_years === 0;
    $('result-label').textContent = now ? '지금 자기자금' : `${calculated.target_years}년 뒤 자기자금`;
    $('result-own').textContent = format.won(calculated.own_funds);
    $('result-assets').textContent = format.won(currentAssets);
    // "지금"은 저축을 더하지 않으므로 식을 보여 주지 않는다 (P-04 ⑦).
    const monthly = calculated.monthly_saving === 0 ? '0원' : format.won(calculated.monthly_saving);
    $('result-formula').textContent = now ? '' : `(${monthly} × 12개월 × ${calculated.target_years}년)`;
    $('result-saving').textContent = calculated.accumulated_saving === 0 ? '0원' : format.won(calculated.accumulated_saving);
    result.note.textContent = now ? NOTES.now : NOTES.later;
  }

  function render() {
    const [title, subtitle] = TITLES[step];
    $('plan-title').textContent = title;
    $('plan-subtitle').textContent = subtitle;
    termField.hidden = step !== 'term';

    const man = renderSaving();
    const values = currentValues();
    renderResult(values);

    if (step === 'saving') {
      hint.hidden = true;
      submit.textContent = '확인';
      submit.disabled = man === null;
      return;
    }
    // 목표 기간을 고르기 전에는 버튼이 꺼져 있고, 그 이유를 버튼 위에 적는다 (P-04 ③).
    hint.hidden = values.target_years !== null;
    submit.textContent = '지도에서 보기';
    submit.disabled = busy || man === null || !isFresh(values);
  }

  // 새로 나타나는 요소가 오른쪽에서 왼쪽으로 밀려 들어온다. 모양은 common.css의 .field--enter
  function slideIn(element) {
    element.classList.remove('field--enter');
    void element.offsetWidth;
    element.classList.add('field--enter');
  }

  // ── 계산 ─────────────────────────────────────────────

  // 서버에 계산을 맡긴다. 값이 다 있을 때만 부른다. 늦게 온 응답은 버린다.
  async function calculate() {
    const values = currentValues();
    if (values.monthly_saving === null || values.target_years === null || isFresh(values)) return;
    const mine = ++calcCount;
    try {
      const data = await api.post('/api/calc/plan', { current_assets: currentAssets, ...values });
      if (mine !== calcCount) return;
      calculated = { ...values, ...data };
      errorBar.hidden = true;
      render();
    } catch (error) {
      if (mine !== calcCount) return;
      if (error.status === 422 && error.field === 'monthly_saving') {
        serverError = error.detail; // 서버가 값을 거부했다. 서버의 문장을 입력란 아래에 그대로 보여 준다.
      } else {
        errorBar.textContent = error.detail;
        errorBar.hidden = false;
      }
      render();
    }
  }

  function calculateSoon() {
    clearTimeout(calcTimer);
    calcTimer = setTimeout(calculate, CALC_DELAY);
  }

  // ── 저장 ─────────────────────────────────────────────

  // "지도에서 보기": 저축 계획을 저장하고 지도로 간다. 실패하면 이 화면에 머물고 값은 그대로 둔다.
  async function save() {
    const values = currentValues();
    busy = true;
    errorBar.hidden = true;
    render();
    try {
      await account.save('/api/profile/plan', values); // 로그인했을 때만 저장한다 (account.js)
    } catch (error) {
      busy = false;
      if (error.status === 422 && error.field === 'monthly_saving') {
        serverError = error.detail;
      } else {
        // 재무정보가 서버에 없을 때처럼 서버가 이유를 알려 주면 그 문장을, 아니면 저장 실패 문장을 보여 준다.
        errorBar.textContent = error.status === 422 ? error.detail : MSG.saveFailed;
        errorBar.hidden = false;
      }
      render();
      return;
    }
    store.set('input', values);
    location.href = 'summary.html'; // 입력 요약(P-04 ⑤)을 한 번 보고 지도로 간다
  }

  // ── 움직임 ───────────────────────────────────────────

  function goTo(next, animate = true) {
    step = next;
    store.set('place', { plan_step: next });
    render();
    if (next === 'saving') saving.input.focus({ preventScroll: true });
    else {
      saving.input.blur(); // 키패드가 내려가고 선택지가 나타난다
      if (animate) slideIn(termField);
    }
  }

  // 월 저축 가능액을 마치고 목표 기간으로 간다. 확인 버튼, 키보드의 "다음"(Enter), 아이폰 키패드의 ✓가 모두 여기로 온다
  function toTerm() {
    store.set('input', { monthly_saving: currentValues().monthly_saving });
    goTo('term');
    calculate(); // 돌아와서 금액만 고쳤으면 고른 기간으로 바로 다시 계산한다
  }

  form.addEventListener('submit', (event) => {
    event.preventDefault();
    if (submit.disabled) return;
    if (step === 'saving') toTerm();
    else save();
  });

  // 아이폰 숫자 키패드에는 "다음"이 없다. ✓로 키보드를 닫으면 금액이 맞을 때 목표 기간으로 간다 (form-flow.js)
  formFlow.onDone(saving.input, () => {
    if (step === 'saving' && !submit.disabled) toTerm();
  }, submit);

  // 값을 고치면 오류 문구가 바로 사라지고, 결과가 바로 바뀐다.
  saving.input.addEventListener('input', () => {
    serverError = null;
    errorBar.hidden = true;
    render();
    const { monthly_saving: monthly } = currentValues();
    if (monthly !== null && step === 'term') {
      store.set('input', { monthly_saving: monthly });
      calculateSoon();
    }
  });

  for (const option of termOptions) {
    option.addEventListener('change', () => {
      errorBar.hidden = true;
      store.set('input', { target_years: pickedYears() });
      render();
      // 결과가 나오면 아래의 "지도에서 보기"가 보이게 조금 내린다 (2026-10-21 팀장 요청)
      calculate().then(() => formFlow.revealSubmit(submit));
    });
  }

  // ── 시작 ─────────────────────────────────────────────

  // 새로 고치거나 다시 들어왔을 때 보관해 둔 값으로 그 자리부터 시작한다.
  function start() {
    const input = store.get('input');
    const has = (value) => value !== undefined && value !== null;
    if (has(input.monthly_saving)) saving.input.value = format.comma(format.wonToMan(input.monthly_saving));
    if (has(input.target_years)) {
      const saved = termOptions.find((option) => Number(option.value) === input.target_years);
      if (saved) saved.checked = true;
    }
    goTo(has(input.monthly_saving) ? 'term' : 'saving', false);
    guard.showNotice();
    calculate();
  }

  start();
})();
