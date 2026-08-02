#!/usr/bin/env python3
"""노션 API → posts/posts.json 동기화 스크립트.

「📰 포털 블로그 포스트」 노션 데이터베이스에서 상태=발행 인 글을 읽어
blog.stargateedu.co.kr/posts/ 스크롤 블로그가 렌더링하는 posts/posts.json 을 생성한다.

독서 기록(`sync_notion_reading.py` → `reading/posts.json`)과는 별개 DB·별개 출력이다.

필요 환경변수:
  NOTION_TOKEN        노션 내부 통합(integration) 시크릿 (ntn_... / secret_...)
  NOTION_DATABASE_ID  (선택) 데이터베이스 ID — 기본값은 아래 DEFAULT_DATABASE_ID

통합(integration)에 데이터베이스가 공유되어 있어야 한다:
노션에서 DB 열기 → ⋯ → 연결(Connections) → 통합 선택.
"""

import html
import json
import os
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

API_BASE = "https://api.notion.com/v1"
NOTION_VERSION = "2022-06-28"
DEFAULT_DATABASE_ID = "074907c157fd450c8708168b362ac5ee"

OUT_PATH = Path(os.environ.get(
    "OUT_PATH", Path(__file__).resolve().parent.parent / "posts" / "posts.json"))
KST = timezone(timedelta(hours=9))

# 노션 select 옵션명 → 포털 카테고리 메타(이모지·색상)
CATEGORY_META = {
    "교육·입시": {"emoji": "🎓", "color": "#2E7D32"},
    "AI·테크": {"emoji": "🤖", "color": "#1E5BC6"},
    "창업·경영": {"emoji": "🏢", "color": "#E65100"},
    "도시·연구": {"emoji": "🏙️", "color": "#6A1B9A"},
    "출판·서평": {"emoji": "📚", "color": "#5D4037"},
    "시사·정치": {"emoji": "🗳️", "color": "#B26A00"},
    "공지": {"emoji": "📢", "color": "#C62828"},
}


def api_request(path: str, payload: dict | None = None) -> dict:
    token = os.environ["NOTION_TOKEN"]
    req = urllib.request.Request(
        f"{API_BASE}{path}",
        data=json.dumps(payload).encode() if payload is not None else None,
        headers={
            "Authorization": f"Bearer {token}",
            "Notion-Version": NOTION_VERSION,
            "Content-Type": "application/json",
        },
        method="POST" if payload is not None else "GET",
    )
    for attempt in range(4):
        try:
            with urllib.request.urlopen(req, timeout=30) as res:
                return json.load(res)
        except urllib.error.HTTPError as e:
            if e.code == 429 and attempt < 3:
                time.sleep(int(e.headers.get("Retry-After", "2")))
                continue
            body = e.read().decode(errors="replace")
            raise RuntimeError(f"Notion API {e.code} {path}: {body[:300]}") from e
    raise RuntimeError(f"Notion API 재시도 초과: {path}")


def rich_text_to_plain(rich: list) -> str:
    return "".join(t.get("plain_text", "") for t in rich)


def rich_text_to_html(rich: list) -> str:
    parts = []
    for t in rich:
        text = html.escape(t.get("plain_text", ""))
        text = text.replace("\n", "<br>")
        ann = t.get("annotations", {})
        if ann.get("code"):
            text = f"<code>{text}</code>"
        if ann.get("bold"):
            text = f"<strong>{text}</strong>"
        if ann.get("italic"):
            text = f"<em>{text}</em>"
        if ann.get("strikethrough"):
            text = f"<s>{text}</s>"
        if ann.get("underline"):
            text = f"<u>{text}</u>"
        href = t.get("href")
        if href:
            text = f'<a href="{html.escape(href)}" target="_blank" rel="noopener">{text}</a>'
        parts.append(text)
    return "".join(parts)


def fetch_children(block_id: str) -> list:
    blocks, cursor = [], None
    while True:
        path = f"/blocks/{block_id}/children?page_size=100"
        if cursor:
            path += f"&start_cursor={cursor}"
        data = api_request(path)
        blocks.extend(data.get("results", []))
        if not data.get("has_more"):
            return blocks
        cursor = data.get("next_cursor")


