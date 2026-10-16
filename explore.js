(() => {
  'use strict';

  const form = document.getElementById('exploreForm');
  const query = document.getElementById('exploreQuery');
  const list = document.getElementById('latestList');
  const featured = document.getElementById('featuredList');
  const count = document.getElementById('latestCount');
  const note = document.getElementById('latestVisibleNote');
  const more = document.getElementById('showMorePosts');
  const empty = document.getElementById('exploreEmpty');
  const readingHint = document.getElementById('exploreReadingHint');
  const topicHint = document.getElementById('exploreTopicHint');
  const reset = document.getElementById('resetExplore');
  const platformGroup = document.getElementById('platformFilters');
  const topicGroup = document.getElementById('topicFilters');
  if (!form || !query || !list || !count || !more || !empty) return;

  const mobileQuery = window.matchMedia('(max-width: 640px)');
  const state = { platform: '', topic: '', expanded: false };

  const cards = (root) => (root ? Array.from(root.querySelectorAll('.latest-card')) : []);
  const budget = () => (mobileQuery.matches ? 6 : 8);
  const haystack = (card) => (card.dataset.search || card.textContent || '').toLowerCase().replace(/\s+/g, ' ');

  const matches = (card) => {
    if (state.platform && card.dataset.platform !== state.platform) return false;
    if (state.topic && card.dataset.topic !== state.topic) return false;
    const term = query.value.trim().toLowerCase().replace(/\s+/g, ' ');
    if (term && !haystack(card).includes(term)) return false;
    return true;
  };

  const setPressed = (group, attr, value) => {
    if (!group) return;
    group.querySelectorAll('button').forEach((button) => {
      const selected = (button.dataset[attr] || '') === value;
      button.classList.toggle('active', selected);
      button.setAttribute('aria-pressed', selected ? 'true' : 'false');
    });
  };

  const render = () => {
    list.classList.add('explore-ready');
    const featuredMatches = cards(featured).filter(matches);
    const regularMatches = cards(list).filter(matches);
    const total = featuredMatches.length + regularMatches.length;
    const limit = state.expanded ? regularMatches.length : Math.max(0, budget() - featuredMatches.length);

    cards(featured).forEach((card) => {
      card.hidden = !featuredMatches.includes(card);
    });
    if (featured) featured.hidden = featuredMatches.length === 0;

    regularMatches.forEach((card, index) => {
      card.hidden = index >= limit;
    });
    cards(list).forEach((card) => {
      if (!regularMatches.includes(card)) card.hidden = true;
    });

    count.textContent = String(total);
    const shown = featuredMatches.length + Math.min(limit, regularMatches.length);
    if (note) {
      note.textContent = total
        ? `${shown}개 표시 중 · 조건에 맞는 글 ${total}건`
        : '';
    }
    const hasCards = cards(featured).length + cards(list).length > 0;
    empty.hidden = total !== 0 || !hasCards;
    if (readingHint) readingHint.hidden = !(total === 0 && state.topic === '독서·기록');
    if (topicHint) topicHint.hidden = !(total === 0 && state.topic === '도시·연구');
    const remaining = regularMatches.length - limit;
    more.hidden = remaining <= 0;
    more.textContent = remaining > 0 ? `더 보기 (${remaining})` : '더 보기';
  };

  const selectPlatform = (value) => {
    state.platform = value;
    state.expanded = false;
    setPressed(platformGroup, 'platform', value);
    render();
  };

  const selectTopic = (value) => {
    state.topic = value;
    state.expanded = false;
    setPressed(topicGroup, 'topic', value);
    render();
  };

  platformGroup?.addEventListener('click', (event) => {
    const button = event.target.closest('button[data-platform]');
    if (!button) return;
    selectPlatform(button.dataset.platform || '');
  });
  topicGroup?.addEventListener('click', (event) => {
    const button = event.target.closest('button[data-topic]');
    if (!button) return;
    selectTopic(button.dataset.topic || '');
  });
  query.addEventListener('input', () => {
    state.expanded = false;
    render();
  });
  form.addEventListener('submit', (event) => event.preventDefault());
  more.addEventListener('click', () => {
    state.expanded = true;
    render();
  });
  reset?.addEventListener('click', () => {
    query.value = '';
    selectPlatform('');
    selectTopic('');
  });
  document.querySelectorAll('[data-notion-jump]').forEach((link) => {
    link.addEventListener('click', () => {
      const button = document.querySelector(`#notionFeedFilters button[data-cat="${link.dataset.notionJump}"]`);
      button?.click();
    });
  });
  document.querySelectorAll('[data-topic-jump]').forEach((link) => {
    link.addEventListener('click', (event) => {
      event.preventDefault();
      selectTopic(link.dataset.topicJump || '');
      document.getElementById('latest')?.scrollIntoView({ behavior: 'smooth', block: 'start' });
    });
  });
  mobileQuery.addEventListener('change', () => {
    if (!state.expanded) render();
  });

  window.StargateHubExplore = {
    sync() {
      state.expanded = false;
      render();
    },
  };
  render();
})();
