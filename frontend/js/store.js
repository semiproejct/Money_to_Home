// 브라우저 저장소 읽고 쓰기. 탭을 닫을 때까지 남는다 (sessionStorage).
//
// 화면에서 sessionStorage를 직접 쓰지 않는다. 이 파일의 함수로만 읽고 쓴다.
// 네 명이 각자 칸을 만들면 화면이 이어지지 않는다.
//
// 묶음은 세 개다. 값의 이름은 API와 DB의 이름과 같다. 금액은 원 단위 정수다.
//
//   input : age, annual_income, current_assets,
//           loan_choice, loan_product_id, repayment_years,
//           monthly_saving, target_years
//   place : 보던 단계와 질문, "처음부터 다시 입력"을 골랐는지, 스플래시를 봤는지(splash_seen)
//   map   : 구와 동, 조건, 정렬, 면적 단위, 자금 부족 표시, 지도의 가운데와 확대 수준
//
// 주민등록번호는 넣지 않는다. 만 나이만 넣는다 (NFR-25).

const STORE_KEYS = { input: 'mth.input', place: 'mth.place', map: 'mth.map' };

function readBundle(name) {
  try {
    return JSON.parse(sessionStorage.getItem(STORE_KEYS[name])) || {};
  } catch (error) {
    return {};
  }
}

function writeBundle(name, value) {
  sessionStorage.setItem(STORE_KEYS[name], JSON.stringify(value));
}

const store = {
  // 묶음 전체를 읽는다. 예: store.get('input').current_assets
  get: (name) => readBundle(name),

  // 묶음의 일부만 바꾼다. 예: store.set('input', { monthly_saving: 1000000 })
  set: (name, values) => writeBundle(name, { ...readBundle(name), ...values }),

  // 묶음 하나를 비운다.
  clear: (name) => sessionStorage.removeItem(STORE_KEYS[name]),

  // 전부 비운다. "처음부터 다시 입력"에서 쓴다.
  clearAll: () => Object.values(STORE_KEYS).forEach((key) => sessionStorage.removeItem(key)),
};
