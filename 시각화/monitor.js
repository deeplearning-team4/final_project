// <head> 에서 읽는다(feed_data.js 가 있으면 그 뒤). 모든 모니터링 페이지 공통: 사이드바, 수신 기록(대시보드가 24샷을 새로 시작할 때마다 다음 24샷), 주의 조건 판정, 작은 그림 도우미
(() => {
  const TYPES = ["정상", "미충전", "기공", "박리", "얼룩", "변형", "기타"];
  const BATCH = 24, KEY = "team3.monitor.v2", MAX_HIST = 200;
  // 처음 여는 24샷의 시작 위치(FEED 순번). 맨 앞 24샷(shot 2~69)은 경보가 0건이라, 2번째 샷에서 바로 경보가 나오는 shot 381부터 재생한다
  const START = 108;
  const FEED = window.FEED || [];
  const $ = id => document.getElementById(id);
  const fmt = v => v.toLocaleString("ko-KR");
  const pad = n => String(n).padStart(2, "0");
  const hms = t => { const d = new Date(t); return `${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`; };

  // 샷 한 줄 → 객체. 필드 순서는 feed_data.js 머리말과 같다
  const shot = r => ({ id: r[0], prod: r[1], melt: r[2], coolT: r[3], coolP: r[4], cast: r[5], cycle: r[6], fac: r[7], spray: r[8], s1: r[9], pred: r[10], dup: r[11] });

  // 주의 조건 — train 직접 집계(보고서 ⑤)와 같은 기준
  const CONDS = [
    { key: "blow", name: "기공", test: s => s.prod === 2 && s.coolT <= 26.4 },
    { key: "stain", name: "얼룩", test: s => s.prod === 2 && s.coolP >= (window.STAIN_CUT || 2.74) },
    { key: "deform", name: "변형", test: s => s.prod === 1 && s.s1 === 1.0 && s.fac > 34.7 && s.melt <= 700 && s.spray <= 8.0 },
  ];
  const condsOf = s => CONDS.filter(c => c.test(s));

  // 수신 기록: {hist: [{t, from, n}]} · 브라우저에만 저장, 막혀 있으면 이번 화면에서만 유지
  let mem = null;
  const read = () => { try { const v = JSON.parse(localStorage.getItem(KEY)); if (v && Array.isArray(v.hist)) return v; } catch (e) {} return mem; };
  const write = st => { mem = st; try { localStorage.setItem(KEY, JSON.stringify(st)); } catch (e) {} };
  const batchShots = b => Array.from({ length: b.n }, (_, i) => shot(FEED[(b.from + i) % FEED.length]));

  const state = () => read() || { hist: [] };
  // 대시보드가 새 24샷을 시작할 때마다(처음 열 때 · 24샷이 끝나 이어서 생산할 때) 다음 24샷을 받는다
  // at 을 주면 그 FEED 순번부터(대시보드 「제품 전환 보기」)
  const receive = at => {
    const st = state(), last = st.hist[st.hist.length - 1];
    const from = at != null ? ((at % FEED.length) + FEED.length) % FEED.length : last ? (last.from + last.n) % FEED.length : START;
    st.hist.push({ t: Date.now(), from, n: BATCH });
    if (st.hist.length > MAX_HIST) st.hist = st.hist.slice(-MAX_HIST);
    write(st);
    return st;
  };
  // 지금까지 기록된 샷 · cut = 마지막 묶음에서 기록된 수(없으면 전부)
  const collected = cut => { const h = state().hist; return h.flatMap((b, i) => { const s = batchShots(b); return i === h.length - 1 && cut != null ? s.slice(0, cut) : s; }); };
  const reset = () => { mem = null; try { localStorage.removeItem(KEY); } catch (e) {} };

  // 미니 막대
  const spark = (el, vals, hl = vals.length - 1) => { const m = Math.max(...vals, 1e-9);
    el.innerHTML = vals.map((v, i) => `<i class="${i === hl ? "hl" : ""}" style="height:${Math.max(8, v / m * 100)}%" title="${+(+v).toFixed(3)}"></i>`).join(""); };
  // 원형 링
  const ring = (el, pct, trk = "var(--track)", col = "var(--orange)") => { const C = 2 * Math.PI * 24;
    el.innerHTML = `<svg viewBox="0 0 56 56"><circle cx="28" cy="28" r="24" fill="none" stroke="${trk}" stroke-width="5"/>
      <circle cx="28" cy="28" r="24" fill="none" stroke="${col}" stroke-width="5" stroke-linecap="round" stroke-dasharray="${C * pct / 100} ${C}"/></svg>${pct}%`; };
  // 반원 게이지
  const gauge = (el, v) => { const r = 80, L = Math.PI * r, arc = `M20 100 A80 80 0 0 1 180 100`;
    el.innerHTML = `<path d="${arc}" fill="none" stroke="var(--frame)" stroke-width="22" stroke-dasharray="0 ${L * v + 4} ${L} 0"/>
      <path d="${arc}" fill="none" stroke="var(--orange)" stroke-width="22" stroke-dasharray="${L * v} ${L}"/>`; };
  // 가로 막대 목록 [{label, sub, value, text, color}]
  const hbars = (el, rows, max) => { const m = max || Math.max(...rows.map(r => r.value), 1e-9);
    el.innerHTML = rows.map(r => `<div class="r"><span>${r.label}${r.sub ? `<span class="s">${r.sub}</span>` : ""}</span>
      <div class="t"><i style="width:${r.value / m * 100}%;background:${r.color || "var(--green)"}"></i></div><b>${r.text}</b></div>`).join(""); };
  const predChip = p => p ? `<span class="chip al">${TYPES[p]}</span>` : `<span class="chip ok">정상</span>`;
  const condChips = s => condsOf(s).map(c => `<span class="chip cd">${c.name} 조건</span>`).join(" ");

  // 사이드바
  const PAGES = [
    ["dashboard", "index.html", "대시보드", '<path d="M2 7l5-4.5L12 7v5H2z"/>'],
    ["feed", "feed.html", "입력 기록", '<path d="M2 3h10M2 7h10M2 11h6"/>'],
    ["types", "types.html", "유형별 검출", '<path d="M2 12V7M7 12V3M12 12V8"/>'],
    ["conditions", "conditions.html", "주의 조건", '<path d="M7 2l5.5 10h-11z M7 6v3"/>'],
    ["rules", "rules.html", "경보 기준", '<circle cx="7" cy="7" r="5"/><path d="M7 4v3l2 2"/>'],
  ];
  // 사이드바: 각 페이지가 <aside class="side"></aside> 바로 뒤에서 MON.side() 로 부른다(첫 그림부터 메뉴가 그려져 있게)
  const side = () => {
    const side = document.querySelector(".side"); if (!side || side.children.length) return;
    const cur = document.body.dataset.page;
    side.innerHTML = `<a class="logo" href="index.html"><svg width="22" height="22" viewBox="0 0 22 22"><path d="M3 6h12l-4 5H3z" fill="#3DBE77"/><path d="M7 11h12l-4 5H7z" fill="#8FE0B2"/></svg>3조 불량예측</a>
      <div class="cap">메뉴</div>
      <nav class="nav">${PAGES.map(([k, href, name, ic]) => `<a class="${k === cur ? "on" : ""}" href="${href}"><span class="ic"><svg viewBox="0 0 14 14">${ic}</svg></span>${name}</a>`).join("")}
        <hr><a class="${cur === "story" ? "on" : ""}" href="스토리페이지.html"><span class="ic"><svg viewBox="0 0 14 14"><path d="M3 1.5h5.5L11 4v8.5H3z M5 7h4M5 9.5h4"/></svg></span>결과 리포트</a></nav>
      <div class="acct"><span class="av">3조</span><div><b>다이캐스팅</b><span>KNN · public 0.589</span></div></div>`;
  };

  // 페이지 전환을 매끄럽게: <head> 의 한 줄 스크립트가 html 에 boot 를 달아 작업 영역 안 내용만 잠깐 숨긴다(틀·사이드바·밝은 작업판은 첫 그림부터 보임).
  // 이 페이지 글자에 필요한 Pretendard 가 준비되면(최대 0.4초) boot 를 떼고 enter 를 달아 내용이 0.22초 동안 들어온다 → 글꼴이 바뀌며 글자가 밀리는 장면이 화면에 안 나온다
  const root = document.documentElement, still = matchMedia("(prefers-reduced-motion: reduce)").matches;
  const show = anim => { if (!root.classList.contains("boot")) return; root.classList.remove("boot"); if (anim && !still) root.classList.add("enter"); };
  addEventListener("pagereveal", e => { if (e.viewTransition) show(false); }); // 브라우저 view transition 이 돌면 그 교차 페이드에 맡긴다
  document.addEventListener("DOMContentLoaded", () => {
    const chars = [...new Set((document.querySelector(".frame") || document.body).textContent.replace(/\s+/g, ""))].join(""); // 화면 글자만(스크립트 제외)
    Promise.race([document.fonts.load('16px "Pretendard Variable"', chars || "가"), new Promise(r => setTimeout(r, 400))]).catch(() => {}).then(() => show(true));
  });

  window.MON = { side, TYPES, BATCH, FEED, CONDS, $, fmt, hms, shot, condsOf, state, receive, reset, collected, batchShots, spark, ring, gauge, hbars, predChip, condChips };
})();
