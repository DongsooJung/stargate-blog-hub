const STORAGE_KEY = "stargateReader.v1";

const view = document.querySelector("#view");
const brandNote = document.querySelector("#brand-note");
let feed = null;
let visitors = null;
let topicId = "";

const state = loadState();

boot();

async function boot() {
  window.addEventListener("hashchange", render);
  const fold = window.matchMedia("(min-width: 900px) and (min-height: 700px), (horizontal-viewport-segments: 2)");
  fold.addEventListener("change", render);
  document.body.addEventListener("click", onClick);
  try {
    feed = await loadFeed();
    visitors = { ...feed.visitors, live: false };
    if (!state.acknowledgedAt) {
      state.acknowledgedAt = newestPublished(feed);
      saveState();
    }
    render();
    visitors = await liveVisitors(feed.visitors);
    if (location.hash === "" || location.hash === "#/" || location.hash.startsWith("#/?")) render();
    registerWorker();
  } catch (error) {
    view.innerHTML = `<p class="empty">글 목록을 열지 못했습니다. 잠시 후 다시 열어 주세요.</p>`;
    console.warn(error);
  }
}

async function loadFeed() {
  const local = await fetch("./feed.json", { cache: "no-store" });
  if (!local.ok) throw new Error("feed.json");
  const data = await local.json();
  if (!validFeed(data)) throw new Error("feed shape");
  return data;
}

function validFeed(data) {
  return Boolean(data && Array.isArray(data.posts) && data.posts.length >= 20 && Array.isArray(data.channels) && data.channels.length === 8);
}

async function liveVisitors(snapshot) {
  try {
    const response = await fetch(snapshot.endpoint, { cache: "no-store", credentials: "omit" });
    if (!response.ok) throw new Error(String(response.status));
    const data = await response.json();
    if (data.source !== "firebase" || !Number.isInteger(data.today) || !Number.isInteger(data.total)) {
      throw new Error("shape");
    }
    return { ...snapshot, today: data.today, total: data.total, date: data.date, live: true };
  } catch {
    return { ...snapshot, live: false };
  }
}

function registerWorker() {
  if (!("serviceWorker" in navigator) || location.protocol === "file:") return;
  navigator.serviceWorker.register("./sw.js").catch(() => {});
}

function loadState() {
  try {
    const saved = JSON.parse(localStorage.getItem(STORAGE_KEY) || "{}");
    return {
      bookmarks: saved.bookmarks || {},
      acknowledgedAt: saved.acknowledgedAt || "",
      notify: saved.notify !== false,
    };
  } catch {
    return { bookmarks: {}, acknowledgedAt: "", notify: true };
  }
}

function saveState() {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
  } catch {
    /* 저장소를 쓸 수 없는 브라우저에서는 이번 실행 동안만 유지한다. */
  }
}

function newestPublished(data) {
  return data.posts.reduce((max, post) => (post.publishedAt > max ? post.publishedAt : max), "");
}

