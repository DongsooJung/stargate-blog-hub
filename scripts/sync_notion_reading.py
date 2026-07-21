#!/usr/bin/env python3
"""Export approved Notion reading notes to a public JSON file."""

from __future__ import annotations

import hashlib
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

API_ROOT = "https://api.notion.com/v1"
API_VERSION = "2026-03-11"
DATA_SOURCE_ID = os.getenv(
    "NOTION_DATA_SOURCE_ID", "66846d6d-864e-42dc-99db-2b61b315f8d4"
)
OUTPUT = Path(os.getenv("OUTPUT_PATH", "reading/posts.json"))
TOKEN = os.getenv("NOTION_TOKEN", "").strip()

COLORS = [
    "linear-gradient(135deg,#24404f,#c58a52)",
    "linear-gradient(135deg,#173e49,#55a69c)",
    "linear-gradient(135deg,#38344d,#8f7dae)",
    "linear-gradient(135deg,#5b346c,#d26e91)",
    "linear-gradient(135deg,#245d45,#e3ab3f)",
]


def request(path: str, *, method: str = "GET", body: dict | None = None) -> dict:
    data = json.dumps(body, ensure_ascii=False).encode() if body is not None else None
    req = urllib.request.Request(
        f"{API_ROOT}{path}",
        data=data,
        method=method,
        headers={
            "Authorization": f"Bearer {TOKEN}",
            "Notion-Version": API_VERSION,
            "Content-Type": "application/json",
            "User-Agent": "stargate-reading-sync/1.0",
        },
    )
    for attempt in range(4):
        try:
            with urllib.request.urlopen(req, timeout=30) as response:
                return json.load(response)
        except urllib.error.HTTPError as error:
            if error.code == 429 or error.code >= 500:
                time.sleep(2**attempt)
                continue
            detail = error.read().decode("utf-8", "replace")
            raise RuntimeError(f"Notion API {error.code}: {detail}") from error
        except urllib.error.URLError as error:
            if attempt == 3:
                raise RuntimeError(f"Notion API network error: {error}") from error
            time.sleep(2**attempt)
    raise RuntimeError("Notion API request failed after retries")


def rich_text(items: list[dict]) -> str:
    return "".join(item.get("plain_text", "") for item in items)


def value(properties: dict, name: str, default=None):
    prop = properties.get(name) or {}
    kind = prop.get("type")
    data = prop.get(kind) if kind else None
    if kind in {"title", "rich_text"}:
        return rich_text(data or [])
    if kind == "select":
        return (data or {}).get("name", default)
    if kind == "multi_select":
        return [item.get("name", "") for item in (data or []) if item.get("name")]
    if kind == "date":
        return (data or {}).get("start", default)
    if kind in {"checkbox", "number", "url"}:
        return data if data is not None else default
    return default


def clean_markdown(text: str) -> str:
    text = re.sub(r"<[^>]+>", "", text)
    text = re.sub(r"!\[[^]]*]\([^)]*\)", "", text)
    text = re.sub(r"\[([^]]+)]\([^)]*\)", r"\1", text)
    text = re.sub(r"[*_`~]", "", text)
    text = re.sub(r"^\s*(?:[-*+] |\d+\. |>|#{1,6}\s*)", "", text, flags=re.M)
    return re.sub(r"\n{3,}", "\n\n", text).strip()


def section(markdown: str, heading_keyword: str) -> str:
    pattern = rf"^##[^\n]*{re.escape(heading_keyword)}[^\n]*\n(.*?)(?=^##\s|\Z)"
    match = re.search(pattern, markdown, flags=re.M | re.S)
    return clean_markdown(match.group(1)) if match else ""


def get_pages() -> list[dict]:
    pages: list[dict] = []
    cursor = None
    while True:
        body = {
            "filter": {
                "and": [
                    {"property": "웹공개", "checkbox": {"equals": True}},
                    {
                        "or": [
                            {"property": "독서상태", "select": {"equals": "완독"}},
                            {"property": "독서상태", "select": {"equals": "재독"}},
                        ]
                    },
                ]
            },
            "sorts": [{"property": "완독일", "direction": "descending"}],
            "page_size": 100,
        }
        if cursor:
            body["start_cursor"] = cursor
        result = request(f"/data_sources/{DATA_SOURCE_ID}/query", method="POST", body=body)
        pages.extend(result.get("results", []))
        if not result.get("has_more"):
            return pages
        cursor = result.get("next_cursor")


def convert(page: dict) -> dict:
    props = page.get("properties", {})
    page_id = page["id"].replace("-", "")
    markdown = request(f"/pages/{page['id']}/markdown").get("markdown", "")
    summary = section(markdown, "한 줄 요약")
    messages = section(markdown, "핵심 메시지")
    application = section(markdown, "내 일·연구에 적용")
    quote = section(markdown, "인상 깊은 구절").strip('"“” ')
    recommendations = value(props, "추천대상", []) or []
    title = value(props, "도서명", "제목 없음")
    category = value(props, "대분류", "기타")
    stars = value(props, "평점", "")
    review_parts = [part for part in (summary, messages, application) if part]
    review = "\n\n".join(review_parts) or clean_markdown(markdown)[:3000]
    color_index = int(hashlib.sha256(category.encode()).hexdigest()[:8], 16) % len(COLORS)
    return {
        "id": page_id,
        "title": title,
        "author": value(props, "저자", "") or "저자 미입력",
        "category": category,
        "rating": stars.count("⭐") or 0,
        "pages": int(value(props, "페이지수", 0) or 0),
        "date": value(props, "완독일", "") or page.get("created_time", "")[:10],
        "oneLine": value(props, "한줄평", "") or summary,
        "quote": quote or "기억할 문장 미입력",
        "review": review,
        "recommend": ", ".join(recommendations) or "추천 대상 미입력",
        "keywords": value(props, "핵심키워드", "") or "",
        "notionUrl": page.get("url", ""),
        "color": COLORS[color_index],
    }


def main() -> int:
    if not TOKEN:
        print("NOTION_TOKEN secret is required", file=sys.stderr)
        return 2
    posts = [convert(page) for page in get_pages()]
    payload = {
        "generatedAt": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "source": "Notion · 📖 독서 LOG & 독후감",
        "posts": posts,
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Exported {len(posts)} approved reading posts to {OUTPUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
