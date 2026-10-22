// 금액과 면적의 표기. 화면에 숫자를 보여 줄 때는 이 파일의 함수를 쓴다.
//
// 여기 있는 것은 표기뿐이다. 대출금액 같은 계산은 서버가 한다 (NFR-13).

const PYEONG = 3.3058; // 1평 = 3.3058㎡
const SIDO_NAME = '전남광주통합특별시'; // 광주 5개 구의 시도 (CLAUDE.md "지역 이름과 코드")

const format = {
  // 원 → "3억 2,500만 원", "8,500만 원". 만원 단위로 반올림한다 (FR-COMMON-11).
  won(amount) {
    const man = Math.round(Math.abs(amount) / 10000);
    const eok = Math.floor(man / 10000);
    const rest = man % 10000;
    const sign = amount < 0 && man > 0 ? '-' : '';

    // 만 원이 안 되는 금액은 원 단위 그대로. 0은 "0원" (2026-10-15에 정함, 전에는 "0만 원")
    const won = Math.round(Math.abs(amount));
    if (man === 0) return `${amount < 0 && won > 0 ? '-' : ''}${won.toLocaleString('ko-KR')}원`;

    let text;
    if (eok > 0 && rest > 0) text = `${eok.toLocaleString('ko-KR')}억 ${rest.toLocaleString('ko-KR')}만 원`;
    else if (eok > 0) text = `${eok.toLocaleString('ko-KR')}억 원`;
    else text = `${rest.toLocaleString('ko-KR')}만 원`;
    return sign + text;
  },

  // 원 → "3.0억", "6.5천", "9천". 지도의 말풍선처럼 자리가 좁은 곳에 쓴다.
  //   1억 원 이상은 억 단위로 소수 첫째 자리까지 (3억 → "3.0억", 3억 2,500만 → "3.3억")
  //   1억 원 미만은 천만 단위로 (6,500만 → "6.5천", 9,000만 → "9천")
  short(amount) {
    const man = Math.round(Math.abs(amount) / 10000);
    if (man >= 10000) return `${(man / 10000).toFixed(1)}억`;
    const cheon = (man / 1000).toFixed(1);
    return `${cheon.endsWith('.0') ? cheon.slice(0, -2) : cheon}천`;
  },

  // 입력란의 만원 값 → 원. 서버에 보낼 때 쓴다.
  manToWon: (man) => man * 10000,

  // 원 → 만원. 입력란을 채울 때 쓴다.
  wonToMan: (won) => Math.round(won / 10000),

  // 숫자에 천 단위 쉼표. 12000 → "12,000"
  comma: (number) => number.toLocaleString('ko-KR'),

  // ㎡ → 평. 반올림한 정수 (요구사항 명세서 부록 C).
  pyeong: (squareMeter) => Math.round(squareMeter / PYEONG),

  // 전용면적의 ㎡. 소수점 아래를 버린다 (84.94 → "84㎡", 59.88 → "59㎡").
  // 흔히 부르는 "84㎡형", "59㎡형"과 같고, 조건 검색의 면적대(area_band)와도 같은 숫자다 (2026-10-13에 정함).
  exclusive: (squareMeter) => `${Math.floor(squareMeter)}㎡`,

  // 면적 표기 (FR-APT-13, 14).
  //   공급면적이 있으면 "111㎡ (전용 84㎡)", 없으면 "전용 59㎡"
  //   unit이 'pyeong'이면 "34평 (전용 25평)", "전용 18평"
  //   ㎡일 때 공급면적은 반올림, 전용면적은 버림이다. 평은 둘 다 실제 면적을 나눠 반올림한다.
  area(supplyArea, exclusiveArea, unit = 'm2') {
    const pyeong = unit === 'pyeong';
    const exclusive = pyeong ? `${format.pyeong(exclusiveArea)}평` : format.exclusive(exclusiveArea);
    if (supplyArea === null || supplyArea === undefined) return `전용 ${exclusive}`;
    const supply = pyeong ? `${format.pyeong(supplyArea)}평` : `${Math.round(supplyArea)}㎡`;
    return `${supply} (전용 ${exclusive})`;
  },

  // 복사하는 주소 (FR-APT-18). 화면에는 "농성동 654-34", "천변우로 329-10"만 보여 주고,
  // 복사할 때는 시도와 구를 붙여 "전남광주통합특별시 서구 농성동 654-34"로 넣는다 (2026-10-19)
  fullAddress: (gu, rest) => `${SIDO_NAME} ${gu} ${rest}`,

  // 이름을 띄어쓰기에서만 줄바꿈되게 넣는다 (2026-10-19). "세계수영선수촌 / 중흥에스-클래스 센트럴"
  // 낱말마다 .keep-word(common.css)로 묶어 하이픈이나 글자 중간에서 꺾이지 않게 한다. 글자 자체는 그대로라 복사하면 원래 이름이다.
  // 한 낱말이 한 줄보다 길 때만 그 안에서 꺾인다
  keepWords(element, text) {
    const parts = String(text).split(/(\s+)/);
    element.replaceChildren(...parts.filter((part) => part !== '').map((part) => {
      if (/^\s+$/.test(part)) return document.createTextNode(part);
      const word = document.createElement('span');
      word.className = 'keep-word';
      word.textContent = part;
      return word;
    }));
  },
};
