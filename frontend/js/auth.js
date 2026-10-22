// 로그인 (P-07)과 회원가입 (P-08). 담당: 김목산
//
// login.html, signup.html이 함께 쓴다. body의 data-page로 어느 화면인지 정한다.
//   로그인     : A-16 POST /api/auth/login        { login_id, password }  → 200 { login_id }
//   아이디 확인 : A-14 POST /api/auth/login-id/check { login_id }         → 200 { available: true }, 쓰는 중이면 409
//   회원가입   : A-15 POST /api/auth/signup       { login_id, password, password_confirm, agreed } → 201 { login_id }
// 로그인 상태는 서버가 쿠키로 둔다. 비밀번호는 어디에도 남기지 않는다.
// 아이디 기억하기(3차, FR-USER-18)를 켜고 로그인했을 때만 아이디를 쿠키(REMEMBER_COOKIE)에 남긴다.
//
// 아이디와 비밀번호의 규칙은 서버(schemas/auth.py)와 같다. 서버도 같은 규칙으로 다시 확인한다.
// 문장은 API 명세서 5장과 와이어프레임의 것을 그대로 쓴다.
// 서버에서 온 글자는 textContent로 넣는다. innerHTML을 쓰지 않는다.

const AUTH_TEXT = {
  loginFailed: '아이디 또는 비밀번호가 맞지 않습니다.', // P-07 ②. 서버가 주는 문장과 같다
  loginNetwork: '로그인하지 못했습니다. 인터넷 연결을 확인하고 다시 시도해 주세요.', // P-07 ④
  checkNetwork: '아이디를 확인하지 못했습니다. 인터넷 연결을 확인하고 다시 시도해 주세요.',
  signupNetwork: '가입하지 못했습니다. 인터넷 연결을 확인하고 다시 시도해 주세요.',
  passwordDiffer: '비밀번호가 서로 다릅니다.', // FR-USER-04
  passwordSame: '비밀번호가 같습니다',
};

