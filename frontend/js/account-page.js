// 비밀번호 변경 (P-10)과 회원 탈퇴 (P-11). 담당: 김목산
//
// account.html이 쓴다. 주소의 # 으로 화면을 고른다: #password(기본), #withdraw.
//   비밀번호 변경 : A-19 PUT    /api/auth/password { current_password, new_password, new_password_confirm } → 204
//                   지금 비밀번호가 틀리면 422
//   회원 탈퇴     : A-20 DELETE /api/auth/me       { password } → 204. 재무정보와 저장한 결과도 지워지고 로그아웃된다
// 요청의 칸 이름은 명세서(3.5)에 아직 없어 이렇게 정했다. 서버가 다른 이름을 쓰면 ACCOUNT_BODY만 고친다.
//
// 로그인해야 쓸 수 있다. 화면을 열 때 account.me()(A-18)로 묻고, 로그인하지 않았으면 로그인 화면으로 보낸다.
// 비밀번호 규칙과 표시 함수(passwordRules, paintRules, allOk, setFieldError, showSnackbar)는 auth.js의 것을 쓴다.
// 서버에서 온 글자는 textContent로 넣는다. innerHTML을 쓰지 않는다.

const ACCOUNT_TEXT = {
  currentWrong: '지금 비밀번호가 맞지 않습니다.', // 와이어프레임 C4
  passwordDiffer: '비밀번호가 서로 다릅니다.', // 회원가입과 같다 (FR-USER-04)
  passwordSame: '비밀번호가 같습니다',
  changeNetwork: '비밀번호를 바꾸지 못했습니다. 인터넷 연결을 확인하고 다시 시도해 주세요.',
  withdrawNetwork: '탈퇴하지 못했습니다. 인터넷 연결을 확인하고 다시 시도해 주세요.',
};

// 요청 본문. 서버의 칸 이름이 정해지면 여기만 맞춘다
const ACCOUNT_BODY = {
  password: (current, next, confirm) => ({ current_password: current, new_password: next, new_password_confirm: confirm }),
  withdraw: (password) => ({ password }),
};

// 로그인이 풀렸다(401). 다시 로그인하게 보낸다
function accountGoLogin() {
  location.href = 'login.html';
}

// ───────── P-10 비밀번호 변경 ─────────
function initPasswordChange() {
  const form = document.getElementById('password-form');
  const submit = document.getElementById('password-submit');
  const snackbar = document.getElementById('password-error');
  const current = {
    field: document.getElementById('password-current-field'),
    input: document.getElementById('password-current'),
    message: document.getElementById('password-current-message'),
  };
  const next = {
    field: document.getElementById('password-new-field'),
    input: document.getElementById('password-new'),
    rules: document.getElementById('password-new-rules'),
    message: document.getElementById('password-new-message'),
  };
  const confirm = {
    field: document.getElementById('password-confirm-field'),
    input: document.getElementById('password-confirm'),
    message: document.getElementById('password-confirm-message'),
  };
  formFlow.enterToNext([current.input, next.input, confirm.input]); // "다음"(Enter)으로 다음 칸, 마지막 칸에서는 바꾸기
  let sending = false;

  // 확인 값 아래 문구. 같으면 "✓ 비밀번호가 같습니다", 새 비밀번호만큼 넣었는데 다르면 "비밀번호가 서로 다릅니다."
  function paintConfirm() {
    const a = next.input.value;
    const b = confirm.input.value;
    if (b !== '' && a === b) {
      confirm.field.classList.remove('field--error');
      confirm.message.textContent = `✓ ${ACCOUNT_TEXT.passwordSame}`;
      confirm.message.dataset.state = 'ok';
      return true;
    }
    delete confirm.message.dataset.state;
    setFieldError(confirm.field, confirm.message, b !== '' && b.length >= a.length ? ACCOUNT_TEXT.passwordDiffer : null);
    return false;
  }

  // 세 값이 다 맞아야 '바꾸기'가 켜진다
  function update() {
    const same = paintConfirm();
    submit.disabled = sending || current.input.value === '' || !allOk(passwordRules(next.input.value)) || !same;
  }

  current.input.addEventListener('input', () => {
    setFieldError(current.field, current.message, null);
    showSnackbar(snackbar, null);
    update();
  });
  next.input.addEventListener('input', () => {
    setFieldError(next.field, next.message, null);
    showSnackbar(snackbar, null);
    paintRules(next.rules, passwordRules(next.input.value), next.input.value.length);
    update();
  });
  confirm.input.addEventListener('input', () => {
    showSnackbar(snackbar, null);
    update();
  });

  form.addEventListener('submit', async (event) => {
    event.preventDefault();
    if (submit.disabled) return;
    sending = true;
    update();
    try {
      await api.put('/api/auth/password', ACCOUNT_BODY.password(current.input.value, next.input.value, confirm.input.value));
      form.hidden = true;
      document.querySelector('.auth-nav').hidden = true; // 가입 완료 화면처럼 ‹ 줄도 없앤다
      document.getElementById('password-done').hidden = false;
      document.getElementById('password-home').focus();
      return;
    } catch (error) {
      if (error.status === 401) {
        accountGoLogin();
        return;
      }
      if (error.status === 422) {
        // 서버가 짚은 칸 아래에 문장을 적는다. 칸을 모르면 지금 비밀번호가 틀린 것으로 본다 (명세서 A-19)
        const target = { new_password: next, new_password_confirm: confirm }[error.field] || current;
        const message = target === current && !error.field ? ACCOUNT_TEXT.currentWrong : error.detail;
        setFieldError(target.field, target.message, message);
        target.input.focus();
      } else {
        showSnackbar(snackbar, ACCOUNT_TEXT.changeNetwork); // 내부 정보는 보여 주지 않는다
      }
    }
    sending = false;
    update();
  });

  paintRules(next.rules, passwordRules(''), 0);
  form.hidden = false;
  update();
  current.input.focus();
}

