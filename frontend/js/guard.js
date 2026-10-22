// 입력이 빠졌으면 빠진 첫 단계로 보낸다 (FR-RESULT-10).
//
// 순서는 재무정보 → 대출상품 → 저축 계획 → 지도다. 주소를 직접 넣거나 링크로 중간에 들어오면 앞 단계가 비어 있다.
//
//   대출상품 화면의 맨 처음:  if (!guard.requireStep('loan')) return;
//   저축 계획 화면의 맨 처음: if (!guard.requireStep('plan')) return;
//   지도 화면의 맨 처음:      if (!guard.requireInput()) return;
//   입력 화면이 다 그려진 뒤:  guard.showNotice();   (HTML에 <p class="notice" id="step-notice" hidden></p>를 둔다)
//
// 빠진 단계로 보낼 때는 그 화면이 왜 열렸는지 한 줄로 알려 준다. 안내는 한 번만 보인다.
// 넣은 값이 하나도 없으면 처음 온 사람으로 보고 시작 화면으로 보낸다.

const STEP_PAGES = { finance: 'profile.html', loan: 'loan.html', plan: 'plan.html' };
const STEP_ORDER = ['finance', 'loan', 'plan'];
const STEP_NOTICES = {
  finance: '재무정보를 먼저 입력해 주세요.',
  loan: '대출 상품을 먼저 골라 주세요.',
  plan: '저축 계획을 먼저 입력해 주세요.',
};
const MAP_PAGE = 'map.html';
const START_PAGE = 'index.html';

const isEmpty = (value) => value === undefined || value === null;

const guard = {
  // 빠진 첫 단계의 이름. 다 있으면 null. 'finance', 'loan', 'plan' 중 하나.
  missingStep() {
    const input = store.get('input');

    if (isEmpty(input.age) || isEmpty(input.annual_income) || isEmpty(input.current_assets)) {
      return 'finance';
    }
    if (isEmpty(input.loan_choice)) return 'loan';
    if (input.loan_choice === 'product' && (isEmpty(input.loan_product_id) || isEmpty(input.repayment_years))) {
      return 'loan';
    }
    if (isEmpty(input.monthly_saving) || isEmpty(input.target_years)) return 'plan';
    return null;
  },

  // 이어서 할 화면. 빠진 첫 단계의 화면이고, 다 넣었으면 지도다.
  // 시작 화면의 "시작하기"가 쓴다. 이 탭에서 입력하던 값이 있으면 보던 자리로 간다 (FR-PROFILE-11).
  resumePage() {
    const step = guard.missingStep();
    return step === null ? MAP_PAGE : STEP_PAGES[step];
  },

  // 넣은 값이 하나도 없는가. 새 탭이나 받은 링크로 처음 들어온 경우다.
  isBlank() {
    return Object.values(store.get('input')).every(isEmpty);
  },

  // 빠진 단계의 화면으로 보낸다. 넣은 값이 하나도 없으면 시작 화면으로 보낸다.
  // 도착한 화면이 안내를 한 번 보여 주도록 빠진 단계의 이름을 남긴다.
  sendTo(step) {
    if (guard.isBlank()) {
      location.replace(START_PAGE);
      return;
    }
    store.set('place', { notice: step });
    location.replace(STEP_PAGES[step]);
  },

  // 지도 화면이 쓴다. 빠진 단계가 있으면 그 화면으로 보내고 false를 돌려준다.
  requireInput() {
    const step = guard.missingStep();
    if (step === null) return true;
    guard.sendTo(step);
    return false;
  },

  // 입력 화면이 쓴다. current('loan' 또는 'plan')보다 앞 단계가 빠졌으면 그 화면으로 보내고 false를 돌려준다.
  requireStep(current) {
    const step = guard.missingStep();
    if (step === null || STEP_ORDER.indexOf(step) >= STEP_ORDER.indexOf(current)) return true;
    guard.sendTo(step);
    return false;
  },

  // 다른 화면에서 보내져 왔으면 안내를 한 번 보여 준다. 새로 고치면 사라진다.
  showNotice() {
    const step = store.get('place').notice;
    const box = document.getElementById('step-notice');
    if (!step || !box) return;
    store.set('place', { notice: null });
    box.textContent = STEP_NOTICES[step];
    box.hidden = false;
  },

  // 계산과 탐색 API에 보내는 conditions 묶음 (API 명세서 2.2).
  conditions() {
    const input = store.get('input');
    const withProduct = input.loan_choice === 'product';
    return {
      current_assets: input.current_assets,
      monthly_saving: input.monthly_saving,
      target_years: input.target_years,
      loan_choice: input.loan_choice,
      loan_product_id: withProduct ? input.loan_product_id : null,
      repayment_years: withProduct ? input.repayment_years : null,
    };
  },
};
