(() => {
  'use strict';

  const feed = document.getElementById('notionFeed');
  const filters = document.getElementById('notionFeedFilters');
  const status = document.getElementById('notionFeedStatus');
  const sentinel = document.getElementById('notionFeedSentinel');
  const updated = document.getElementById('notionFeedUpdated');
  if (!feed || !filters || !status || !sentinel || !updated) return;

  const batchSize = 4;
  let allPosts = [];
  let visiblePosts = [];
  let rendered = 0;
  let category = '';

  const makeCard = (post, index) => {
    const article = document.createElement('article');
    article.className = 'notion-card';

    const meta = document.createElement('div');
    meta.className = 'notion-card__meta';

    const chip = document.createElement('span');
    chip.className = 'notion-card__category';
    chip.style.setProperty('--notion-color', post.color || '#0b3d91');
    chip.textContent = `${post.emoji || ''} ${post.category || ''}`.trim();

    const date = document.createElement('time');
    date.className = 'notion-card__date';
    date.dateTime = post.date || '';
    date.textContent = post.date || '';
    meta.append(chip, date);

    const title = document.createElement('h3');
    title.textContent = post.title || '제목 없음';

    const summary = document.createElement('p');
    summary.className = 'notion-card__summary';
    summary.textContent = post.summary || '';

    const actions = document.createElement('div');
    actions.className = 'notion-card__actions';

    const body = document.createElement('div');
    body.className = 'notion-card__body';
    body.id = `notion-post-body-${index}`;
    body.hidden = true;

    if (post.html) {
      const toggle = document.createElement('button');
      toggle.type = 'button';
      toggle.setAttribute('aria-expanded', 'false');
      toggle.setAttribute('aria-controls', body.id);
      toggle.textContent = '전체 읽기 ▾';
      toggle.addEventListener('click', () => {
        const opening = body.hidden;
        if (opening && !body.hasChildNodes()) body.innerHTML = post.html;
        body.hidden = !opening;
        toggle.setAttribute('aria-expanded', String(opening));
        toggle.textContent = opening ? '접기 ▴' : '전체 읽기 ▾';
      });
      actions.appendChild(toggle);
    }

    if (post.external_url) {
      const original = document.createElement('a');
      original.href = post.external_url;
      original.target = '_blank';
      original.rel = 'noopener';
      original.textContent = '원문 보기 ↗';
      actions.appendChild(original);
    }

    article.append(meta, title, summary, actions, body);
    return article;
  };

  const updateStatus = () => {
    if (!visiblePosts.length) {
      status.hidden = false;
      status.textContent = '이 카테고리에는 아직 발행된 글이 없습니다.';
    } else if (rendered >= visiblePosts.length) {
      status.hidden = true;
    } else {
      status.hidden = false;
      status.textContent = `스크롤하면 이어서 불러옵니다 (${rendered}/${visiblePosts.length})`;
    }
  };

  const renderNext = () => {
    if (rendered >= visiblePosts.length) {
      updateStatus();
      return;
    }
    visiblePosts.slice(rendered, rendered + batchSize).forEach((post, index) => {
      feed.appendChild(makeCard(post, rendered + index));
    });
    rendered = Math.min(rendered + batchSize, visiblePosts.length);
    updateStatus();
  };

  const applyFilter = (nextCategory) => {
    category = nextCategory || '';
    visiblePosts = category ? allPosts.filter((post) => post.category === category) : allPosts;
    rendered = 0;
    feed.replaceChildren();
    filters.querySelectorAll('button').forEach((button) => {
      button.classList.toggle('active', (button.dataset.cat || '') === category);
    });
    renderNext();
  };

  filters.addEventListener('click', (event) => {
    const button = event.target.closest('button');
    if (button) applyFilter(button.dataset.cat);
  });

  if ('IntersectionObserver' in window) {
    new IntersectionObserver((entries) => {
      if (entries[0].isIntersecting) renderNext();
    }, { rootMargin: '400px' }).observe(sentinel);
  } else {
    window.addEventListener('scroll', () => {
      if (sentinel.getBoundingClientRect().top < window.innerHeight + 400) renderNext();
    }, { passive: true });
  }

  fetch(`./posts/posts.json?t=${Date.now()}`, { cache: 'no-store' })
    .then((response) => {
      if (!response.ok) throw new Error(String(response.status));
      return response.json();
    })
    .then((data) => {
      allPosts = Array.isArray(data.posts) ? data.posts : [];
      if (data.generated_at) updated.textContent = `Notion 자동 갱신 · ${data.generated_at}`;
      applyFilter('');
    })
    .catch(() => {
      status.hidden = false;
      status.textContent = '글을 불러오지 못했습니다. 잠시 후 새로고침해 주세요.';
    });
})();