// ───────── P-11 회원 탈퇴 ─────────
function initWithdraw(loginId) {
  const form = document.getElementById('withdraw-form');
  const field = document.getElementById('withdraw-password-field');
  const input = document.getElementById('withdraw-password');
  const message = document.getElementById('withdraw-password-message');
  const submit = document.getElementById('withdraw-submit');
  const snackbar = document.getElementById('withdraw-error');
  let sending = false;

  // 비밀번호를 넣어야 '탈퇴하기'가 켜진다 (C5)
  const update = () => {
    submit.disabled = sending || input.value === '';
  };
  input.addEventListener('input', () => {
    setFieldError(field, message, null);
    showSnackbar(snackbar, null);
    update();
  });

  // 취소: 우리 화면에서 왔으면 그 화면으로, 아니면 시작 화면으로
  document.getElementById('withdraw-cancel').addEventListener('click', (event) => {
    if (document.referrer.startsWith(location.origin) && history.length > 1) {
      event.preventDefault();
      history.back();
    }
  });

  // 확인 모달 (2026-10-15 팀장과 정함). 화면의 '탈퇴하기'는 모달만 열고, 모달의 '탈퇴하기'가 서버에 보낸다.
  // 취소, Esc, 모달 바깥을 누르면 닫히고 아무 일도 없다. 열리면 '취소'에 먼저 초점을 둔다 (Enter로 실수해도 탈퇴되지 않게)
  const confirmBox = document.getElementById('withdraw-confirm');
  const confirmOk = document.getElementById('withdraw-confirm-ok');
  const closeConfirm = () => {
    if (confirmBox.open) confirmBox.close();
  };
  document.getElementById('withdraw-confirm-cancel').addEventListener('click', closeConfirm);
  confirmBox.addEventListener('click', (event) => {
    if (event.target === confirmBox) closeConfirm(); // 상자 밖(어두운 바탕)을 누름
  });
  confirmBox.addEventListener('close', () => {
    if (!sending) input.focus();
  });

  form.addEventListener('submit', (event) => {
    event.preventDefault();
    if (submit.disabled) return;
    confirmBox.showModal();
    document.getElementById('withdraw-confirm-cancel').focus();
  });

  confirmOk.addEventListener('click', async () => {
    if (sending) return;
    sending = true;
    confirmOk.disabled = true;
    update();
    try {
      await api.delete('/api/auth/me', ACCOUNT_BODY.withdraw(input.value));
      // 서버가 로그아웃까지 했다. 이 탭의 로그인 표시를 지우고, 기억해 둔 이 아이디도 지운다
      store.set('place', { login_id: null, expired: false });
      if (rememberedId.get() === loginId) rememberedId.clear();
      location.href = 'index.html'; // 탈퇴하면 시작 화면으로 간다 (C5)
      return;
    } catch (error) {
      sending = false;
      confirmOk.disabled = false;
      closeConfirm();
      if (error.status === 401 && error.field !== 'password') {
        accountGoLogin();
        return;
      }
      if (error.status === 422 || error.status === 401) {
        setFieldError(field, message, error.detail); // 비밀번호가 틀림. 넣은 값은 지우지 않는다
        input.focus();
      } else {
        showSnackbar(snackbar, ACCOUNT_TEXT.withdrawNetwork);
      }
    }
    sending = false;
    update();
  });

  form.hidden = false;
  update();
  input.focus();
}

async function initAccountPage() {
  const loginId = await account.me();
  if (!loginId) {
    accountGoLogin(); // 로그인해야 쓰는 화면이다
    return;
  }
  if (location.hash === '#withdraw') initWithdraw(loginId);
  else initPasswordChange();
}

// 같은 화면에서 # 만 바뀌면(예: 비밀번호 변경 → 회원 탈퇴 링크) 브라우저가 다시 열지 않으므로 직접 다시 연다
window.addEventListener('hashchange', () => location.reload());

initAccountPage();