def blocks_to_html(blocks: list, depth: int = 0) -> str:
    out: list[str] = []
    list_tag = None  # 열려 있는 목록 태그: 'ul' | 'ol'

    def close_list():
        nonlocal list_tag
        if list_tag:
            out.append(f"</{list_tag}>")
            list_tag = None

    for b in blocks:
        btype = b.get("type", "")
        data = b.get(btype, {})
        rich = data.get("rich_text", [])
        inner = rich_text_to_html(rich)
        children_html = ""
        if b.get("has_children") and depth < 3:
            children_html = blocks_to_html(fetch_children(b["id"]), depth + 1)

        if btype in ("bulleted_list_item", "numbered_list_item"):
            tag = "ul" if btype == "bulleted_list_item" else "ol"
            if list_tag != tag:
                close_list()
                out.append(f"<{tag}>")
                list_tag = tag
            out.append(f"<li>{inner}{children_html}</li>")
            continue
        close_list()

        if btype == "paragraph":
            if inner.strip():
                out.append(f"<p>{inner}</p>")
        elif btype in ("heading_1", "heading_2", "heading_3"):
            level = {"heading_1": "h2", "heading_2": "h3", "heading_3": "h4"}[btype]
            out.append(f"<{level}>{inner}</{level}>")
        elif btype == "quote":
            out.append(f"<blockquote>{inner}{children_html}</blockquote>")
        elif btype == "callout":
            icon = data.get("icon") or {}
            emoji = html.escape(icon.get("emoji", "💡")) if icon.get("type") == "emoji" else "💡"
            out.append(f'<div class="post-callout"><span class="ico">{emoji}</span><div>{inner}{children_html}</div></div>')
        elif btype == "code":
            lang = html.escape(data.get("language", ""))
            out.append(f'<pre class="post-code" data-lang="{lang}"><code>{rich_text_to_html(rich)}</code></pre>')
        elif btype == "divider":
            out.append("<hr>")
        elif btype == "image":
            src = (data.get("external") or {}).get("url") or (data.get("file") or {}).get("url", "")
            caption = rich_text_to_html(data.get("caption", []))
            if src:
                out.append(f'<figure><img src="{html.escape(src)}" alt="" loading="lazy">'
                           + (f"<figcaption>{caption}</figcaption>" if caption else "") + "</figure>")
        elif btype == "bookmark":
            url = data.get("url", "")
            if url:
                out.append(f'<p><a href="{html.escape(url)}" target="_blank" rel="noopener">🔗 {html.escape(url)}</a></p>')
        elif btype == "to_do":
            checked = "checked" if data.get("checked") else ""
            out.append(f'<p class="post-todo"><input type="checkbox" disabled {checked}> {inner}</p>')
        elif btype == "toggle":
            out.append(f"<details><summary>{inner}</summary>{children_html}</details>")
        elif inner.strip():
            out.append(f"<p>{inner}</p>")

    close_list()
    return "".join(out)


def page_to_post(page: dict) -> dict:
    props = page.get("properties", {})

    def prop(name):
        return props.get(name, {})

    title = rich_text_to_plain(prop("제목").get("title", []))
    summary = rich_text_to_plain(prop("요약").get("rich_text", []))
    category = (prop("카테고리").get("select") or {}).get("name", "공지")
    date = (prop("발행일").get("date") or {}).get("start") or page.get("created_time", "")[:10]
    external = prop("외부링크").get("url")
    meta = CATEGORY_META.get(category, {"emoji": "📝", "color": "#0B3D91"})

    print(f"  · {date} [{category}] {title}", flush=True)
    body_html = blocks_to_html(fetch_children(page["id"]))
    return {
        "id": page["id"],
        "title": title,
        "summary": summary,
        "category": category,
        "emoji": meta["emoji"],
        "color": meta["color"],
        "date": date[:10],
        "external_url": external,
        "notion_url": page.get("url"),
        "html": body_html,
    }


def main() -> int:
    if not os.environ.get("NOTION_TOKEN"):
        print("NOTION_TOKEN 환경변수가 없습니다. GitHub Secrets 에 노션 통합 토큰을 등록하세요.", file=sys.stderr)
        return 1
    database_id = os.environ.get("NOTION_DATABASE_ID", DEFAULT_DATABASE_ID)

    pages, cursor = [], None
    while True:
        payload = {
            "filter": {"property": "상태", "select": {"equals": "발행"}},
            "sorts": [{"property": "발행일", "direction": "descending"}],
            "page_size": 100,
        }
        if cursor:
            payload["start_cursor"] = cursor
        data = api_request(f"/databases/{database_id}/query", payload)
        pages.extend(data.get("results", []))
        if not data.get("has_more"):
            break
        cursor = data.get("next_cursor")

    print(f"발행 상태 포스트 {len(pages)}건 수집", flush=True)
    posts = [page_to_post(p) for p in pages]
    posts.sort(key=lambda p: p["date"], reverse=True)

    result = {
        "generated_at": datetime.now(KST).strftime("%Y-%m-%d %H:%M KST"),
        "source": "notion",
        "count": len(posts),
        "posts": posts,
    }
    OUT_PATH.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"{OUT_PATH} 갱신 완료 ({len(posts)}건)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