// 로그인한 뒤 돌아갈 화면. login.html?next=saved.html 처럼 부른 화면이 주소로 넘긴다.
// 우리 화면 이름(영문·숫자·-, .html, 뒤에 ?값)만 받는다. 바깥 주소(https://…, //…)는 버린다 (다른 사이트로 보내지 않게).
// 로그인·가입 화면 자신도 받지 않는다. 회원가입으로 넘어갔다 와도 이어지게 두 화면의 링크에 붙여 둔다.
const AUTH_NEXT_PATTERN = /^[a-z0-9-]+\.html(\?[^#]*)?$/i;

function nextPage() {
  const next = new URLSearchParams(location.search).get('next');
  if (!next || !AUTH_NEXT_PATTERN.test(next)) return null;
  if (/^(login|signup)\.html/i.test(next)) return null;
  return next;
}

// 로그인·가입 화면 사이의 링크에 next를 이어 붙인다
function keepNext(selector) {
  const next = nextPage();
  if (!next) return;
  document.querySelectorAll(selector).forEach((link) => {
    link.href = `${link.getAttribute('href')}?next=${encodeURIComponent(next)}`;
  });
}

// 아이디 기억하기 쿠키. 아이디만 둔다. 끄고 로그인하면 지운다
const REMEMBER_COOKIE = 'mth_remember_id';
const REMEMBER_DAYS = 30;

const rememberedId = {
  get() {
    const pair = document.cookie.split('; ').find((item) => item.startsWith(`${REMEMBER_COOKIE}=`));
    if (!pair) return '';
    try {
      return decodeURIComponent(pair.slice(REMEMBER_COOKIE.length + 1));
    } catch (error) {
      return '';
    }
  },
  set(loginId) {
    const maxAge = REMEMBER_DAYS * 24 * 60 * 60;
    document.cookie = `${REMEMBER_COOKIE}=${encodeURIComponent(loginId)}; max-age=${maxAge}; path=/; SameSite=Lax`;
  },
  clear() {
    document.cookie = `${REMEMBER_COOKIE}=; max-age=0; path=/; SameSite=Lax`;
  },
};

const SIGNUP_STEPS = {
  id: { title: '사용할 아이디를 정해 주세요', subtitle: '실명과 연락처는 받지 않습니다.', button: '확인' },
  password: { title: '비밀번호를 정해 주세요', subtitle: '', button: '확인' },
  confirm: { title: '비밀번호를 한 번 더 입력해 주세요', subtitle: '', button: '확인' },
  ready: { title: '이대로 가입할까요?', subtitle: '', button: '가입하기' },
};

// 아이디 규칙 (FR-USER-19). 값마다 'ok'(✓), 'bad'(✕), 'wait'(· 아직)
function idRules(value) {
  const empty = value === '';
  return {
    start: empty ? 'wait' : /^[a-z]/.test(value) ? 'ok' : 'bad',
    chars: empty ? 'wait' : /^[a-z0-9]+$/.test(value) ? 'ok' : 'bad',
    length: value.length > 20 ? 'bad' : value.length >= 5 ? 'ok' : 'wait',
  };
}

// 비밀번호 규칙 (FR-USER-03). 모자란 것은 'wait'(·)로 둔다. 어긴 것이 아니라 아직 덜 넣은 것이다
function passwordRules(value) {
  return {
    length: value.length >= 8 ? 'ok' : 'wait',
    letter: /[A-Za-z]/.test(value) ? 'ok' : 'wait',
    digit: /[0-9]/.test(value) ? 'ok' : 'wait',
  };
}

const allOk = (rules) => Object.values(rules).every((state) => state === 'ok');

// 규칙 줄에 ✓ ✕ · 를 붙인다. 색만이 아니라 표시로도 구분한다 (P-08 ②)
function paintRules(list, rules, lengthNow) {
  list.querySelectorAll('.auth__rule').forEach((item) => {
    const state = rules[item.dataset.rule];
    item.dataset.state = state;
    if (!item.dataset.text) item.dataset.text = item.textContent;
    let text = item.dataset.text;
    if (item.dataset.rule === 'length' && state !== 'ok' && lengthNow > 0) text += ` (지금 ${lengthNow}자)`;
    item.textContent = text;
    const label = { ok: '맞음', bad: '어김', wait: '아직' }[state];
    item.setAttribute('aria-label', `${text}: ${label}`);
  });
}

function setFieldError(field, messageEl, message) {
  field.classList.toggle('field--error', Boolean(message));
  messageEl.textContent = message || '';
}

function showSnackbar(el, message) {
  el.textContent = message || '';
  el.hidden = !message;
}

// ‹ : 우리 화면에서 왔으면 그 화면으로 돌아가고, 아니면 링크에 적힌 화면으로 간다
function bindBack() {
  const back = document.getElementById('auth-back');
  back.addEventListener('click', (event) => {
    if (document.referrer.startsWith(location.origin) && history.length > 1) {
      event.preventDefault();
      history.back();
    }
  });
}

// ───────── P-07 로그인 ─────────
function initLogin() {
  const form = document.getElementById('login-form');
  const idInput = document.getElementById('login-id');
  const passwordInput = document.getElementById('login-password');
  const passwordField = document.getElementById('login-password-field');
  const message = document.getElementById('login-message');
  const snackbar = document.getElementById('login-error');
  const submit = document.getElementById('login-submit');
  const remember = document.getElementById('login-remember');
  let sending = false;

  // 기억한 아이디가 있으면 채우고 체크 상자를 켜 둔다 (FR-USER-18)
  const savedId = rememberedId.get();
  if (savedId) {
    idInput.value = savedId;
    remember.checked = true;
  }

  // 시나리오 탭에서 "결과 저장"을 누르고 넘어왔는가 (P-07 ③). 저장할 값은 박채은의 scenario.js가 남기고 지운다.
  // 그때는 안내를 보이고, 로그인하면 지도로 돌아가 저장을 이어 간다
  const pendingSave = Boolean(store.get('place').pending_save);
  document.getElementById('login-pending').hidden = !pendingSave;

  // 두 값을 모두 넣어야 켜진다 (P-07 ①)
  const update = () => {
    submit.disabled = sending || idInput.value === '' || passwordInput.value === '';
  };
  [idInput, passwordInput].forEach((input) => input.addEventListener('input', () => {
    setFieldError(passwordField, message, null);
    showSnackbar(snackbar, null);
    update();
  }));

  form.addEventListener('submit', async (event) => {
    event.preventDefault();
    if (submit.disabled) return;
    sending = true;
    update();
    try {
      await api.post('/api/auth/login', { login_id: idInput.value, password: passwordInput.value });
      // 로그인에 성공했을 때만 기억한다. 꺼져 있으면 전에 기억한 아이디도 지운다
      if (remember.checked) rememberedId.set(idInput.value);
      else rememberedId.clear();
      // 저장하려다 왔으면 지도로(저장은 scenario.js가 이어서 한다). 돌아갈 화면(next)이 있으면 그 화면으로.
      // 둘 다 아니면 시작 화면의 로그인 상태로 (P-01 ②, ③)
      location.href = pendingSave ? 'map.html' : (nextPage() || 'index.html');
      return;
    } catch (error) {
      // 넣은 값은 지우지 않는다. 어느 쪽이 틀렸는지 구분하지 않는다 (P-07 ②)
      if (error.status === 401) setFieldError(passwordField, message, AUTH_TEXT.loginFailed);
      else if (error.status === 422) setFieldError(passwordField, message, error.detail);
      else showSnackbar(snackbar, AUTH_TEXT.loginNetwork); // 내부 정보는 보여 주지 않는다 (P-07 ④)
    }
    sending = false;
    update();
  });

  formFlow.enterToNext([idInput, passwordInput]); // 아이디에서 "다음"을 누르면 비밀번호로, 비밀번호에서 누르면 로그인
  update();
  (savedId ? passwordInput : idInput).focus();
}

// ───────── P-08 회원가입 ─────────
function initSignup() {
  const form = document.getElementById('signup-form');
  const title = document.getElementById('signup-title');
  const subtitle = document.getElementById('signup-subtitle');
  const submit = document.getElementById('signup-submit');
  const snackbar = document.getElementById('signup-error');
  const loginLink = document.getElementById('signup-login');
  const consent = document.getElementById('signup-consent');
  const agreed = document.getElementById('signup-agreed');

  const id = {
    field: document.getElementById('signup-id-field'),
    input: document.getElementById('signup-id'),
    rules: document.getElementById('signup-id-rules'),
    message: document.getElementById('signup-id-message'),
  };
  const password = {
    field: document.getElementById('signup-password-field'),
    input: document.getElementById('signup-password'),
    rules: document.getElementById('signup-password-rules'),
    message: document.getElementById('signup-password-message'),
  };
  const confirm = {
    field: document.getElementById('signup-confirm-field'),
    input: document.getElementById('signup-confirm'),
    message: document.getElementById('signup-confirm-message'),
  };

  let step = 'id';
  let sending = false;

  // 단계를 바꾼다. 앞 단계의 입력란은 위에 남고, 새로 나타나는 입력란은 그 아래에 밀려 들어온다
  function setStep(next) {
    const before = step;
    // 방금 입력한 칸의 자리. 다음 칸이 그 아래에 열리면 화면을 올려 그 자리에 오게 한다 (키보드에 가려지지 않게)
    const fields = { id: id.field, password: password.field, confirm: confirm.field };
    const top = fields[before] ? formFlow.placeOf(fields[before]) : 0;
    step = next;
    const text = SIGNUP_STEPS[next];
    title.textContent = text.title;
    subtitle.textContent = text.subtitle;
    subtitle.hidden = text.subtitle === '';
    submit.textContent = text.button;

    const reveal = (field, show) => {
      if (show && field.hidden) {
        field.classList.remove('field--enter');
        void field.offsetWidth; // 다시 나타날 때도 움직이게 한다
        field.classList.add('field--enter');
      }
      field.hidden = !show;
    };
    reveal(password.field, next !== 'id');
    reveal(confirm.field, next === 'confirm' || next === 'ready');
    // 규칙 줄은 그 값을 넣는 단계에서만 보인다
    id.rules.hidden = next !== 'id';
    password.rules.hidden = next !== 'password';
    loginLink.hidden = next !== 'ready';
    consent.hidden = next !== 'ready'; // 수집 항목과 목적은 가입 전 확인에서 보인다 (P-08 ⑥)

    if (next !== before) {
      const focus = { id: id.input, password: password.input, confirm: confirm.input }[next];
      if (focus) focus.focus({ preventScroll: true });
      if (focus && fields[next] && next !== 'id') formFlow.keepPlace(top, fields[next]);
      // 비밀번호 확인까지 맞으면 키보드를 내리고 동의와 가입하기 버튼이 보이게 내린다 (2026-10-21 팀장 요청)
      if (next === 'ready') formFlow.revealSubmit(submit);
    }
    update();
  }

  // 지금 단계의 버튼을 켤 수 있는가
  function update() {
    let ok = false;
    if (step === 'id') ok = allOk(idRules(id.input.value)) && id.message.textContent === '';
    if (step === 'password') ok = allOk(passwordRules(password.input.value));
    if (step === 'confirm') ok = false;
    if (step === 'ready') ok = agreed.checked; // 동의해야 '가입하기'가 켜진다 (FR-USER-05)
    submit.disabled = sending || !ok;
  }

  // 비밀번호 확인을 맞춰 본다. 같으면 '가입하기' 단계, 다르면 문구
  function checkConfirm() {
    const a = password.input.value;
    const b = confirm.input.value;
    if (b !== '' && a === b) {
      confirm.field.classList.remove('field--error');
      confirm.message.textContent = `✓ ${AUTH_TEXT.passwordSame}`;
      confirm.message.dataset.state = 'ok';
      if (step !== 'ready') setStep('ready');
      return;
    }
    delete confirm.message.dataset.state;
    // 처음 비밀번호만큼 넣었는데 다를 때만 알린다. 덜 넣은 동안에는 조용히 둔다
    setFieldError(confirm.field, confirm.message, b.length >= a.length && b !== '' ? AUTH_TEXT.passwordDiffer : null);
    if (step === 'ready') setStep('confirm');
    else update();
  }

  id.input.addEventListener('input', () => {
    setFieldError(id.field, id.message, null);
    showSnackbar(snackbar, null);
    const rules = idRules(id.input.value);
    paintRules(id.rules, rules, id.input.value.length);
    id.field.classList.toggle('field--error', Object.values(rules).includes('bad')); // 어긴 규칙이 있으면 빨간 밑줄 (P-08 ②)
    if (step !== 'id') setStep('id'); // 위에 남은 아이디를 고치면 아이디 단계로 돌아간다
    else update();
  });
  id.input.addEventListener('focus', () => {
    if (step !== 'id') setStep('id');
  });

  password.input.addEventListener('input', () => {
    setFieldError(password.field, password.message, null);
    showSnackbar(snackbar, null);
    paintRules(password.rules, passwordRules(password.input.value), password.input.value.length);
    if (step === 'confirm' || step === 'ready') {
      // 규칙을 깨면 비밀번호 단계로 돌아가고, 아니면 확인 값과 다시 맞춰 본다
      if (!allOk(passwordRules(password.input.value))) setStep('password');
      else checkConfirm();
    } else update();
  });
  password.input.addEventListener('focus', () => {
    if (step === 'confirm' && !allOk(passwordRules(password.input.value))) setStep('password');
  });

  agreed.addEventListener('change', () => {
    showSnackbar(snackbar, null);
    update();
  });

  confirm.input.addEventListener('input', () => {
    showSnackbar(snackbar, null);
    checkConfirm();
  });

  // 서버가 거부한 값의 문장을 그 입력란 아래에 적고 그 단계로 돌아간다
  function showServerError(error, network) {
    const target = { login_id: [id, 'id'], password: [password, 'password'], password_confirm: [confirm, 'confirm'] }[error.field];
    if ((error.status === 409 || error.status === 422) && target) {
      const [where, back] = target;
      setStep(back);
      setFieldError(where.field, where.message, error.detail);
      update();
      return;
    }
    showSnackbar(snackbar, error.status === 422 ? error.detail : network);
  }

  form.addEventListener('submit', async (event) => {
    event.preventDefault();
    if (submit.disabled) return;
    sending = true;
    update();
    try {
      if (step === 'id') {
        await api.post('/api/auth/login-id/check', { login_id: id.input.value }); // 중복은 서버에서 확인한다 (P-08 ③)
        setStep('password');
      } else if (step === 'password') {
        setStep('confirm');
        if (confirm.input.value !== '') checkConfirm();
      } else if (step === 'ready') {
        const user = await api.post('/api/auth/signup', {
          login_id: id.input.value,
          password: password.input.value,
          password_confirm: confirm.input.value,
          agreed: agreed.checked,
        });
        showDone(user.login_id);
        return;
      }
    } catch (error) {
      showServerError(error, step === 'id' ? AUTH_TEXT.checkNetwork : AUTH_TEXT.signupNetwork);
    } finally {
      sending = false;
    }
    update();
  });

  // P-08 ⑦ 가입 완료. 가입과 함께 로그인되었다.
  // '시작하기'는 재무정보로 간다. 입력하던 값이 이 탭에 남아 있으면 그 자리로 간다.
  // 결과를 저장하려다 로그인 화면을 거쳐 가입했으면 지도로 돌아가 저장을 이어 간다 (P-07 ③)
  function showDone(loginId) {
    form.hidden = true;
    document.querySelector('.auth-nav').hidden = true;
    document.getElementById('signup-done-text').textContent =
      `${loginId}님, 이제 입력한 정보를 저장해 다음에 이어서 볼 수 있습니다.`;
    document.getElementById('signup-start').href = store.get('place').pending_save ? 'map.html' : (nextPage() || guard.resumePage());
    document.getElementById('signup-done').hidden = false;
    document.getElementById('signup-start').focus();
  }

  paintRules(id.rules, idRules(''), 0);
  paintRules(password.rules, passwordRules(''), 0);
  setStep('id');
}

bindBack();
keepNext('a[href="signup.html"], a[href="login.html"]');
if (document.body.dataset.page === 'login') initLogin();
if (document.body.dataset.page === 'signup') initSignup();
