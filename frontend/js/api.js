// 서버를 부르는 공통 함수. 모든 화면이 이 함수로만 서버를 부른다.
//
//   const data = await api.get('/api/loan-products');
//   const data = await api.post('/api/calc/loan', { ... });
//   const data = await api.put('/api/profile/finance', { ... });
//   await api.delete('/api/auth/me', { password });   본문이 필요 없으면 api.delete(path)
//
// 오류가 나면 ApiError를 던진다. error.detail은 사용자에게 보여 줄 문장이고,
// error.field는 문제가 된 입력란의 이름이다 (없을 수 있다).
//
//   try { ... } catch (error) { 보여주기(error.detail, error.field); }

const MSG_NETWORK = '서버에 연결하지 못했습니다. 잠시 후 다시 시도해 주세요.';

class ApiError extends Error {
  constructor(status, detail, field) {
    super(detail);
    this.status = status; // 서버에 닿지 못했으면 0
    this.detail = detail;
    this.field = field || null;
  }
}

async function request(method, path, body) {
  const options = { method, headers: {}, credentials: 'same-origin' };
  if (body !== undefined) {
    options.headers['Content-Type'] = 'application/json';
    options.body = JSON.stringify(body);
  }

  let response;
  try {
    response = await fetch(path, options);
  } catch (error) {
    throw new ApiError(0, MSG_NETWORK);
  }

  if (response.status === 204) return null;

  let data = null;
  try {
    data = await response.json();
  } catch (error) {
    data = null;
  }

  if (!response.ok) {
    const detail = data && typeof data.detail === 'string' ? data.detail : MSG_NETWORK;
    throw new ApiError(response.status, detail, data && data.field);
  }
  return data;
}

const api = {
  get: (path) => request('GET', path),
  post: (path, body) => request('POST', path, body),
  put: (path, body) => request('PUT', path, body),
  delete: (path, body) => request('DELETE', path, body), // 본문은 있을 때만 보낸다 (A-20 탈퇴의 비밀번호)
};
