// 로그인 상태 (2차). 담당: 김해원
//
// 로그인 쿠키는 서버가 두고 스크립트는 읽지 못한다(HttpOnly). 로그인했는지는 A-18(GET /api/auth/me)로 묻는다.
//
//   const loginId = await account.me();       로그인했으면 아이디, 아니면 null. 한 화면에서 한 번만 묻는다
//   await account.save('/api/profile/plan', values);
//                                            로그인했을 때만 서버에 저장한다 (FR-PROFILE-04). 아니면 아무것도 하지 않는다
//                                            시작 화면에서 고른 재무정보(place.profile_id)가 있으면 그 재무정보에 저장한다
//                                            (주소 끝에 ?profile_id=, 재무정보 3개, 2026-10-21)
//   await account.logout();                  로그아웃
//
// 30분 동안 요청이 없어 로그인이 풀리면 (FR-USER-08, 와이어프레임 P-01 ⑤)
//   - 로그인한 채로 이 탭을 쓰고 있었으면 store의 place.login_id에 아이디가 있다.
//   - 그런데 서버가 401을 주면 로그인이 풀린 것이다. place.expired를 남기고 시작 화면으로 보낸다.
//   - 입력하던 값(store의 input)은 지우지 않는다. "로그인 없이 시작하기"를 누르면 보던 자리로 돌아간다.
//   - 화면을 열어 둔 채 가만히 있어도 알 수 있게, 1분마다 마지막 요청에서 30분이 지났는지 본다.
//
// 아이디와 비밀번호는 브라우저 저장소에 두지 않는다. place.login_id는 화면에 이름을 적고 만료를 알아채는 데만 쓴다.

const ACCOUNT_SESSION_MS = 30 * 60 * 1000; // 서버의 로그인 유지 시간과 같다 (backend/services/auth.py)
const ACCOUNT_CHECK_MS = 60 * 1000;
const ACCOUNT_START_PAGE = 'index.html';

const account = (() => {
  let asked = null; // A-18의 답 (Promise). 한 화면에서 한 번만 묻는다
  let lastRequest = Date.now();
  let watching = false;

  // 어느 화면의 요청이든 서버는 로그인 쿠키를 새로 내준다 (backend/main.py). 그래서 모든 요청의 때를 적어 둔다.
  ['get', 'post', 'put', 'delete'].forEach((method) => {
    const send = api[method];
    api[method] = (...args) => {
      lastRequest = Date.now();
      return send(...args);
    };
  });

  // 로그인이 풀렸다. 시작 화면에서 안내를 보이게 표시를 남기고 보낸다.
  function expire() {
    store.set('place', { login_id: null, expired: true, profile_id: null, profile_name: null });
    if (!location.pathname.endsWith(`/${ACCOUNT_START_PAGE}`) && location.pathname !== '/') {
      location.href = ACCOUNT_START_PAGE;
    }
  }

  // 로그인한 채로 쓰다가 1분마다 본다. 마지막 요청에서 30분이 지났으면 서버에 물어 확인한다.
  function watch() {
    if (watching) return;
    watching = true;
    setInterval(async () => {
      if (!store.get('place').login_id || Date.now() - lastRequest < ACCOUNT_SESSION_MS) return;
      asked = null;
      await api_.me(); // 401이면 me()가 expire를 부른다
    }, ACCOUNT_CHECK_MS);
  }

  const api_ = {
    async me() {
      if (!asked) {
        asked = api.get('/api/auth/me')
          .then((data) => {
            lastRequest = Date.now();
            store.set('place', { login_id: data.login_id, expired: false });
            watch();
            return data.login_id;
          })
          .catch((error) => {
            if (error.status === 401 && store.get('place').login_id) expire();
            if (error.status === 401) return null;
            asked = null; // 서버에 닿지 못했다. 다음에 다시 묻는다
            return null;
          });
      }
      return asked;
    },

    // 로그인했을 때만 저장한다. 저장하다 401이면 로그인이 풀린 것이다.
    async save(path, body) {
      if (!(await api_.me())) return null;
      const profileId = store.get('place').profile_id;
      try {
        const data = await api.put(profileId ? `${path}?profile_id=${encodeURIComponent(profileId)}` : path, body);
        lastRequest = Date.now();
        return data;
      } catch (error) {
        if (error.status === 401) {
          expire();
          return null;
        }
        throw error;
      }
    },

    async logout() {
      try {
        await api.post('/api/auth/logout');
      } catch (error) {
        // 이미 풀렸어도 화면은 로그아웃한 것으로 둔다
      }
      asked = Promise.resolve(null);
      store.set('place', { login_id: null, expired: false, profile_id: null, profile_name: null });
    },

    // 이 탭에서 "로그인이 풀렸다"는 안내를 보여야 하는가. 한 번 보이면 지운다.
    takeExpired() {
      const expired = store.get('place').expired === true;
      if (expired) store.set('place', { expired: false });
      return expired;
    },
  };
  return api_;
})();
