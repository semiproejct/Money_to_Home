// P-02 재무정보 입력. 담당: 김해원
//
// 값 세 개를 한 번에 하나씩 묻는다.
//   rrn(주민등록번호 앞 7자리 → 만 나이) → income(연 소득) → assets(현재 보유자산) → confirm(확인)
// 하나를 넣으면 다음 칸이 그 아래에 열린다. 키보드의 "다음"·✓로 넘어간다 (js/form-flow.js)
//
// 주민등록번호 앞 7자리는 만 나이를 계산하는 데만 쓴다.
// 브라우저 저장소, 서버 요청 어디에도 넣지 않는다. 보관하는 것은 만 나이뿐이다 (NFR-25).
//
// 금액은 화면에서 만 원으로 받고, 저장소와 서버에는 원으로 넣는다 (C-01).

(function () {
  const MAX_MAN = 1000000; // 연 소득, 현재 보유자산의 상한: 100억 원 = 1,000,000만 원
  const MIN_AGE = 15;
  const MAX_AGE = 100;

  const MSG = {
    negative: '0 이상의 숫자만 입력할 수 있습니다.',
    decimal: '소수는 입력할 수 없습니다. 만 원 단위의 정수로 입력해 주세요.',
    notNumber: '숫자만 입력할 수 있습니다.',
    max: '100억 원(1,000,000만 원)까지 입력할 수 있습니다.',
    date: '생년월일을 다시 확인해 주세요.',
    ageRange: '만 15세부터 100세까지 입력할 수 있습니다.',
  };

  const TITLES = {
    rrn: ['주민등록번호 앞 7자리를\n알려 주세요', '만 나이를 계산하는 데만 쓰고 저장하지 않습니다.'],
    income: ['연 소득은 얼마인가요?', '만 원 단위로 입력합니다.'],
    assets: ['지금 가진 돈은 얼마인가요?', '만 원 단위로 입력합니다.'],
    confirm: ['입력한 내용이 맞는지\n확인해 주세요', '고칠 값을 누르면 바로 수정할 수 있습니다.'],
  };

  const $ = (id) => document.getElementById(id);
  const form = $('profile-form');
  const submit = $('profile-submit');
  const saveError = $('save-error');

  // 금액 입력란 두 개. help는 오류가 없을 때의 설명이다.
  const money = {
    income: { field: $('income-field'), input: $('income-input'), message: $('income-message'), read: $('income-read'), help: '세전 금액. 계산에는 쓰지 않습니다.', key: 'annual_income' },
    assets: { field: $('assets-field'), input: $('assets-input'), message: $('assets-message'), read: $('assets-read'), help: '예금, 적금처럼 집을 살 때 쓸 수 있는 돈', key: 'current_assets' },
  };
  const rrn = { field: $('rrn-field'), front: $('rrn-front'), back: $('rrn-back'), message: $('rrn-message'), help: '계산에는 쓰지 않고 화면에 표시만 합니다.' };
  const ageField = $('age-field');
  const ageValue = $('age-value');

  let step = 'rrn';
  let age = null; // 계산한 만 나이. 주민등록번호 자체는 변수에도 남기지 않는다.
  const serverErrors = {}; // 서버가 거부한 값의 이름 -> 문장 (P-02 ⑬)

  // ── 검사 ─────────────────────────────────────────────

  // 금액 입력란의 글자를 검사한다. { value: 만 원 정수 또는 null, error: 문장 또는 null }
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

  // 주민등록번호 앞 6자리와 뒤 첫째 자리로 만 나이를 계산한다. { age, error }
  function checkRrn(front, back) {
    if (/\D/.test(front) || /\D/.test(back)) return { age: null, error: MSG.notNumber };
    if (front.length < 6 || back.length < 1) return { age: null, error: null };

    // 뒤 첫째 자리: 1, 2, 5, 6은 1900년대. 3, 4, 7, 8은 2000년대. 0, 9는 1800년대라 100세를 넘는다.
    const century = '1256'.includes(back) ? 1900 : '3478'.includes(back) ? 2000 : 1800;
    const year = century + Number(front.slice(0, 2));
    const month = Number(front.slice(2, 4));
    const day = Number(front.slice(4, 6));
    const birth = new Date(year, month - 1, day);
    const real = birth.getFullYear() === year && birth.getMonth() === month - 1 && birth.getDate() === day;
    const today = new Date();
    if (!real || birth > today) return { age: null, error: MSG.date };

    const hadBirthday = today.getMonth() > birth.getMonth() || (today.getMonth() === birth.getMonth() && today.getDate() >= birth.getDate());
    const years = today.getFullYear() - year - (hadBirthday ? 0 : 1);
    if (years < MIN_AGE || years > MAX_AGE) return { age: null, error: MSG.ageRange };
    return { age: years, error: null };
  }

  // ── 그리기 ───────────────────────────────────────────

  function showMessage(target, error) {
    target.field.classList.toggle('field--error', Boolean(error));
    target.message.textContent = error || target.help;
  }

  // 숫자만 든 글자에 천 단위 쉼표를 다시 찍는다. 자릿수가 많아도 숫자를 바꾸지 않게 글자로 다룬다
  function commaDigits(text) {
    return text.replace(/,/g, '').trim().replace(/\B(?=(\d{3})+(?!\d))/g, ',');
  }

  // 금액 입력란 하나를 다시 그린다. 값이 맞으면 만 원 정수를 돌려준다.
  function renderMoney(name) {
    const target = money[name];
    const { value, error } = checkMoney(target.input.value);
    if (value !== null) target.input.value = format.comma(value); // 천 단위 쉼표
    else if (error === MSG.max) target.input.value = commaDigits(target.input.value); // 상한을 넘어도 쉼표는 바른 자리에 ("100,0001" → "1,000,001")
    target.read.textContent = value !== null ? format.won(format.manToWon(value)) : '';
    showMessage(target, error || serverErrors[target.key] || null);
    return error || serverErrors[target.key] ? null : value;
  }

  function renderRrn() {
    const result = checkRrn(rrn.front.value, rrn.back.value);
    showMessage(rrn, result.error);
    return result.age;
  }

  // 지금 단계에서 버튼을 켤 수 있는지 본다.
  function canGoOn() {
    if (step === 'rrn') return renderRrn() !== null;
    if (step === 'income') return renderMoney('income') !== null;
    if (step === 'assets') return renderMoney('assets') !== null;
    return age !== null && renderMoney('income') !== null && renderMoney('assets') !== null;
  }

  function render() {
    const [title, subtitle] = TITLES[step];
    $('profile-title').textContent = title;
    $('profile-subtitle').textContent = subtitle;

    // 앞에서 넣은 값은 위에 남는다. 주민등록번호 대신 계산한 만 나이만 남긴다.
    rrn.field.hidden = step !== 'rrn';
    ageField.hidden = step === 'rrn' || age === null;
    ageValue.textContent = age === null ? '' : String(age);
    money.income.field.hidden = step === 'rrn';
    money.assets.field.hidden = step === 'rrn' || step === 'income';

    submit.textContent = step === 'confirm' ? (saveError.hidden ? '다음' : '다시 시도') : '확인';
    submit.disabled = !canGoOn();
  }

  // 새로 나타나는 입력란이 오른쪽에서 왼쪽으로 밀려 들어온다. 모양은 common.css의 .field--enter
  function slideIn(field) {
    field.classList.remove('field--enter', 'jump');
    field.style.animationDelay = '';
    void field.offsetWidth; // 같은 입력란이 다시 나타날 때도 처음부터 움직이게 한다
    field.classList.add('field--enter');
  }

  // 확인 단계로 바뀔 때 제목과 값들이 한 번 뛰어오른다. 화면이 바뀐 것을 알아보게 한다. 모양은 common.css의 .jump
  function jump() {
    const targets = [$('profile-title').parentElement, ageField, money.income.field, money.assets.field];
    targets.forEach((target, index) => {
      target.classList.remove('field--enter', 'jump');
      void target.offsetWidth;
      target.style.animationDelay = `${index * 60}ms`; // 위에서부터 차례로
      target.classList.add('jump');
    });
  }

  function goTo(next, focus, animate = true) {
    step = next;
    store.set('place', { profile_step: next });
    render();
    const entering = { rrn: rrn.field, income: money.income.field, assets: money.assets.field }[next];
    if (animate && entering) slideIn(entering);
    if (animate && next === 'confirm') jump();
    if (focus) focus.focus({ preventScroll: true });
  }

  // ── 저장 ─────────────────────────────────────────────

  function currentValues() {
    return {
      age,
      annual_income: format.manToWon(checkMoney(money.income.input.value).value),
      current_assets: format.manToWon(checkMoney(money.assets.input.value).value),
    };
  }

  // 확인 화면의 "다음": 서버가 값을 한 번 더 검사하고 저장한다. 통과하면 대출상품 화면으로 간다.
  async function save() {
    const values = currentValues();
    const restart = store.get('place').restart === true; // "처음부터 다시 입력"으로 시작했으면 대출과 저축을 함께 지운다
    submit.disabled = true;
    saveError.hidden = true;
    try {
      await account.save('/api/profile/finance', { ...values, restart }); // 로그인했을 때만 저장한다 (account.js)
    } catch (error) {
      if (error.status === 422 && error.field) {
        // 서버가 값을 거부했다. 서버의 문장을 그 입력란 아래에 그대로 보여 준다 (P-02 ⑬).
        serverErrors[error.field] = error.detail;
      } else {
        saveError.hidden = false; // 저장하지 못했다. 입력한 값은 그대로 둔다 (P-02 ⑭).
      }
      render();
      return;
    }
    store.set('input', values);
    store.set('place', { profile_step: 'confirm', restart: false });
    // 입력 요약의 "수정"으로 왔으면 이 화면만 고치고 요약으로 돌아간다
    location.href = store.get('place').return_to === 'summary' ? 'summary.html' : 'loan.html';
  }

  // ── 움직임 ───────────────────────────────────────────

  // 지금 칸을 마치고 다음 칸으로 간다. 확인 버튼, 키보드의 "다음"(Enter), 아이폰 키패드의 ✓가 모두 여기로 온다.
  // focus: 다음 칸에 바로 커서를 둘지. 키보드가 떠 있을 때만 둔다 (✓로 키보드를 닫았으면 다시 띄우지 않는다)
  function advance(focus = true) {
    // 방금 입력한 칸의 자리. 다음 칸이 그 아래에 열리면 화면을 올려 그 자리에 오게 한다 (키보드에 가려지지 않게)
    const from = { rrn: rrn.field, income: money.income.field, assets: money.assets.field }[step];
    const top = from ? formFlow.placeOf(from) : 0;
    if (step === 'rrn') {
      age = renderRrn();
      rrn.front.value = '';
      rrn.back.value = ''; // 일곱 자리는 만 나이를 구한 뒤 바로 지운다
      store.set('input', { age });
      if (!money.income.input.value) goTo('income', focus && money.income.input);
      else if (!money.assets.input.value) goTo('assets', focus && money.assets.input);
      else goTo('confirm');
    } else if (step === 'income') {
      store.set('input', { annual_income: currentValues().annual_income });
      if (money.assets.input.value) goTo('confirm');
      else goTo('assets', focus && money.assets.input);
    } else if (step === 'assets') {
      store.set('input', { current_assets: currentValues().current_assets });
      goTo('confirm');
    }
    // 다 넣었으면 키보드를 내리고 아래의 버튼이 보이게 조금 내린다 (2026-10-21 팀장 요청)
    if (step === 'confirm') formFlow.revealSubmit(submit);
    else if (focus) formFlow.keepPlace(top, { income: money.income.field, assets: money.assets.field }[step]);
  }

  form.addEventListener('submit', (event) => {
    event.preventDefault();
    if (!canGoOn()) return;
    if (step === 'confirm') save();
    else advance();
  });

  // 아이폰 숫자 키패드에는 "다음"이 없다. ✓로 키보드를 닫으면 값이 맞을 때 다음 칸으로 간다 (form-flow.js)
  for (const name of Object.keys(money)) {
    formFlow.onDone(money[name].input, () => {
      if (step === name && canGoOn()) advance(false);
    }, submit);
  }

  // 값을 고치면 오류 문구가 바로 사라진다. 서버가 거부했던 값도 고치면 다시 시도할 수 있다.
  for (const name of Object.keys(money)) {
    money[name].input.addEventListener('input', () => {
      delete serverErrors[money[name].key];
      saveError.hidden = true;
      render();
    });
  }
  rrn.front.addEventListener('input', () => {
    if (rrn.front.value.length === 6 && !/\D/.test(rrn.front.value)) rrn.back.focus(); // 여섯 자리를 다 치면 뒤 첫째 자리로
    render();
  });
  // 일곱 자리를 다 넣고 맞으면 바로 다음 칸(연 소득)으로 간다. 키보드는 그대로 둔다
  rrn.back.addEventListener('input', () => {
    if (step === 'rrn' && canGoOn()) advance();
    else render();
  });
  // 앞 여섯 자리에서 키보드의 "다음"을 누르면 뒤 첫째 자리로 (폼을 보내지 않는다)
  rrn.front.addEventListener('keydown', (event) => {
    if (event.key === 'Enter') {
      event.preventDefault();
      rrn.back.focus();
    }
  });
  rrn.back.addEventListener('keydown', (event) => {
    if (event.key === 'Backspace' && rrn.back.value === '') rrn.front.focus();
  });

  // 만 나이를 누르면 주민등록번호를 다시 입력한다.
  ageField.addEventListener('click', () => {
    age = null;
    goTo('rrn', rrn.front);
  });

  // ── 시작 ─────────────────────────────────────────────

  // 새로 고치거나 다시 들어왔을 때 보관해 둔 값으로 그 자리부터 시작한다.
  function start() {
    const input = store.get('input');
    const has = (value) => value !== undefined && value !== null;
    if (has(input.age)) age = input.age;
    if (has(input.annual_income)) money.income.input.value = format.comma(format.wonToMan(input.annual_income));
    if (has(input.current_assets)) money.assets.input.value = format.comma(format.wonToMan(input.current_assets));

    let first = 'rrn';
    if (has(input.age)) first = 'income';
    if (first === 'income' && has(input.annual_income)) first = 'assets';
    if (first === 'assets' && has(input.current_assets)) first = 'confirm';

    const focus = { rrn: rrn.front, income: money.income.input, assets: money.assets.input }[first];
    goTo(first, focus, false); // 처음 열 때는 움직이지 않는다
    guard.showNotice();
  }

  start();
})();
