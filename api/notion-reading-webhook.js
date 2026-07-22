const crypto = require("node:crypto");

const REPOSITORY = process.env.GITHUB_REPOSITORY || "DongsooJung/stargate-blog-hub";
const FEED_PATH = process.env.READING_FEED_PATH || "reading/posts.json";
const BRANCH = process.env.GITHUB_BRANCH || "main";
const COLORS = [
  "linear-gradient(135deg,#24404f,#c58a52)",
  "linear-gradient(135deg,#173e49,#55a69c)",
  "linear-gradient(135deg,#38344d,#8f7dae)",
  "linear-gradient(135deg,#5b346c,#d26e91)",
  "linear-gradient(135deg,#245d45,#e3ab3f)",
];

function send(res, status, body) {
  res.status(status).setHeader("content-type", "application/json; charset=utf-8");
  res.setHeader("cache-control", "no-store");
  res.end(JSON.stringify(body));
}

function safeEqual(left, right) {
  const a = Buffer.from(String(left || ""));
  const b = Buffer.from(String(right || ""));
  return a.length === b.length && crypto.timingSafeEqual(a, b);
}

function primitive(value) {
  if (value == null) return "";
  if (["string", "number", "boolean"].includes(typeof value)) return value;
  if (Array.isArray(value)) {
    return value
      .map((item) => primitive(item))
      .filter((item) => item !== "")
      .join(", ");
  }
  if (typeof value === "object") {
    if ("plain_text" in value) return value.plain_text;
    if ("content" in value && typeof value.content === "string") return value.content;
    if ("name" in value && typeof value.name === "string") return value.name;
    if ("start" in value && typeof value.start === "string") return value.start;
    if ("checkbox" in value) return Boolean(value.checkbox);
    if ("number" in value) return value.number;
    if ("url" in value && typeof value.url === "string") return value.url;
    for (const key of ["title", "rich_text", "select", "multi_select", "date"] ) {
      if (key in value) return primitive(value[key]);
    }
  }
  return "";
}

function findNamed(node, target) {
  if (!node || typeof node !== "object") return undefined;
  if (Object.prototype.hasOwnProperty.call(node, target)) return node[target];
  for (const value of Object.values(node)) {
    const found = findNamed(value, target);
    if (found !== undefined) return found;
  }
  return undefined;
}

function field(payload, name, fallback = "") {
  const found = findNamed(payload, name);
  const result = primitive(found);
  return result === "" ? fallback : result;
}

function truthy(value) {
  return value === true || ["true", "yes", "1", "__YES__", "예", "공개"].includes(String(value));
}

function pageId(payload, title) {
  const candidates = [
    field(payload, "page_id"),
    field(payload, "pageId"),
    field(payload, "id"),
    field(payload, "url"),
  ].filter(Boolean);
  const notionId = candidates.find((value) => /[0-9a-f]{32}|[0-9a-f-]{36}/i.test(String(value)));
  if (notionId) {
    const match = String(notionId).match(/[0-9a-f]{32}|[0-9a-f-]{36}/i);
    return match[0].replaceAll("-", "");
  }
  return crypto.createHash("sha256").update(title).digest("hex").slice(0, 32);
}

function colorFor(category) {
  const hash = crypto.createHash("sha256").update(category).digest();
  return COLORS[hash.readUInt32BE(0) % COLORS.length];
}

function toPost(payload) {
  const title = String(field(payload, "도서명", "제목 없음")).trim();
  const category = String(field(payload, "대분류", "기타")).trim();
  const stars = String(field(payload, "평점", ""));
  const url = String(field(payload, "Notion URL", field(payload, "url", "")));
  return {
    id: pageId(payload, title),
    title,
    author: String(field(payload, "저자", "저자 미입력")),
    category,
    rating: Math.min(5, (stars.match(/⭐/g) || []).length || Number(stars) || 0),
    pages: Number(field(payload, "페이지수", 0)) || 0,
    date: String(field(payload, "완독일", new Date().toISOString().slice(0, 10))).slice(0, 10),
    oneLine: String(field(payload, "한줄평", "")),
    quote: String(field(payload, "인용문", "기억할 문장 미입력")),
    review: String(field(payload, "독후감본문", field(payload, "적용 액션", ""))),
    recommend: String(field(payload, "추천대상", "추천 대상 미입력")),
    keywords: String(field(payload, "핵심키워드", "")),
    notionUrl: url,
    color: colorFor(category),
  };
}

async function github(path, options = {}) {
  const token = process.env.GITHUB_CONTENTS_TOKEN;
  if (!token) throw new Error("GITHUB_CONTENTS_TOKEN is not configured");
  const response = await fetch(`https://api.github.com/repos/${REPOSITORY}/${path}`, {
    ...options,
    headers: {
      accept: "application/vnd.github+json",
      authorization: `Bearer ${token}`,
      "x-github-api-version": "2022-11-28",
      "user-agent": "stargate-reading-webhook/1.0",
      ...(options.headers || {}),
    },
  });
  const data = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(`GitHub API ${response.status}: ${data.message || "request failed"}`);
  return data;
}

async function updateFeed(post, publish) {
  const encodedPath = FEED_PATH.split("/").map(encodeURIComponent).join("/");
  const current = await github(`contents/${encodedPath}?ref=${encodeURIComponent(BRANCH)}`);
  const feed = JSON.parse(Buffer.from(current.content.replace(/\n/g, ""), "base64").toString("utf8"));
  const posts = Array.isArray(feed.posts) ? feed.posts : [];
  const same = (item) => item.id === post.id || item.title === post.title;
  const next = publish ? [post, ...posts.filter((item) => !same(item))] : posts.filter((item) => !same(item));
  next.sort((a, b) => String(b.date || "").localeCompare(String(a.date || "")));
  const body = {
    message: publish
      ? `chore(reading): ${post.title} 웹훅 발행`
      : `chore(reading): ${post.title} 공개 해제`,
    content: Buffer.from(JSON.stringify({
      generatedAt: new Date().toISOString(),
      source: "Notion webhook · 📖 독서 LOG & 독후감",
      posts: next,
    }, null, 2) + "\n").toString("base64"),
    sha: current.sha,
    branch: BRANCH,
  };
  await github(`contents/${encodedPath}`, {
    method: "PUT",
    headers: { "content-type": "application/json" },
    body: JSON.stringify(body),
  });
  return next.length;
}

module.exports = async function handler(req, res) {
  if (req.method === "GET") return send(res, 200, { ok: true, service: "stargate-reading-webhook" });
  if (req.method !== "POST") return send(res, 405, { ok: false, error: "method_not_allowed" });

  const expected = process.env.NOTION_WEBHOOK_KEY;
  const received = req.headers["x-stargate-webhook-key"];
  if (!expected || !safeEqual(received, expected)) {
    return send(res, 401, { ok: false, error: "unauthorized" });
  }

  try {
    const payload = typeof req.body === "string" ? JSON.parse(req.body) : (req.body || {});
    const post = toPost(payload);
    if (!post.title || post.title === "제목 없음") {
      return send(res, 422, { ok: false, error: "missing_title" });
    }
    const publish = truthy(field(payload, "웹공개")) && ["완독", "재독"].includes(String(field(payload, "독서상태")));
    const count = await updateFeed(post, publish);
    return send(res, 200, { ok: true, action: publish ? "published" : "unpublished", title: post.title, count });
  } catch (error) {
    console.error(error);
    return send(res, 500, { ok: false, error: "sync_failed" });
  }
};
