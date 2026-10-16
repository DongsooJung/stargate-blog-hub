#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
blog.stargateedu.co.kr 허브 인덱스 빌더
=====================================

매일 KST 03:00 GitHub Actions 에서 실행됩니다.

동작:
    1) FEEDS 에 정의된 5개 채널의 RSS 를 수집
    2) 제목·주소를 정리하고 중복 제거 → 발행 시각순 20개로 정렬
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
import calendar
import html
import re
from datetime import datetime, timezone, timedelta
from email.utils import parsedate_to_datetime
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

import feedparser  # type: ignore
from jinja2 import Environment, FileSystemLoader, select_autoescape  # type: ignore


# ───────────────────────────────────────────────────────────────────
# 설정
# ───────────────────────────────────────────────────────────────────

KST = timezone(timedelta(hours=9))

FEEDS: dict[str, dict[str, str]] = {
    "부동산·경제": {
        "url": "https://rss.blog.naver.com/stargate8224.xml",
        "icon": "📒",
        "color": "#03C75A",
    },
    "수학·AI": {
        "url": "https://rss.blog.naver.com/stargate8225.xml",
        "icon": "🏢",
        "color": "#2DB400",
    },
    "정치·데이터": {
        "url": "https://dongsoo.tistory.com/rss",
        "icon": "✍️",
        "color": "#FF5900",
    },
    "Google Blog": {
        "url": "https://jds0688.blogspot.com/feeds/posts/default?alt=rss",
        "icon": "📝",
        "color": "#b84b00",
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


# ───────────────────────────────────────────────────────────────────
# 로깅 (GitHub Actions group 형식)
# ───────────────────────────────────────────────────────────────────

def log(level: str, msg: str) -> None:
    prefixes = {"INFO": "", "WARN": "::warning::", "ERROR": "::error::", "NOTICE": "::notice::"}
    print(f"{prefixes.get(level, '')}[{level}] {msg}", file=sys.stderr, flush=True)


# ───────────────────────────────────────────────────────────────────
# RSS 수집
# ───────────────────────────────────────────────────────────────────

def clean_title(value: str) -> str:
    """Decode feed entities before the template escapes HTML once."""
    title = str(value or "제목 없음")
    for _ in range(5):
        decoded = re.sub(r"&(?:#[0-9]+|#x[0-9a-fA-F]+|[A-Za-z][A-Za-z0-9]+);", lambda match: html.unescape(match.group()), title)
        if decoded == title:
            break
        title = decoded
    title = re.sub(r"\s+", " ", title).strip()
    return re.sub(r"^#{1,6}\s+", "", title).strip() or "제목 없음"


def clean_url(value: str) -> str:
    """Remove tracking only; retain parameters that identify the article."""
    try:
        url = urlsplit(str(value or "").strip().replace("&amp;", "&"))
        if url.scheme not in ("http", "https") or not url.hostname or url.username or url.password:
            return ""
        host = url.hostname.lower()
        scheme = url.scheme
        if host == "m.blog.naver.com":
            host = "blog.naver.com"
        if host == "blog.naver.com" or host.endswith((".tistory.com", ".blogspot.com")):
            scheme = "https"
        port = url.port
        if (url.scheme, port) in (("http", 80), ("https", 443)):
            port = None
        netloc = host if not port else f"{host}:{port}"
        query = [(key, val) for key, val in parse_qsl(url.query, keep_blank_values=True)
                 if not key.lower().startswith("utm_")
                 and key.lower() not in {"fromrss", "trackingcode", "fbclid", "gclid", "_ga", "_gl"}
                 and not (host.endswith(".blogspot.com") and key == "m" and val in ("0", "1"))]
        path = url.path or "/"
        if host == "blog.naver.com" and path.lower() == "/postview.naver":
            params = dict(query)
            if re.fullmatch(r"[A-Za-z0-9_-]+", params.get("blogId", "")) and params.get("logNo", "").isdigit():
                path = f"/{params['blogId']}/{params['logNo']}"
                query = []
        return urlunsplit((scheme, netloc, path, urlencode(sorted(query)), ""))
    except (TypeError, ValueError):
        return ""


def article_key(link: str) -> str:
    """Recognize YouTube's watch, short and sharing URLs as one video."""
    url = urlsplit(link)
    video = ""
    if url.hostname == "youtu.be":
        video = url.path.strip("/")
    elif url.hostname in ("www.youtube.com", "youtube.com", "m.youtube.com"):
        video = dict(parse_qsl(url.query)).get("v", "") if url.path == "/watch" else ""
        if url.path.startswith("/shorts/"):
            video = url.path.split("/")[2]
    if re.fullmatch(r"[A-Za-z0-9_-]{11}", video):
        return "youtube:" + video
    return link


def parse_timestamp(entry: dict) -> datetime | None:
    """feedparser struct_times are UTC; display all feeds in Asia/Seoul."""
    for key in ("published", "updated", "created"):
        st = entry.get(key + "_parsed")
        if st:
            try:
                return datetime.fromtimestamp(calendar.timegm(st), timezone.utc).astimezone(KST)
            except (TypeError, ValueError, OverflowError):
                pass
        raw = entry.get(key)
        if not raw:
            continue
        try:
            value = parsedate_to_datetime(str(raw))
        except (TypeError, ValueError, OverflowError):
            try:
                value = datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
            except (TypeError, ValueError):
                continue
        if value.tzinfo is None:
            value = value.replace(tzinfo=KST)
        return value.astimezone(KST)
    return None


def parse_pubdate(entry: dict) -> str:
    stamp = parse_timestamp(entry)
    return stamp.strftime("%Y-%m-%d") if stamp else ""


def select_posts(posts: list[dict], limit: int = TOP_N) -> list[dict]:
    selected, seen = [], set()
    for post in sorted(posts, key=lambda post: post["sort_key"], reverse=True):
        key = article_key(post["link"])
        if key in seen:
            continue
        seen.add(key)
        selected.append(post)
        if len(selected) >= limit:
            break
    return selected


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

    posts, seen = [], set()
    entries = sorted(parsed.entries, key=lambda entry: (parse_timestamp(entry) or datetime.min.replace(tzinfo=KST)).isoformat(), reverse=True)
    for entry in entries:
        title = clean_title(entry.get("title"))
        link = clean_url(entry.get("link"))
        if not link or article_key(link) in seen:
            continue
        seen.add(article_key(link))
        stamp = parse_timestamp(entry)
        posts.append({
            "channel": channel,
            "icon":    meta["icon"],
            "color":   meta["color"],
            "title":   title,
            "link":    link,
            "date": stamp.strftime("%Y-%m-%d") if stamp else "",
            "published_at": stamp.isoformat() if stamp else "",
            "display_date": stamp.strftime("%Y.%m.%d") if stamp else "날짜 확인 중",
            "display_time": stamp.strftime("%H:%M") if stamp else "",
            "sort_key": stamp.timestamp() if stamp else 0,
        })
        if len(posts) >= MAX_PER_FEED:
            break
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

    if not all_posts:
        log("ERROR", "수집된 글 없음 — 기존 index.html을 보존합니다.")
        return 1
    top_posts = select_posts(all_posts)

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
