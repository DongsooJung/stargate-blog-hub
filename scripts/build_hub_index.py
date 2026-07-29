#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
blog.stargateedu.co.kr 허브 인덱스 빌더
=====================================

매일 KST 03:00 GitHub Actions 에서 실행됩니다.

동작:
    1) FEEDS 에 정의된 4개(+옵션) 채널의 RSS 를 수집
    2) 각 채널 최신 5개씩 → 전체 최신순 20개로 정렬
    3) 목록이 직전 빌드와 동일하면 아무 파일도 건드리지 않고 종료
    4) 변경이 있으면 templates/허브_템플릿.html 을 렌더링해
       index.html 과 posts.json 을 원자적으로 갱신

posts.json 은 페이지의 "🔄 새로고침" 버튼이 읽어가는 데이터 소스입니다.
버튼을 누르면 브라우저가 이 파일을 캐시 없이 다시 받아 목록을 다시 그리므로,
페이지를 새로 열지 않아도 최신 갱신 결과가 즉시 반영됩니다.

환경 변수:
    TEMPLATE_PATH  : 템플릿 경로 (기본 templates/허브_템플릿.html)
    OUTPUT_PATH    : 출력 경로   (기본 index.html)
    DATA_PATH      : 데이터 경로 (기본 posts.json)
    FEED_TIMEOUT   : RSS 타임아웃 초 (기본 15)
    MAX_PER_FEED   : 채널당 최대 수집 수 (기본 5)
    TOP_N          : 전체 상위 표시 수 (기본 20)
    FORCE_WRITE    : 1 이면 변경이 없어도 강제로 다시 씀

로컬 테스트:
    pip install -r scripts/requirements.txt
    python scripts/build_hub_index.py
"""

from __future__ import annotations

import json
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
        "url": "https://rss.blog.naver.com/stargate8224.xml",
        "icon": "📒",
        "color": "#03C75A",
    },
    "네이버 법인": {
        "url": "https://rss.blog.naver.com/stargate8225.xml",
        "icon": "🏢",
        "color": "#2DB400",
    },
    "티스토리": {
        "url": "https://dongsoo.tistory.com/rss",
        "icon": "✍️",
        "color": "#FF5900",
    },
    "YouTube 우주인": {
        "url": "https://www.youtube.com/feeds/videos.xml?channel_id=UCZi4uumj35DvcKQFKKBjsvw",
        "icon": "📺",
        "color": "#FF0000",
    },
}

MAX_PER_FEED = int(os.environ.get("MAX_PER_FEED", "5"))
TOP_N        = int(os.environ.get("TOP_N", "20"))
FEED_TIMEOUT = int(os.environ.get("FEED_TIMEOUT", "15"))

BASE_DIR      = Path(__file__).resolve().parent.parent
TEMPLATE_PATH = Path(os.environ.get("TEMPLATE_PATH", BASE_DIR / "templates" / "허브_템플릿.html"))
OUTPUT_PATH   = Path(os.environ.get("OUTPUT_PATH",   BASE_DIR / "index.html"))
DATA_PATH     = Path(os.environ.get("DATA_PATH",     BASE_DIR / "posts.json"))
FORCE_WRITE   = os.environ.get("FORCE_WRITE", "") == "1"

# posts.json 에 담는 필드 (sort_key 는 내부 정렬용이라 제외)
PUBLIC_FIELDS = ("channel", "icon", "color", "title", "link", "date")


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

def render(posts: list[dict], updated: str) -> str:
    env = Environment(
        loader=FileSystemLoader(str(TEMPLATE_PATH.parent)),
        autoescape=select_autoescape(["html"]),
    )
    template = env.get_template(TEMPLATE_PATH.name)
    return template.render(
        posts=posts,
        post_count=len(posts),
        updated=updated,
    )


def public_posts(posts: list[dict]) -> list[dict]:
    """posts.json 에 실을 형태로 정리."""
    return [{k: p[k] for k in PUBLIC_FIELDS} for p in posts]


def load_previous() -> list[dict]:
    """직전 빌드의 posts.json 목록. 없거나 깨졌으면 빈 목록."""
    if not DATA_PATH.exists():
        return []
    try:
        return json.loads(DATA_PATH.read_text(encoding="utf-8")).get("posts", [])
    except (json.JSONDecodeError, OSError) as exc:
        log("WARN", f"기존 {DATA_PATH.name} 읽기 실패 — 새로 씁니다: {exc}")
        return []


def write_atomic(path: Path, text: str) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    tmp.replace(path)


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
    current = public_posts(top_posts)

    # 목록이 그대로면 파일을 건드리지 않는다.
    # → 갱신 시각이 "마지막으로 글 목록이 실제로 바뀐 시각"을 가리키고,
    #    Actions 도 매 실행마다 빈 커밋을 만들지 않는다.
    if not FORCE_WRITE and OUTPUT_PATH.exists() and current == load_previous():
        log("NOTICE", f"변경 없음 — 기존 목록 유지 (포스팅 {len(current)}개)")
        return 0

    updated = datetime.now(KST).strftime("%Y-%m-%d %H:%M KST")
    write_atomic(OUTPUT_PATH, render(top_posts, updated))
    write_atomic(DATA_PATH, json.dumps(
        {"updated": updated, "post_count": len(current), "posts": current},
        ensure_ascii=False, indent=2,
    ) + "\n")

    log("NOTICE",
        f"완료 — {OUTPUT_PATH.name} · {OUTPUT_PATH.stat().st_size/1024:.1f} KB · "
        f"{DATA_PATH.name} 동시 갱신 · 포스팅 {len(top_posts)}/{len(all_posts)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
