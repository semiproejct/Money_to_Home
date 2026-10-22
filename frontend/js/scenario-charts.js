// 시나리오 탭의 그래프 두 개 (2026-10-18). 담당: 김해원
//
// "조건 바꿔 보기" 위에 "숫자로 보는 이 아파트" 묶음을 둔다. scenario.js의 draw()가 부른다.
//   scenarioCharts.section({ apartmentId, areaBand, result })  → <section> (그릴 자리)
//     result  A-07 응답. 선(평균가, 쓸 수 있는 자금, 지금 보유자산)에 쓴다. "다시 계산"하면 새 값으로 다시 그린다
//
//   ① 최근 1년 실거래: 그 면적의 거래를 점으로 (해제된 거래는 빈 점). 평균가 · 쓸 수 있는 자금 · 지금 보유자산 선
//   ② 같은 동 같은 면적 안에서의 위치: 같은 구·동, 같은 면적대 아파트의 평균가 막대. 이 아파트만 파랑
//
// 자료는 A-27 GET /api/apartments/{id}/price-history?area_band= (DB 값 그대로). 아파트·면적마다 한 번만 받는다.
// 숫자는 서버가 준 값만 쓴다 (NFR-13). 그래프의 좌표만 여기서 정한다. 글자는 textContent로 넣는다.
// 앞으로의 집값은 그리지 않는다. 묶음 제목 옆 (?)는 다른 용어 설명과 같은 말풍선이다 (glossary.js).

const SCENARIO_CHART_TEXT = {
  title: '숫자로 보는 이 아파트',
  help: '최근 1년 실거래 기록과 입력한 값으로만 그립니다. 앞으로의 집값은 예측하지 않습니다.',
  trades: '최근 1년 실거래',
  neighbors: (dong, area) => `${dong} 같은 면적 (전용 ${area}㎡대) 안에서의 위치`,
  source: '출처: 국토교통부 실거래가 (계약일 기준)',
  neighborSource: '각 아파트의 최근 1년 실거래 평균가',
  loading: '그래프를 불러오는 중입니다.',
  failed: '그래프를 불러오지 못했습니다.',
};

// (?) 말풍선의 문장. glossary.js의 용어 목록에 더한다
if (typeof GLOSSARY_TERMS !== 'undefined') {
  GLOSSARY_TERMS.charts = { title: '그래프', text: SCENARIO_CHART_TEXT.help };
}

