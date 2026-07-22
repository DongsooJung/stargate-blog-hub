const assert = require("node:assert/strict");

process.env.NOTION_WEBHOOK_KEY = "test-webhook-key";
process.env.GITHUB_CONTENTS_TOKEN = "test-github-token";

const currentFeed = {
  generatedAt: "2026-07-21T21:50:00Z",
  source: "test",
  posts: [],
};
let written;
global.fetch = async (_url, options = {}) => {
  if (!options.method || options.method === "GET") {
    return {
      ok: true,
      json: async () => ({
        sha: "feed-sha",
        content: Buffer.from(JSON.stringify(currentFeed)).toString("base64"),
      }),
    };
  }
  written = JSON.parse(options.body);
  return { ok: true, json: async () => ({ content: { sha: "new-sha" } }) };
};

const handler = require("../api/notion-reading-webhook");

function response() {
  return {
    statusCode: 0,
    headers: {},
    status(code) { this.statusCode = code; return this; },
    setHeader(name, value) { this.headers[name] = value; },
    end(body) { this.body = JSON.parse(body); },
  };
}

(async () => {
  const req = {
    method: "POST",
    headers: { "x-stargate-webhook-key": "test-webhook-key" },
    body: {
      data: {
        id: "383339ae-11e5-8124-9fec-d6d84b4810a2",
        properties: {
          도서명: { title: [{ plain_text: "도시개발론" }] },
          저자: { rich_text: [{ plain_text: "홍길동" }] },
          대분류: { select: { name: "도시·부동산·건축" } },
          평점: { select: { name: "⭐⭐⭐⭐" } },
          페이지수: { number: 320 },
          완독일: { date: { start: "2026-04-15" } },
          한줄평: { rich_text: [{ plain_text: "한줄평" }] },
          인용문: { rich_text: [{ plain_text: "인용문" }] },
          독후감본문: { rich_text: [{ plain_text: "본문" }] },
          추천대상: { multi_select: [{ name: "도시·부동산 실무" }] },
          핵심키워드: { rich_text: [{ plain_text: "도시개발" }] },
          독서상태: { select: { name: "완독" } },
          웹공개: { checkbox: true },
        },
      },
    },
  };
  const res = response();
  await handler(req, res);
  assert.equal(res.statusCode, 200);
  assert.equal(res.body.action, "published");
  const nextFeed = JSON.parse(Buffer.from(written.content, "base64").toString("utf8"));
  assert.equal(nextFeed.posts[0].title, "도시개발론");
  assert.equal(nextFeed.posts[0].rating, 4);
  assert.equal(nextFeed.posts[0].review, "본문");
  console.log("notion-reading-webhook: ok");
})().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
