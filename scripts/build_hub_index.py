#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
blog.stargateedu.co.kr 허브 인덱스 빌더
=====================================

매일 KST 03:00 GitHub Actions 에서 실행됩니다.

동작:
    1) FEEDS 에 정의된 4개(+옵션) 채널의 RSS 를 수집
    2) 각 채널 최신 5개씩 → 전체 최신순 20개로 정렬
    3) templates/허브_템플릿.html 을 렌더링
    4) 리포 루트의 index.html 을 원자적으로 갱신

환경 변수:
    TEMPLATE_PATH  : 템플릿 경로 (기본 templates/허브_템플릿.html)
    OUTPUT_PATH    : 출력 경로   (기본 index.html)
    FEED_TIMEOUT   : RSS 타임아웃 초 (기본 15)
    MAX_PER_FEED   : 채널당 최대 수집 수 (기본 5)
    TOP_N          : 전체 상위 표시 수 (기본 20)

로컬 테스트:
    pip install -r scripts/requirements.txt
    python scripts/build_hub_index.py
"""

from __future__ import annotations

import os
import sys
import socket
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path

import feedparser  # type: ignore
from jinja2 import Environment, FileSystemLoader, select_autoescape  # type: ignore


# ───────────────────────────────────────────────────────────────────
# 설정
# ───────────────────────────────────────────────────────────────────

KST = timezone(timedelta(hours=9))

FEEDS: dict[str, dict[str, str]] = {
    "네이버 개인": {
        "url": "https://rss.blog.naver.com/jds0688.xml",
        "icon": "📒",
        "color": "#03C75A",
    },
    "네이버 법인": {
        "url": "https://rss.blog.naver.com/rvcompany77.xml",
        "icon": "🏢",
        "color": "#2DB400",
    },
    "티스토리": {
        "url": "https://dongsoo.tistory.com/rss",
        "icon": "✍️",
        "color": "#FF5900",
    },
    "Medium": {
        "url": "https://medium.com/feed/@stargate-en",
        "icon": "🌐",
        "color": "#000000",
    },
}

MAX_PER_FEED = int(os.environ.get("MAX_PER_FEED", "5"))
TOP_N        = int(os.environ.get("TOP_N", "20"))
FEED_TIMEOUT = int(os.environ.get("FEED_TIMEOUT", "15"))

BASE_DIR      = Path(__file__).resolve().parent.parent
TEMPLATE_PATH = Path(os.environ.get("TEMPLATE_PATH", BASE_DIR / "templates" / "허브_템플릿.html"))
OUTPUT_PATH   = Path(os.environ.get("OUTPUT_PATH",   BASE_DIR / "index.html"))


# ───────────────────────────────────────────────────────────────────
# 로깅 (GitHub Actions group 형식)
# ───────────────────────────────────────────────────────────────────

def log(level: str, msg: str) -> None:
    prefixes = {"INFO": "", "WARN": "::warning::", "ERROR": "::error::", "NOTICE": "::notice::"}
    print(f"{prefixes.get(level, '')}[{level}] {msg}", file=sys.stderr, flush=True)


# ───────────────────────────────────────────────────────────────────
# RSS 수집
# ───────────────────────────────────────────────────────────────────

def parse_pubdate(entry: dict) -> str:
    """published · updated 필드에서 ISO 날짜 문자열 추출."""
    # feedparser 가 제공하는 struct_time 우선
    for key in ("published_parsed", "updated_parsed"):
        st = entry.get(key)
        if st:
            try:
                return time.strftime("%Y-%m-%d", st)
            except Exception:
                pass
    # 원본 문자열 fallback
    for key in ("published", "updated", "created"):
        val = entry.get(key, "")
        if val:
            return str(val)[:10]
    return ""


def fetch_feed(channel: str, meta: dict) -> list[dict]:
    """단일 RSS 파싱."""
    socket.setdefaulttimeout(FEED_TIMEOUT)
    try:
        parsed = feedparser.parse(meta["url"])
    except Exception as exc:
        log("WARN", f"{channel} RSS 파싱 예외: {exc}")
        return []

    if parsed.bozo and not parsed.entries:
        log("WARN", f"{channel} RSS 응답 비어있음 (bozo={parsed.bozo_exception!r})")
        return []

    posts = []
    for entry in parsed.entries[:MAX_PER_FEED]:
        title = (entry.get("title") or "제목 없음").strip()
        link  = entry.get("link") or "#"
        date  = parse_pubdate(entry)
        posts.append({
            "channel": channel,
            "icon":    meta["icon"],
            "color":   meta["color"],
            "title":   title,
            "link":    link,
            "date":    date or "-",
            "sort_key": date or "0000-00-00",
        })
    log("INFO", f"{channel}: {len(posts)}개 수집")
    return posts


# ───────────────────────────────────────────────────────────────────
# 렌더링
# ───────────────────────────────────────────────────────────────────

def render(posts: list[dict]) -> str:
    env = Environment(
        loader=FileSystemLoader(str(TEMPLATE_PATH.parent)),
        autoescape=select_autoescape(["html"]),
    )
    template = env.get_template(TEMPLATE_PATH.name)
    return template.render(
        posts=posts,
        post_count=len(posts),
        updated=datetime.now(KST).strftime("%Y-%m-%d %H:%M KST"),
    )


# ───────────────────────────────────────────────────────────────────
# 메인
# ───────────────────────────────────────────────────────────────────

def main() -> int:
    if not TEMPLATE_PATH.exists():
        log("ERROR", f"템플릿 파일 없음: {TEMPLATE_PATH}")
        return 2

    all_posts: list[dict] = []
    for ch, meta in FEEDS.items():
        all_posts.extend(fetch_feed(ch, meta))

    all_posts.sort(key=lambda x: x["sort_key"], reverse=True)
    top_posts = all_posts[:TOP_N]

    html = render(top_posts)

    # 원자적 쓰기
    tmp = OUTPUT_PATH.with_suffix(OUTPUT_PATH.suffix + ".tmp")
    tmp.write_text(html, encoding="utf-8")
    tmp.replace(OUTPUT_PATH)

    log("NOTICE",
        f"완료 — {OUTPUT_PATH.name} · {OUTPUT_PATH.stat().st_size/1024:.1f} KB · "
        f"포스팅 {len(top_posts)}/{len(all_posts)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