const scenarioCharts = (() => {
  const NS = 'http://www.w3.org/2000/svg';
  const cache = new Map(); // '아파트:면적대' → Promise(A-27 응답)

  const el = (tag, className, text) => {
    const node = document.createElement(tag);
    if (className) node.className = className;
    if (text !== undefined && text !== null) node.textContent = text;
    return node;
  };
  const svgEl = (tag, attrs, text) => {
    const node = document.createElementNS(NS, tag);
    Object.entries(attrs).forEach(([k, v]) => node.setAttribute(k, v));
    if (text !== undefined) node.textContent = text;
    return node;
  };
  const color = (name) => getComputedStyle(document.body).getPropertyValue(name).trim();
  // 그래프 안의 금액은 짧게: 1억 이상은 소수 한 자리 "3.5억", "2.1억", "4억", 1억 밑은 "8,500만" (2026-10-19)
  const short = (won) => {
    if (won >= 100_000_000) return `${(Math.round(won / 10_000_000) / 10).toFixed(1).replace(/\.0$/, '')}억`;
    return `${format.comma(Math.round(won / 10_000))}만`;
  };

  function load(apartmentId, areaBand) {
    const key = `${apartmentId}:${areaBand}`;
    if (!cache.has(key)) {
      const promise = api.get(`/api/apartments/${apartmentId}/price-history?area_band=${areaBand}`);
      promise.catch(() => cache.delete(key)); // 실패하면 다음에 다시 받는다
      cache.set(key, promise);
    }
    return cache.get(key);
  }

  // 선의 이름과 값. 목표 기간이 "지금"이면 지금 보유자산 선은 겹치므로 뺀다
  function lines(result) {
    const when = result.target_years === 0 ? '지금' : `${result.target_years}년 뒤`;
    const loan = result.loan && result.loan.choice === 'product';
    const funds = result.price - result.shortage; // 쓸 수 있는 자금 = 집값 − 부족자금 (서버 값)
    const out = [{ key: 'funds', value: funds, label: `${when} ${loan ? '쓸 수 있는 자금' : '자기자금'}`, color: color('--color-within') }];
    if (result.target_years !== 0) out.push({ key: 'now', value: result.current_assets, label: '지금 보유자산', color: color('--color-text-hint') });
    return out;
  }

  // 축 눈금: 범위를 3 ~ 4칸으로 나눈 깔끔한 값 (1천만, 5천만, 1억 …)
  function ticks(lo, hi) {
    const span = hi - lo;
    const steps = [10_000_000, 20_000_000, 50_000_000, 100_000_000, 200_000_000, 500_000_000, 1_000_000_000];
    const step = steps.find((s) => span / s <= 4) || steps[steps.length - 1];
    const out = [];
    for (let v = Math.ceil(lo / step) * step; v <= hi; v += step) out.push(v);
    return out;
  }

  // ① 최근 1년 실거래
  // 그래프 하나의 틀: 제목과 한 줄 설명은 판 밖(위), 판 안에는 그래프와 범례, 출처만 (그래프를 크게)
  function block(title, say) {
    const wrap = el('div', 'scenario-chart-block');
    const head = el('h4', 'scenario-chart__title', title);
    const box = el('div', 'scenario-chart');
    wrap.append(head, say, box);
    return { wrap, box };
  }

  function tradesChart(data, result) {
    const done = data.trades.filter((t) => !t.is_canceled);
    const say = el('p', 'scenario-chart__say');
    // 한 줄에 들어가게 짧게 (2026-10-19). 금액은 끊기지 않게 굵은 글자 하나로
    say.append(document.createTextNode('최근 1년 거래 '), el('b', null, `${format.comma(done.length)}번`), document.createTextNode(' · 평균 '), el('b', null, format.won(data.avg_price)));
    const { wrap, box } = block(SCENARIO_CHART_TEXT.trades, say);

    const W = 320; const H = 180; const L = 46; const R = 312; const T = 14; const B = 150;
    const svg = svgEl('svg', { viewBox: `0 0 ${W} ${H}`, role: 'img', 'aria-label': `최근 1년 거래 ${done.length}건, 평균 ${format.won(data.avg_price)}` });
    const prices = data.trades.map((t) => t.price);
    const marks = lines(result);
    // 선이 거래보다 아주 멀면(1.6배 넘게) 축에 넣지 않고 위·아래 끝에 이름만 둔다 (점이 한쪽에 몰리지 않게)
    const pMin = Math.min(...prices, data.avg_price);
    const pMax = Math.max(...prices, data.avg_price);
    const inRange = marks.filter((m) => m.value <= pMax * 1.6 && m.value >= pMin / 1.6);
    const lo0 = Math.min(pMin, ...inRange.map((m) => m.value));
    const hi0 = Math.max(pMax, ...inRange.map((m) => m.value));
    const pad = (hi0 - lo0) * 0.12 || hi0 * 0.1;
    const lo = Math.max(0, lo0 - pad); const hi = hi0 + pad;
    const t0 = new Date(data.period_start).getTime(); const t1 = new Date(data.period_end).getTime();
    const span = Math.max(t1 - t0, 1);
    const X = (d) => L + 6 + (new Date(d).getTime() - t0) / span * (R - L - 12);
    const Y = (v) => B - (v - lo) / (hi - lo) * (B - T);

    ticks(lo, hi).forEach((v) => {
      svg.append(svgEl('line', { x1: L, x2: R, y1: Y(v), y2: Y(v), stroke: color('--color-line'), 'stroke-width': 1 }));
      svg.append(svgEl('text', { x: L - 6, y: Y(v) + 4, 'text-anchor': 'end', 'font-size': 10, fill: color('--color-text-sub') }, short(v)));
    });
    // 가로축: 처음, 가운데, 끝 달
    [t0, (t0 + t1) / 2, t1].forEach((t) => {
      const d = new Date(t);
      svg.append(svgEl('text', { x: X(d), y: B + 16, 'text-anchor': 'middle', 'font-size': 10, fill: color('--color-text-sub') },
        `${String(d.getFullYear()).slice(2)}.${String(d.getMonth() + 1).padStart(2, '0')}`));
    });
    const hline = (v, stroke, dash, label) => {
      svg.append(svgEl('line', { x1: L, x2: R, y1: Y(v), y2: Y(v), stroke, 'stroke-width': 1.5, 'stroke-dasharray': dash }));
      svg.append(svgEl('text', { x: R, y: Y(v) - 4, 'text-anchor': 'end', 'font-size': 10, 'font-weight': 700, fill: stroke }, label));
    };
    // 선 위에는 숫자만 (무슨 선인지는 아래 범례)
    inRange.forEach((m) => hline(m.value, m.color, '', short(m.value)));
    hline(data.avg_price, color('--color-primary'), '4 3', short(data.avg_price));
    // 범위 밖의 선: 끝에 이름과 화살표
    marks.filter((m) => !inRange.includes(m)).forEach((m) => {
      const up = m.value > hi;
      svg.append(svgEl('text', { x: R, y: up ? T - 2 : B - 4, 'text-anchor': 'end', 'font-size': 10, 'font-weight': 700, fill: m.color },
        `${up ? '↑' : '↓'} ${short(m.value)}`));
    });
    // 점. 같은 날 같은 값이 겹치면 해제된 거래를 조금 옆으로
    data.trades.forEach((t) => {
      const off = t.is_canceled ? 6 : 0;
      svg.append(svgEl('circle', {
        cx: X(t.contract_date) + off, cy: Y(t.price), r: 4.5,
        fill: t.is_canceled ? color('--color-bg') : color('--color-primary'),
        stroke: t.is_canceled ? color('--color-text-hint') : color('--color-bg'), 'stroke-width': 1.5,
      }));
    });
    box.append(svg);

    const legend = el('div', 'scenario-chart__legend');
    const item = (cls, style, text) => {
      const span = el('span');
      const mark = el('i', cls);
      Object.assign(mark.style, style);
      span.append(mark, document.createTextNode(text));
      legend.append(span);
    };
    item('scenario-chart__dot', { background: color('--color-primary') }, '거래');
    item('', { borderColor: color('--color-primary'), borderTopStyle: 'dashed' }, '평균가');
    marks.forEach((m) => item('', { borderColor: m.color }, m.label));
    box.append(legend);
    box.append(el('p', 'scenario-chart__src', `${SCENARIO_CHART_TEXT.source}, ${data.period_start} ~ ${data.period_end}`));
    return wrap;
  }

  // ② 같은 동 같은 면적 안에서의 위치. 한 곳뿐이면 그리지 않는다. 많으면 이 아파트 둘레 12곳만
  function neighborsChart(data, result, place) {
    const all = data.neighbors;
    if (all.length < 2) return null;
    const me = all.findIndex((n) => n.is_self);
    const rank = me + 1;
    let rows = all;
    if (all.length > 12) {
      const start = Math.min(Math.max(me - 5, 0), all.length - 12);
      rows = all.slice(start, start + 12);
    }
    const say = el('p', 'scenario-chart__say');
    const priciest = rank === all.length; // 가장 비싼 곳이면 글자와 이 아파트 막대를 빨간색으로 (2026-10-19)
    const where = rank === 1 ? '가장 싼 곳' : priciest ? '가장 비싼 곳' : `${rank}번째로 싼 곳`;
    say.append(document.createTextNode(`같은 면적 ${format.comma(all.length)}곳 가운데 `),
      el('b', priciest ? 'scenario-chart__priciest' : null, where)); // 동은 제목에 있다
    const selfBar = priciest ? color('--color-lack') : color('--color-primary');
    const selfText = priciest ? color('--color-lack-text') : color('--color-primary');
    const { wrap, box } = block(SCENARIO_CHART_TEXT.neighbors(place.dong, data.area_band), say);

    const rowH = 20; const L = 96; const R = 270; const T = 6;
    const funds = lines(result)[0];
    const vmax = Math.max(...rows.map((n) => n.avg_price));
    const showFunds = funds.value <= vmax * 1.3; // 너무 멀면 선을 빼고 글로만
    const top = Math.max(vmax, showFunds ? funds.value : 0) * 1.05;
    const X = (v) => L + v / top * (R - L);
    const yEnd = T + rows.length * rowH;
    const svg = svgEl('svg', { viewBox: `0 0 320 ${yEnd + (showFunds ? 18 : 4)}`, role: 'img', 'aria-label': `같은 동 같은 면적 ${all.length}곳 가운데 ${where}` });
    if (showFunds) svg.append(svgEl('line', { x1: X(funds.value), x2: X(funds.value), y1: T, y2: yEnd, stroke: funds.color, 'stroke-width': 2, opacity: 0.8 }));
    const panel = color('--new-control-bg') || '#f7f7f7';
    rows.forEach((n, i) => {
      const y = T + i * rowH;
      const self = n.is_self;
      const name = n.name.length > 9 ? `${n.name.slice(0, 8)}…` : n.name;
      svg.append(svgEl('text', { x: L - 6, y: y + 12, 'text-anchor': 'end', 'font-size': 10.5, 'font-weight': self ? 700 : 400, fill: self ? color('--color-text') : color('--color-text-sub') }, name));
      svg.append(svgEl('rect', { x: L, y: y + 3, width: Math.max(X(n.avg_price) - L, 2), height: 12, rx: 3, fill: self ? selfBar : color('--color-line-strong') }));
      svg.append(svgEl('text', { x: X(n.avg_price) + 4, y: y + 12, 'font-size': 9.5, 'font-weight': self ? 700 : 400, fill: self ? selfText : color('--color-text-sub'), stroke: panel, 'stroke-width': 3, 'paint-order': 'stroke' }, short(n.avg_price)));
    });
    if (showFunds) svg.append(svgEl('text', { x: X(funds.value), y: yEnd + 13, 'text-anchor': 'middle', 'font-size': 10, 'font-weight': 700, fill: color('--color-within-text') }, `${funds.label} ${short(funds.value)}`));
    box.append(svg);
    const src = all.length > rows.length ? `${SCENARIO_CHART_TEXT.neighborSource}. ${all.length}곳 가운데 이 아파트 둘레 ${rows.length}곳` : SCENARIO_CHART_TEXT.neighborSource;
    box.append(el('p', 'scenario-chart__src', showFunds ? `${src}. 초록 선은 ${funds.label}` : `${src}. ${funds.label}은 ${short(funds.value)}`));
    return wrap;
  }

  function fill(section, data, result, place) {
    const parts = [tradesChart(data, result)];
    const second = neighborsChart(data, result, place);
    if (second) parts.push(second);
    section.querySelector('.scenario-charts__body').replaceChildren(...parts);
  }

  return {
    section({ apartmentId, areaBand, result, place }) {
      const section = el('section', 'scenario-charts');
      // 제목 옆 (?) 는 다른 용어 설명과 같은 말풍선 (glossary.js)
      const title = el('h3', 'scenario-charts__title', SCENARIO_CHART_TEXT.title);
      if (typeof glossary !== 'undefined' && GLOSSARY_TERMS.charts) title.append(glossary.button('charts'));
      section.append(title);
      const body = el('div', 'scenario-charts__body');
      body.append(el('p', 'scenario-charts__wait', SCENARIO_CHART_TEXT.loading));
      section.append(body);
      load(apartmentId, areaBand).then((data) => {
        if (!section.isConnected && !section.parentNode) return; // 그사이 다시 그렸다
        if (!data.trades.length) { section.hidden = true; return; }
        fill(section, data, result, place);
      }).catch(() => {
        body.replaceChildren(el('p', 'scenario-charts__wait', SCENARIO_CHART_TEXT.failed));
      });
      return section;
    },
  };
})();