function route() {
  const raw = (location.hash || "#/").replace(/^#/, "");
  const [path, query = ""] = raw.split("?");
  return { parts: path.split("/").filter(Boolean), query: new URLSearchParams(query) };
}

function render() {
  if (!feed) return;
  const { parts, query } = route();
  const screen = parts[0] || "home";
  document.querySelectorAll(".tabs a").forEach((link) => {
    const tab = link.dataset.tab;
    const current = screen === "read" ? "" : screen === "home" ? "home" : tab === screen ? tab : "";
    if (current && tab === current) link.setAttribute("aria-current", "page");
    else link.removeAttribute("aria-current");
  });
  if (screen === "channels" && parts[1]) {
    brandNote.textContent = channelName(parts[1]);
    view.innerHTML = channelScreen(parts[1]);
  } else if (screen === "channels") {
    brandNote.textContent = "고정된 8개 채널";
    view.innerHTML = channelsScreen();
  } else if (screen === "search") {
    brandNote.textContent = "제목 · 요약 · 채널 · 주제";
    view.innerHTML = searchScreen(query.get("q") || "");
  } else if (screen === "read") {
    brandNote.textContent = "글 읽기";
    view.innerHTML = readScreen(parts[1]);
  } else if (screen === "me") {
    brandNote.textContent = "이 기기에 남는 기록";
    view.innerHTML = meScreen();
  } else {
    brandNote.textContent = "흩어진 글을 한 목록으로";
    view.innerHTML = homeScreen();
  }
  view.focus({ preventScroll: true });
  const scroller = document.querySelector(".fold-list");
  const current = scroller?.querySelector(".is-current");
  if (scroller && current) {
    const delta = current.getBoundingClientRect().top - scroller.getBoundingClientRect().top;
    scroller.scrollTop += delta - 8;
  }
}

function homeScreen() {
  const selected = topicId;
  const posts = selected ? postsByTopic(selected) : feed.posts.filter((post) => post.onHome);
  const label = selected ? `${topicName(selected)} ${posts.length}편` : "시간순 20편";
  return `
    <section class="hero">
      <h1>오늘 읽을 글</h1>
      <p class="lead">발행 시각순으로 모은 글입니다.</p>
      ${visitorBlock()}
      <div class="topics" role="group" aria-label="주제">
        ${topicButton("", "시간순", !selected)}
        ${feed.topics.map((topic) => topicButton(topic.id, topic.name, selected === topic.id)).join("")}
      </div>
      <div class="section-label"><h2>${escapeHtml(label)}</h2><span>한국시간</span></div>
      <div class="list">${posts.map(postItem).join("") || `<p class="empty">이 주제의 글이 아직 목록에 없습니다.</p>`}</div>
      ${selected ? "" : latestMathLink()}
    </section>`;
}

function topicButton(id, name, pressed) {
  return `<button type="button" data-topic="${escapeHtml(id)}" aria-pressed="${pressed ? "true" : "false"}">${escapeHtml(name)}</button>`;
}

function visitorBlock() {
  const data = visitors || feed.visitors;
  const caption = data.live
    ? `${data.date} · 같은 브라우저 하루 1회`
    : `${data.date} 기준. 브랜드 주소에서 열면 갱신됩니다.`;
  return `
    <div class="stats">
      <div class="stat"><b>${Number(data.today).toLocaleString("ko-KR")}</b><span>오늘 방문</span></div>
      <div class="stat"><b>${Number(data.total).toLocaleString("ko-KR")}</b><span>누적 방문</span></div>
    </div>
    <p class="caption">${escapeHtml(caption)}</p>`;
}

function latestMathLink() {
  const post = feed.daily && feed.posts.find((item) => item.id === feed.daily.problemId);
  if (!post) return "";
  return `
    <a class="follow" href="#/read/${escapeHtml(post.id)}">
      <span>수학 채널의 최근 글</span>
      <strong>${escapeHtml(post.title)}</strong>
    </a>`;
}

function channelsScreen() {
  return `
    <div class="section-label"><h2>채널</h2><span>8곳</span></div>
    <div class="channels">
      ${feed.channels.map((channel) => `
        <a class="channel" href="#/channels/${escapeHtml(channel.id)}">
          <span>${escapeHtml(channel.platform)} · ${escapeHtml(readLabel(channel.read))}</span>
          <strong>${escapeHtml(channel.name)}</strong>
          <span>${escapeHtml(channel.blurb)}</span>
        </a>`).join("")}
    </div>`;
}

function channelScreen(id) {
  const channel = feed.channels.find((item) => item.id === id);
  if (!channel) return `<p class="empty">채널을 찾지 못했습니다.</p>`;
  const posts = feed.posts.filter((post) => post.channelId === id)
    .slice()
    .sort((a, b) => b.publishedAt.localeCompare(a.publishedAt));
  const outside = posts.length === 0;
  return `
    <a class="back" href="#/channels">채널 목록</a>
    <article class="panel">
      <h2>${escapeHtml(channel.name)}</h2>
      <p>${escapeHtml(channel.blurb)}</p>
      ${outside ? `<a class="primary" href="${escapeHtml(channel.url)}" target="_blank" rel="noopener">원문 채널 열기</a>` : ""}
    </article>
    <div class="list">${posts.map(postItem).join("")}</div>
    ${posts.length === 0 ? `<p class="empty">이 채널의 글은 앱 목록에 없고, 원문에서 이어 봅니다.</p>` : ""}`;
}

function searchScreen(q) {
  const query = q.trim();
  const posts = (query ? feed.posts.filter((post) => haystack(post).includes(query.toLowerCase())) : feed.posts.slice())
    .sort((a, b) => b.publishedAt.localeCompare(a.publishedAt));
  return `
    <form id="search-form" action="#/search" method="get">
      <label class="meta" for="q">검색</label>
      <input class="search" id="q" name="q" value="${escapeHtml(query)}" placeholder="제목, 요약, 채널, 주제" autocomplete="off">
    </form>
    <div class="section-label"><h2>${query ? "검색 결과" : "전체 목록"}</h2><span>${posts.length}편</span></div>
    <div class="list">${posts.map(postItem).join("") || `<p class="empty">맞는 글이 없습니다.</p>`}</div>`;
}

function unfoldedWide() {
  return window.matchMedia("(min-width: 900px) and (min-height: 700px), (horizontal-viewport-segments: 2)").matches;
}

function readScreen(id) {
  const article = readArticle(id);
  if (!unfoldedWide()) return article;
  const posts = topicId ? postsByTopic(topicId) : feed.posts.filter((post) => post.onHome);
  return `
    <div class="fold">
      <aside class="fold-list" aria-label="글 목록">
        <div class="list">${posts.map((post) => postItem(post, id)).join("")}</div>
      </aside>
      <div class="fold-article">${article}</div>
    </div>`;
}

function readArticle(id) {
  const post = feed.posts.find((item) => item.id === id);
  if (!post) return `<p class="empty">글을 찾지 못했습니다.</p>`;
  const channel = feed.channels.find((item) => item.id === post.channelId);
  const head = `
    <a class="back" href="#/">목록</a>
    <h1>${escapeHtml(post.title)}</h1>
    <div class="read-tools">
      <p class="meta">${escapeHtml(channel ? channel.name : "")} · ${escapeHtml(formatTime(post.publishedAt))} · ${escapeHtml(post.topic)}</p>
      <button class="bookmark" type="button" data-bookmark="${escapeHtml(post.id)}" aria-pressed="${state.bookmarks[post.id] ? "true" : "false"}">${state.bookmarks[post.id] ? "담김" : "담기"}</button>
    </div>`;
  if (post.read !== "in-app" || !post.bodyHtml) {
    const where = channel ? channel.platform : "원문";
    return `
      <article class="article">
        ${head}
        <div class="panel">
          <h2>${escapeHtml(where)}에서 이어 읽기</h2>
          <p>${escapeHtml(post.summary || "이 글의 본문은 원문에 있습니다.")}</p>
          <a class="primary" href="${escapeHtml(post.url)}" target="_blank" rel="noopener">원문 열기</a>
        </div>
      </article>`;
  }
  return `
    <article class="article">
      ${head}
      <div class="prose">${sanitize(post.bodyHtml)}</div>
      <p><a class="primary" href="${escapeHtml(post.url)}" target="_blank" rel="noopener">원문도 열기</a></p>
    </article>`;
}

function meScreen() {
  const saved = feed.posts.filter((post) => state.bookmarks[post.id]);
  const fresh = newPosts();
  const publisher = feed.publisher || {
    name: "STARGATE",
    legalName: "주식회사 별의문",
    email: "ceo@stargateedu.co.kr",
    package: "kr.co.stargateedu.blog",
  };
  const origin = feed.web.origin || "https://blog.stargateedu.co.kr/app/";
  const privacy = feed.web.privacy || "https://stargateedu.co.kr/privacy.html";
  return `
    <section>
      <h1>내 기록</h1>
      ${visitorBlock()}
      <article class="panel">
        <h2>새 글</h2>
        <p>이 기기에서 확인한 시각 이후에 목록에 들어온 글입니다. 알림 서버는 두지 않습니다.</p>
        <p><button class="text-button" type="button" data-notify="${state.notify ? "off" : "on"}">${state.notify ? "새 글 표시 켜짐" : "새 글 표시 꺼짐"}</button></p>
        <div class="list">${state.notify ? fresh.map(postItem).join("") : ""}</div>
        ${!state.notify || fresh.length === 0 ? `<p class="empty">새로 표시할 글이 없습니다.</p>` : `<p><button class="text-button" type="button" data-ack="1">이 목록을 확인했습니다</button></p>`}
      </article>
      <div class="section-label"><h2>북마크</h2><span>${saved.length}편</span></div>
      <div class="list">${saved.map(postItem).join("") || `<p class="empty">담아 둔 글이 없습니다. 글을 열고 담기를 누르면 이 기기에 남습니다.</p>`}</div>
      <div class="stack">
        <a class="panel" href="${escapeHtml(feed.web.feedback)}" target="_blank" rel="noopener"><h2>좋아요와 별점</h2><p>웹 허브에 있는 반응입니다. 앱에는 2단계에서 붙입니다.</p></a>
        <a class="panel" href="${escapeHtml(feed.web.survey)}" target="_blank" rel="noopener"><h2>1분 설문</h2><p>관심 주제와 추천 의향은 웹에서 받습니다.</p></a>
        <a class="panel" href="${escapeHtml(feed.web.community)}" target="_blank" rel="noopener"><h2>자유게시판</h2><p>질문과 의견은 웹 게시판에 있습니다.</p></a>
        <a class="panel" href="${escapeHtml(feed.web.play)}" target="_blank" rel="noopener"><h2>KOI 채점과 상담</h2><p>기존 Play 앱 kr.co.stargateedu.twa 에 남겨 둡니다.</p></a>
        <article class="panel">
          <h2>${escapeHtml(publisher.name)}</h2>
          <p>${escapeHtml(publisher.legalName)} · <a href="mailto:${escapeHtml(publisher.email)}">${escapeHtml(publisher.email)}</a></p>
          <p>공개 주소 ${escapeHtml(origin)} · 패키지 ${escapeHtml(publisher.package)}</p>
          <p><a href="${escapeHtml(privacy)}" target="_blank" rel="noopener">개인정보처리방침</a></p>
        </article>
      </div>
      <p class="caption">7일 방문과 수집 실패는 3단계에서 이 화면에 붙입니다. 지금 숫자는 오늘과 누적입니다. Notion 본문 파일은 ${escapeHtml(feed.notionArchive.generatedAt)} 이후 갱신되지 않았습니다.</p>
    </section>`;
}

function postItem(post, currentId) {
  const channel = feed.channels.find((item) => item.id === post.channelId);
  const current = post.id === currentId ? " is-current" : "";
  return `
    <article class="item${current}">
      <a href="#/read/${escapeHtml(post.id)}">
        <div class="meta">${escapeHtml(channel ? channel.name : "")} · ${escapeHtml(formatTime(post.publishedAt))}<span class="mode">${post.read === "in-app" ? "앱에서 읽기" : "원문"}</span></div>
        <h3>${escapeHtml(post.title)}</h3>
        <p>${escapeHtml(post.summary || post.topic)}</p>
      </a>
      <button class="bookmark" type="button" data-bookmark="${escapeHtml(post.id)}" aria-pressed="${state.bookmarks[post.id] ? "true" : "false"}" aria-label="${escapeHtml(post.title)} 북마크">${state.bookmarks[post.id] ? "담김" : "담기"}</button>
    </article>`;
}

function newPosts() {
  if (!state.acknowledgedAt) return [];
  return feed.posts
    .filter((post) => post.publishedAt > state.acknowledgedAt)
    .slice()
    .sort((a, b) => b.publishedAt.localeCompare(a.publishedAt));
}

function postsByTopic(id) {
  const name = topicName(id);
  return feed.posts
    .filter((post) => post.topic === name)
    .slice()
    .sort((a, b) => b.publishedAt.localeCompare(a.publishedAt));
}

function topicName(id) {
  const topic = feed.topics.find((item) => item.id === id);
  return topic ? topic.name : "";
}

function channelName(id) {
  const channel = feed.channels.find((item) => item.id === id);
  return channel ? channel.name : "채널";
}

function haystack(post) {
  const channel = feed.channels.find((item) => item.id === post.channelId);
  return [post.title, post.summary, post.topic, post.category, channel && channel.name, channel && channel.platform]
    .filter(Boolean)
    .join(" ")
    .toLowerCase();
}

function readLabel(read) {
  return read === "in-app" ? "앱에서 본문" : "원문으로 이동";
}

function formatTime(iso) {
  const parts = new Intl.DateTimeFormat("en-GB", {
    timeZone: "Asia/Seoul",
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    hourCycle: "h23",
  }).formatToParts(new Date(iso));
  const get = (type) => parts.find((part) => part.type === type).value;
  return `${get("year")}.${get("month")}.${get("day")} · ${get("hour")}:${get("minute")}`;
}

function onClick(event) {
  const topic = event.target.closest("[data-topic]");
  if (topic) {
    topicId = topic.dataset.topic;
    if ((location.hash || "#/") !== "#/" && !location.hash.startsWith("#/?")) location.hash = "#/";
    else render();
    return;
  }
  const bookmark = event.target.closest("[data-bookmark]");
  if (bookmark) {
    const id = bookmark.dataset.bookmark;
    if (state.bookmarks[id]) delete state.bookmarks[id];
    else state.bookmarks[id] = true;
    saveState();
    render();
    return;
  }
  if (event.target.closest("[data-ack]")) {
    const newest = newestPublished(feed);
    state.acknowledgedAt = newest;
    saveState();
    render();
    return;
  }
  if (event.target.closest("[data-notify]")) {
    state.notify = !state.notify;
    if (state.notify && !state.acknowledgedAt) {
      state.acknowledgedAt = feed.posts.reduce((max, post) => (post.publishedAt > max ? post.publishedAt : max), "");
    }
    saveState();
    render();
  }
  const form = event.target.closest("#search-form");
  if (form && event.target.id !== "q") return;
}

document.body.addEventListener("submit", (event) => {
  if (event.target.id !== "search-form") return;
  event.preventDefault();
  const q = new FormData(event.target).get("q") || "";
  location.hash = `#/search?q=${encodeURIComponent(String(q))}`;
});

document.body.addEventListener("input", (event) => {
  if (event.target.id !== "q") return;
  const q = event.target.value;
  history.replaceState(null, "", `#/search?q=${encodeURIComponent(q)}`);
  const start = event.target.selectionStart;
  render();
  const field = document.querySelector("#q");
  if (field) {
    field.focus();
    field.setSelectionRange(start, start);
  }
});

function escapeHtml(value) {
  return String(value ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

function sanitize(html) {
  const template = document.createElement("template");
  template.innerHTML = html;
  const allowed = new Set(["P", "BR", "H2", "H3", "H4", "UL", "OL", "LI", "BLOCKQUOTE", "STRONG", "EM", "A", "PRE", "CODE"]);
  const walk = (node) => {
    [...node.children].forEach((child) => {
      if (!allowed.has(child.tagName)) {
        child.replaceWith(document.createTextNode(child.textContent || ""));
        return;
      }
      [...child.attributes].forEach((attr) => {
        if (child.tagName === "A" && attr.name === "href" && /^https?:\/\//.test(attr.value)) return;
        child.removeAttribute(attr.name);
      });
      if (child.tagName === "A") {
        child.setAttribute("target", "_blank");
        child.setAttribute("rel", "noopener");
      }
      walk(child);
    });
  };
  walk(template.content);
  return template.innerHTML;
}
