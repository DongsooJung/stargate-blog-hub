(() => {
  'use strict';
  const counter = document.getElementById('blog-visitor-counter');
  if (!counter) return;
  const today = document.getElementById('blog-visitor-today');
  const total = document.getElementById('blog-visitor-total');
  const endpoint = 'https://stargate.stargate8225.workers.dev/api/blog-visitors';
  const prefix = 'stargateBlogVisitorsV1';
  const uuid = /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;
  let pending = false;
  let lastChecked = 0;
  let midnightTimer;

  function koreaDay() {
    return new Date(Date.now() + 9 * 3600000).toISOString().slice(0,10);
  }
  function browserId() {
    try {
      let id = localStorage.getItem(`${prefix}:id`);
      if (!id || !uuid.test(id)) {
        id = crypto.randomUUID();
        localStorage.setItem(`${prefix}:id`,id);
      }
      return id;
    } catch { return null; }
  }
  function wasCounted(day) {
    try { return localStorage.getItem(`${prefix}:counted`) === day; }
    catch { return false; }
  }
  async function update() {
    if (pending || document.visibilityState === 'hidden') return;
    pending = true;
    const day = koreaDay();
    const id = browserId();
    const record = Boolean(id && !wasCounted(day));
    try {
      const response = await fetch(endpoint,{
        method:record ? 'POST' : 'GET', cache:'no-store', credentials:'omit',
        ...(record ? {headers:{'Content-Type':'application/json'},body:JSON.stringify({visitorId:id})} : {}),
        signal:AbortSignal.timeout(12000),
      });
      if (!response.ok) throw Error(`Visitor counter HTTP ${response.status}`);
      const value = await response.json();
      if (value.source !== 'firebase' || !/^\d{4}-\d{2}-\d{2}$/.test(value.date) || ![value.today,value.total].every(n => Number.isSafeInteger(n) && n >= 0)) throw Error('Invalid visitor summary');
      today.textContent = value.today.toLocaleString('ko-KR');
      total.textContent = value.total.toLocaleString('ko-KR');
      counter.dataset.state = 'ready';
      counter.title = `${value.date} 한국시간 기준 · 같은 브라우저 하루 1회 · 누적은 일별 방문 합계`;
      if (record) {
        try { localStorage.setItem(`${prefix}:counted`,value.date); } catch {}
      }
      lastChecked = Date.now();
    } catch(error) {
      today.textContent = total.textContent = '—';
      counter.dataset.state = 'error';
      counter.title = '방문 통계를 불러오지 못했습니다. 잠시 후 다시 방문해 주세요.';
      console.warn('Blog visitor counter unavailable:',error.message);
    } finally {
      pending = false;
      clearTimeout(midnightTimer);
      const nextMidnight = Date.parse(`${koreaDay()}T00:00:00+09:00`) + 86400000;
      midnightTimer = setTimeout(update,Math.max(1000,nextMidnight - Date.now() + 1000));
    }
  }
  document.addEventListener('visibilitychange',() => {
    if (document.visibilityState === 'visible' && (Date.now() - lastChecked > 60000 || !wasCounted(koreaDay()))) update();
  });
  update();
})();
