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
