(() => {
  'use strict';
  const menu = document.querySelector('.nav-more');
  if (menu) {
    document.addEventListener('click',event => {
      if (!menu.contains(event.target) || event.target.closest('a')) menu.open = false;
    });
    menu.addEventListener('keydown',event => {
      if (event.key === 'Escape') { menu.open = false; menu.querySelector('summary').focus(); }
    });
  }

  const button = document.getElementById('refreshLatest');
  const list = document.querySelector('#latest .latest-list');
  const count = document.querySelector('#latest .count');
  const updated = document.querySelector('#latest .updated-pill');
  const status = document.getElementById('latestRefreshStatus');
  const more = document.getElementById('latest-show-more');
  const visibleStatus = document.getElementById('latest-visible-status');
  if (!button || !list || !count || !updated || !status) return;

  const label = button.querySelector('.refresh-label');
  const timeFormatter = new Intl.DateTimeFormat('ko-KR',{hour:'2-digit',minute:'2-digit',timeZone:'Asia/Seoul'});
  const pageSize = 6;
  let visibleLimit = pageSize;
  const cards = () => Array.from(list.querySelectorAll('.latest-item'));
  function paginate() {
    if (!more || !visibleStatus) return;
    const items = cards();
    items.forEach((item,index) => { item.hidden = index >= visibleLimit; });
    const shown = Math.min(visibleLimit,items.length);
    visibleStatus.textContent = items.length ? `전체 ${items.length}개 중 ${shown}개` : '';
    more.hidden = shown >= items.length;
    more.textContent = `글 더 보기 (${Math.min(pageSize,items.length-shown)}개) ↓`;
  }
  more?.addEventListener('click',() => {
    const firstNew = cards()[visibleLimit];
    visibleLimit += pageSize;
    paginate();
    if (more.hidden) firstNew?.querySelector('a')?.focus({preventScroll:true});
  });
  paginate();

  function fingerprint(element) {
    return JSON.stringify(Array.from(element.querySelectorAll('.latest-item')).map(item => [
      item.querySelector('a')?.getAttribute('href'),
      item.querySelector('a')?.textContent.trim(),
      item.querySelector('time')?.getAttribute('datetime'),
    ]));
  }
  const setBusy = busy => {
    button.disabled = busy;
    button.setAttribute('aria-busy',String(busy));
    list.setAttribute('aria-busy',String(busy));
    label.textContent = busy ? '확인 중…' : '업데이트 확인';
  };
  button.addEventListener('click',async() => {
    const previous = fingerprint(list);
    setBusy(true);
    status.classList.remove('error');
    status.textContent = '배포된 최신 목록을 확인하고 있습니다.';
    try {
      const url = new URL(window.location.href);
      url.hash = '';
      url.searchParams.set('refresh',Date.now().toString());
      const response = await fetch(url,{cache:'no-store',credentials:'same-origin',headers:{Accept:'text/html'},signal:AbortSignal.timeout(15000)});
      if (!response.ok) throw Error(`HTTP ${response.status}`);
      const nextDocument = new DOMParser().parseFromString(await response.text(),'text/html');
      const nextList = nextDocument.querySelector('#latest .latest-list');
      const nextCount = nextDocument.querySelector('#latest .count');
      const nextUpdated = nextDocument.querySelector('#latest .updated-pill');
      if (!nextList || !nextCount || !nextUpdated) throw Error('최신 글 영역을 찾지 못했습니다.');
      const changed = fingerprint(nextList) !== previous;
      list.replaceChildren(...Array.from(nextList.children,child => child.cloneNode(true)));
      count.textContent = nextCount.textContent;
      updated.textContent = nextUpdated.textContent;
      document.body.dataset.postCount = nextCount.textContent.trim();
      paginate();
      const checkedAt = timeFormatter.format(new Date());
      status.textContent = changed ? `새 목록을 반영했습니다 · ${checkedAt} 확인` : `최신 배포본과 같은 목록입니다 · ${checkedAt} 확인`;
    } catch(error) {
      console.warn('Latest posts refresh failed:',error.message);
      status.classList.add('error');
      status.textContent = '확인하지 못했습니다. 기존 목록을 유지합니다.';
    } finally { setBusy(false); }
  });
})();