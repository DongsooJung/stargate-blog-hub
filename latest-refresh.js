(() => {
  if (!window.__STARGATE_ANALYTICS_LOADER_REQUESTED__) {
    window.__STARGATE_ANALYTICS_LOADER_REQUESTED__ = true;
    const script = document.createElement('script');
    script.defer = true;
    script.src = 'https://stargateedu.co.kr/assets/analytics-loader.js';
    document.head.appendChild(script);
  }
})();

(() => {
  'use strict';

  const button = document.getElementById('refreshLatest');
  const list = document.querySelector('#latest .latest-list');
  const count = document.querySelector('#latest .count');
  const updated = document.querySelector('#latest .updated-pill');
  const status = document.getElementById('latestRefreshStatus');

  if (!button || !list || !count || !updated || !status) return;

  const label = button.querySelector('.refresh-label');
  const timeFormatter = new Intl.DateTimeFormat('ko-KR', {
    hour: '2-digit',
    minute: '2-digit',
    timeZone: 'Asia/Seoul',
  });

  const setBusy = (busy) => {
    button.disabled = busy;
    button.setAttribute('aria-busy', String(busy));
    list.setAttribute('aria-busy', String(busy));
    label.textContent = busy ? '확인 중…' : '최신 글 새로고침';
  };

  button.addEventListener('click', async () => {
    const previousUpdated = updated.textContent.trim();
    setBusy(true);
    status.classList.remove('error');
    status.textContent = '최신 배포본을 확인하고 있습니다.';

    try {
      const url = new URL(window.location.href);
      url.hash = '';
      url.searchParams.set('refresh', Date.now().toString());

      const response = await fetch(url, {
        cache: 'no-store',
        credentials: 'same-origin',
        headers: { Accept: 'text/html' },
      });
      if (!response.ok) throw new Error(`HTTP ${response.status}`);

      const nextDocument = new DOMParser().parseFromString(await response.text(), 'text/html');
      const nextList = nextDocument.querySelector('#latest .latest-list');
      const nextCount = nextDocument.querySelector('#latest .count');
      const nextUpdated = nextDocument.querySelector('#latest .updated-pill');
      if (!nextList || !nextCount || !nextUpdated) throw new Error('최신 글 영역을 찾지 못했습니다.');

      list.replaceChildren(...Array.from(nextList.children, (child) => child.cloneNode(true)));
      count.textContent = nextCount.textContent;
      updated.textContent = nextUpdated.textContent;
      document.body.dataset.postCount = nextCount.textContent.trim();

      const checkedAt = timeFormatter.format(new Date());
      status.textContent = nextUpdated.textContent.trim() === previousUpdated
        ? `새 게시물이 없습니다 · ${checkedAt} 확인`
        : `최신 포스팅으로 갱신했습니다 · ${checkedAt} 확인`;
    } catch (error) {
      console.error('Latest posts refresh failed:', error);
      status.classList.add('error');
      status.textContent = '새로고침하지 못했습니다. 잠시 후 다시 시도해 주세요.';
    } finally {
      setBusy(false);
    }
  });
})();

(() => {
  const addMathLinks = () => {
    const nav = document.querySelector('.nav-pills');
    if (nav && !nav.querySelector('a[href="./math/"],a[href="/math/"]')) {
      const link = document.createElement('a');
      link.href = './math/';
      link.textContent = '🧮 하루 한 문제';
      const posts = nav.querySelector('a[href="./posts/"]');
      if (posts) posts.insertAdjacentElement('afterend', link);
      else nav.appendChild(link);
    }

    const channels = document.querySelector('.channels');
    if (channels && !channels.querySelector('[data-math-daily]')) {
      const article = document.createElement('article');
      article.className = 'channel';
      article.dataset.mathDaily = 'true';
      article.innerHTML = '<div class="icon">🧮</div><h3>STARGATE MATH</h3><div class="meta">하루 한 문제 · 자동발행</div><p>성대경시형·황소형 중등 수학 문제를 문제·힌트·단계별 풀이로 한 문제씩 발행합니다.</p><a class="text-link" href="./math/">수학 블로그 →</a>';
      channels.insertBefore(article, channels.firstChild);
    }
  };
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', addMathLinks);
  else addMathLinks();
})();