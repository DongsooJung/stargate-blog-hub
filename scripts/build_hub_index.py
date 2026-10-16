#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""blog.stargateedu.co.kr 허브 인덱스 빌더.

채널 카드와 RSS 수집 대상은 config/channels.json 한곳에서 읽습니다.
수집에 실패하면 해당 채널의 직전 정상 결과를 유지하고, 모든 채널이
실패하면 기존 글 목록을 보존한 뒤 상태만 기록합니다.
"""

from __future__ import annotations

import html
import json
import os
import re
import socket
import sys
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

import feedparser  # type: ignore
from jinja2 import Environment, FileSystemLoader, select_autoescape  # type: ignore


KST = timezone(timedelta(hours=9))
TOPICS = ["부동산·경제", "수학·AI", "도시·연구", "사회·데이터", "독서·기록"]
TRACKING_KEYS = {
    "fromrss",
    "trackingcode",
    "fbclid",
    "gclid",
    "igshid",
    "si",
    "ref",
    "source",
}
LEGACY_LABELS = {
    "부동산·경제": "naver-estate",
    "수학·AI": "naver-math",
    "정치·데이터": "tistory",
    "YouTube 우주인": "youtube",
}
HEADING_HASH = re.compile(r"^#{1,6}\s+")
TAG_RE = re.compile(r"<[^>]+>")
IMG_RE = re.compile(r"""<img[^>]+src=["']([^"']+)["']""", re.I)
HEX_COLOR = re.compile(r"^#[0-9A-Fa-f]{6}$")
LEGACY_ARTICLE = re.compile(
    r'<article class="latest-item">.*?'
    r'<span class="channel-tag"[^>]*>(.*?)</span>.*?'
    r'<a href="(.*?)".*?>(.*?)</a>.*?'
    r'<time datetime="(.*?)">',
    re.S,
)

MAX_PER_FEED = int(os.environ.get("MAX_PER_FEED", "8"))
TOP_N = int(os.environ.get("TOP_N", "60"))
FEED_TIMEOUT = int(os.environ.get("FEED_TIMEOUT", "15"))

BASE_DIR = Path(__file__).resolve().parent.parent
CONFIG_PATH = Path(os.environ.get("CONFIG_PATH", BASE_DIR / "config" / "channels.json"))
TEMPLATE_PATH = Path(os.environ.get("TEMPLATE_PATH", BASE_DIR / "templates" / "허브_템플릿.html"))
OUTPUT_PATH = Path(os.environ.get("OUTPUT_PATH", BASE_DIR / "index.html"))
DATA_DIR = Path(os.environ.get("DATA_DIR", BASE_DIR / "data"))
CACHE_DIR = DATA_DIR / "feeds"
STATUS_PATH = DATA_DIR / "collection-status.json"
SNAPSHOT_PATH = DATA_DIR / "posts-snapshot.json"


def log(level: str, msg: str) -> None:
    prefixes = {"INFO": "", "WARN": "::warning::", "ERROR": "::error::", "NOTICE": "::notice::"}
    print(f"{prefixes.get(level, '')}[{level}] {msg}", file=sys.stderr, flush=True)


@dataclass(frozen=True)
class Channel:
    id: str
    name: str
    description: str
    url: str
    platform: str
    topic: str
    icon: str
    color: str
    rss: str
    order: int
    link_label: str
    external: bool

    @property
    def has_rss(self) -> bool:
        return bool(self.rss.strip())


def load_config(path: Path) -> tuple[list[Channel], list[str]]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    channels: list[Channel] = []
    for item in raw.get("channels", []):
        color = str(item.get("color") or "").strip()
        if not HEX_COLOR.match(color):
            color = "#0B3D91"
        channels.append(
            Channel(
                id=str(item["id"]).strip(),
                name=str(item.get("name") or "").strip(),
                description=str(item.get("description") or "").strip(),
                url=str(item.get("url") or "").strip(),
                platform=str(item.get("platform") or "").strip(),
                topic=str(item.get("topic") or "").strip(),
                icon=str(item.get("icon") or "").strip(),
                color=color,
                rss=str(item.get("rss") or "").strip(),
                order=int(item.get("order") or 0),
                link_label=str(item.get("link_label") or "바로가기").strip(),
                external=bool(item.get("external", True)),
            )
        )
    channels.sort(key=lambda ch: (ch.order, ch.name))
    featured = [str(url).strip() for url in raw.get("featured_urls", []) if str(url).strip()]
    return channels, featured


def clean_text(value: str) -> str:
    text = value or ""
    for _ in range(3):
        decoded = html.unescape(text)
        if decoded == text:
            break
        text = decoded
    text = text.replace("\xa0", " ").replace("\u200b", "")
    text = TAG_RE.sub(" ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def clean_title(value: str) -> str:
    text = clean_text(value)
    text = HEADING_HASH.sub("", text).strip()
    return text or "제목 없음"


def clean_summary(value: str, title: str = "") -> str:
    text = clean_text(value)
    text = re.sub(r"\*\*(.*?)\*\*", r"\1", text)
    text = re.sub(r"(?:^|\s)#{1,6}\s+", " ", text)
    text = re.sub(r"\s+", " ", text).strip(" -|")
    while title and text.startswith(title):
        text = text[len(title):].strip(" -|")
    if not text or text == title:
        return ""
    if len(text) > 180:
        text = text[:179].rstrip() + "…"
    return text


def canonical_url(url: str) -> str:
    raw = html.unescape((url or "").strip())
    if not raw or raw == "#":
        return raw
    parts = urlsplit(raw)
    if not parts.netloc and not parts.scheme:
        return raw
    query = [
        (key, val)
        for key, val in parse_qsl(parts.query, keep_blank_values=True)
        if key.lower() not in TRACKING_KEYS and not key.lower().startswith("utm_")
    ]
    path = parts.path or "/"
    if path != "/":
        path = path.rstrip("/")
    return urlunsplit((
        (parts.scheme or "https").lower(),
        parts.netloc.lower(),
        path,
        urlencode(query),
        "",
    ))


def kst_from_struct(st) -> datetime | None:
    try:
        return datetime(*st[:6], tzinfo=timezone.utc).astimezone(KST)
    except (TypeError, ValueError):
        return None


def parse_entry_datetime(entry: dict) -> datetime | None:
    for key in ("published_parsed", "updated_parsed"):
        parsed = kst_from_struct(entry.get(key))
        if parsed:
            return parsed
    for key in ("published", "updated", "created"):
        raw = str(entry.get(key) or "").strip()
        if not raw:
            continue
        try:
            dt = parsedate_to_datetime(raw)
        except (TypeError, ValueError, IndexError):
            dt = None
        if dt is None:
            try:
                dt = datetime.fromisoformat(raw.replace("Z", "+00:00"))
            except ValueError:
                dt = None
        if dt is None:
            continue
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=KST)
        return dt.astimezone(KST)
    return None


def extract_image(entry: dict) -> str:
    for key in ("media_thumbnail", "media_content"):
        media = entry.get(key) or []
        if isinstance(media, list):
            for item in media:
                url = str((item or {}).get("url") or "")
                if url.startswith("https://"):
                    return url
    for enclosure in entry.get("enclosures") or []:
        url = str((enclosure or {}).get("href") or (enclosure or {}).get("url") or "")
        mime = str((enclosure or {}).get("type") or "")
        if url.startswith("https://") and (not mime or mime.startswith("image/")):
            return url
    summary = str(entry.get("summary") or entry.get("description") or "")
    match = IMG_RE.search(summary)
    if match and match.group(1).startswith("https://"):
        return match.group(1)
    return ""


def make_post(channel: Channel, *, title: str, link: str, when: datetime | None,
              summary: str = "", image: str = "", from_cache: bool = False) -> dict:
    if when is None:
        when = datetime(1970, 1, 1, tzinfo=KST)
        date = ""
        precise = False
    else:
        date = when.strftime("%Y-%m-%d")
        precise = True
    clean = clean_title(title)
    return {
        "channel_id": channel.id,
        "channel_name": channel.name,
        "platform": channel.platform,
        "topic": channel.topic,
        "icon": channel.icon,
        "color": channel.color,
        "title": clean,
        "summary": clean_summary(summary, clean),
        "link": html.unescape(link).strip() or "#",
        "canonical": canonical_url(link),
        "image": image if image.startswith("https://") else "",
        "date": date,
        "datetime": when.isoformat(timespec="seconds"),
        "sort_key": when.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "precise_time": precise,
        "from_cache": from_cache,
    }


def post_from_entry(channel: Channel, entry: dict) -> dict:
    when = parse_entry_datetime(entry)
    summary = str(entry.get("summary") or entry.get("description") or "")
    return make_post(
        channel,
        title=str(entry.get("title") or ""),
        link=str(entry.get("link") or "#"),
        when=when,
        summary=summary,
        image=extract_image(entry),
    )


def fetch_feed(channel: Channel) -> tuple[list[dict], str | None]:
    if not channel.has_rss:
        return [], None
    socket.setdefaulttimeout(FEED_TIMEOUT)
    try:
        parsed = feedparser.parse(
            channel.rss,
            request_headers={"User-Agent": "StargateBlogHub/1.0 (+https://blog.stargateedu.co.kr/)"},
        )
    except Exception as exc:  # noqa: BLE001 - 수집 실패는 캐시로 복구한다.
        return [], f"파싱 예외: {exc}"

    status = getattr(parsed, "status", None)
    if status and int(status) >= 400:
        return [], f"HTTP {status}"
    if not parsed.entries:
        detail = getattr(parsed, "bozo_exception", None)
        return [], f"항목 없음{f' ({detail})' if detail else ''}"

    posts = [post_from_entry(channel, entry) for entry in parsed.entries[:MAX_PER_FEED]]
    return posts, None


def cache_path(channel_id: str) -> Path:
    safe = re.sub(r"[^a-z0-9._-]", "-", channel_id)
    return CACHE_DIR / f"{safe}.json"


def read_json(path: Path) -> dict | None:
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        log("WARN", f"{path.name} 읽기 실패: {exc}")
        return None
    return data if isinstance(data, dict) else None


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)


def load_channel_cache(channel_id: str) -> dict | None:
    data = read_json(cache_path(channel_id))
    if not data or not isinstance(data.get("posts"), list):
        return None
    return data


def save_channel_cache(channel: Channel, posts: list[dict], when: datetime) -> None:
    write_json(cache_path(channel.id), {
        "channel_id": channel.id,
        "last_success_at": when.isoformat(timespec="seconds"),
        "posts": posts,
    })


def mark_cached(posts: list[dict]) -> list[dict]:
    copied = []
    for post in posts:
        item = dict(post)
        item["from_cache"] = True
        copied.append(item)
    return copied


def dedupe_posts(posts: list[dict]) -> list[dict]:
    chosen: dict[str, dict] = {}
    order: list[str] = []
    for post in posts:
        key = post.get("canonical") or post.get("link") or post.get("title")
        previous = chosen.get(key)
        if previous is None:
            chosen[key] = post
            order.append(key)
            continue
        if str(post.get("sort_key") or "") > str(previous.get("sort_key") or ""):
            chosen[key] = post
    return [chosen[key] for key in order]


def sort_posts(posts: list[dict]) -> list[dict]:
    return sorted(posts, key=lambda post: (str(post.get("sort_key") or ""), str(post.get("title") or "")), reverse=True)


def apply_featured(posts: list[dict], featured_urls: list[str]) -> tuple[list[dict], list[dict]]:
    wanted = [canonical_url(url) for url in featured_urls]
    featured: list[dict] = []
    used: set[str] = set()
    by_canon = {post.get("canonical"): post for post in posts}
    for canon in wanted:
        post = by_canon.get(canon)
        if post and canon not in used and len(featured) < 2:
            item = dict(post)
            item["featured"] = True
            featured.append(item)
            used.add(canon)
    regular = []
    for post in posts:
        if post.get("canonical") in used:
            continue
        item = dict(post)
        item["featured"] = False
        regular.append(item)
    return featured, regular


def legacy_posts(index_html: str, channels: list[Channel]) -> dict[str, list[dict]]:
    by_id = {channel.id: channel for channel in channels}
    grouped: dict[str, list[dict]] = {}
    for label_html, href, title, date in LEGACY_ARTICLE.findall(index_html):
        label = clean_text(label_html)
        label = re.sub(r"^[^\w가-힣]+", "", label).strip()
        channel_id = LEGACY_LABELS.get(label)
        channel = by_id.get(channel_id or "")
        if not channel:
            continue
        when = None
        if re.fullmatch(r"\d{4}-\d{2}-\d{2}", date):
            when = datetime.fromisoformat(date).replace(tzinfo=KST)
        grouped.setdefault(channel.id, []).append(
            make_post(channel, title=html.unescape(title), link=html.unescape(href), when=when)
        )
    return grouped


def assemble(channels: list[Channel], fetcher, caches: dict[str, dict | None],
             legacy: dict[str, list[dict]], now: datetime) -> tuple[list[dict], dict, dict[str, list[dict]]]:
    """채널별 수집 결과를 합친다. fetcher(channel) -> (posts, error)."""
    posts: list[dict] = []
    channel_status: list[dict] = []
    fresh_by_channel: dict[str, list[dict]] = {}
    fresh_success = False

    for channel in channels:
        if not channel.has_rss:
            channel_status.append({
                "id": channel.id,
                "name": channel.name,
                "ok": None,
                "used_cache": False,
                "count": 0,
                "error": None,
                "last_success_at": None,
                "rss": False,
            })
            continue

        fetched, error = fetcher(channel)
        previous = caches.get(channel.id)
        previous_posts = previous.get("posts", []) if previous else []
        previous_at = previous.get("last_success_at") if previous else None

        if error or not fetched:
            reason = error or "항목 없음"
            fallback = previous_posts or legacy.get(channel.id) or []
            if fallback:
                posts.extend(mark_cached(fallback))
                log("WARN", f"{channel.name} 수집 실패, 직전 결과 {len(fallback)}개 유지: {reason}")
            else:
                log("WARN", f"{channel.name} 수집 실패, 유지할 이전 결과 없음: {reason}")
            channel_status.append({
                "id": channel.id,
                "name": channel.name,
                "ok": False,
                "used_cache": bool(fallback),
                "count": len(fallback),
                "error": reason,
                "last_success_at": previous_at,
                "rss": True,
            })
            continue

        fresh_success = True
        stamped = []
        for post in fetched:
            item = dict(post)
            item["from_cache"] = False
            stamped.append(item)
        fresh_by_channel[channel.id] = stamped
        posts.extend(stamped)
        success_at = now.isoformat(timespec="seconds")
        channel_status.append({
            "id": channel.id,
            "name": channel.name,
            "ok": True,
            "used_cache": False,
            "count": len(stamped),
            "error": None,
            "last_success_at": success_at,
            "rss": True,
        })
        log("INFO", f"{channel.name}: {len(stamped)}개 수집")

    rss_rows = [row for row in channel_status if row["rss"]]
    all_failed = bool(rss_rows) and all(row["ok"] is False for row in rss_rows)
    success_times = [row["last_success_at"] for row in rss_rows if row.get("last_success_at")]
    last_success = max(success_times) if success_times else None
    if fresh_success:
        last_success = now.isoformat(timespec="seconds")

    kept_cache = any(row["ok"] is False and row["used_cache"] for row in rss_rows)
    missed = any(row["ok"] is False and not row["used_cache"] for row in rss_rows)
    status = {
        "attempted_at": now.isoformat(timespec="seconds"),
        "last_success_at": last_success,
        "interval": "1h",
        "all_failed": all_failed,
        "partial": (kept_cache or missed) and not all_failed,
        "kept_cache": kept_cache and not all_failed,
        "missed": missed and not all_failed,
        "channels": channel_status,
    }
    deduped = sort_posts(dedupe_posts(posts))[:TOP_N]
    return deduped, status, fresh_by_channel


def format_kst(value: str | None) -> str:
    if not value:
        return "기록 없음"
    try:
        dt = datetime.fromisoformat(value)
    except ValueError:
        return value
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=KST)
    return dt.astimezone(KST).strftime("%Y-%m-%d %H:%M KST")


def status_message(status: dict) -> str:
    when = format_kst(status.get("last_success_at"))
    if status.get("all_failed"):
        return f"이번 수집에 실패해 기존 글 목록을 유지하고 있습니다. 마지막 수집 시각 · {when}"
    if status.get("kept_cache"):
        return f"마지막 수집 시각 · {when}. 일부 채널은 직전 수집 결과를 유지하고 있습니다."
    if status.get("missed"):
        return f"마지막 수집 시각 · {when}. 일부 채널을 가져오지 못했습니다."
    return f"마지막 수집 시각 · {when}"


def platforms_for(channels: list[Channel]) -> list[str]:
    found: list[str] = []
    for channel in channels:
        if channel.has_rss and channel.platform and channel.platform not in found:
            found.append(channel.platform)
    return found


def render(template_path: Path, **context) -> str:
    env = Environment(
        loader=FileSystemLoader(str(template_path.parent)),
        autoescape=select_autoescape(["html"]),
        trim_blocks=True,
        lstrip_blocks=True,
    )
    return env.get_template(template_path.name).render(**context)


def load_snapshot_posts() -> list[dict]:
    data = read_json(SNAPSHOT_PATH)
    posts = data.get("posts") if data else None
    return posts if isinstance(posts, list) else []


def build(config_path: Path = CONFIG_PATH, output_path: Path = OUTPUT_PATH,
          template_path: Path = TEMPLATE_PATH, now: datetime | None = None,
          fetcher=None) -> dict:
    if not template_path.exists():
        raise FileNotFoundError(template_path)
    if not config_path.exists():
        raise FileNotFoundError(config_path)

    now = now or datetime.now(KST)
    channels, featured_urls = load_config(config_path)
    caches = {channel.id: load_channel_cache(channel.id) for channel in channels}
    legacy = {}
    if output_path.exists() and any(channel.has_rss and not caches.get(channel.id) for channel in channels):
        legacy = legacy_posts(output_path.read_text(encoding="utf-8"), channels)

    posts, status, fresh_by_channel = assemble(
        channels,
        fetcher or fetch_feed,
        caches,
        legacy,
        now,
    )
    if not posts and status["all_failed"]:
        posts = sort_posts(load_snapshot_posts())
        if posts:
            log("WARN", f"모든 채널 수집 실패. 기존 스냅샷 {len(posts)}개를 보존합니다.")

    featured, regular = apply_featured(posts, featured_urls)
    for channel in channels:
        fresh = fresh_by_channel.get(channel.id)
        if fresh is not None:
            save_channel_cache(channel, fresh, now)

    snapshot_posts = featured + regular
    write_json(SNAPSHOT_PATH, {"posts": snapshot_posts, "saved_at": now.isoformat(timespec="seconds")})
    write_json(STATUS_PATH, status)

    html_out = render(
        template_path,
        channels=channels,
        featured=featured,
        posts=regular,
        post_count=len(snapshot_posts),
        updated=format_kst(status.get("last_success_at")),
        status_message=status_message(status),
        all_failed=status["all_failed"],
        partial=status["partial"],
        platforms=platforms_for(channels),
        topics=TOPICS,
        generated_at=now.isoformat(timespec="seconds"),
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    tmp = output_path.with_suffix(output_path.suffix + ".tmp")
    tmp.write_text(html_out, encoding="utf-8")
    tmp.replace(output_path)
    log("NOTICE", f"완료 — {output_path.name} · 글 {len(snapshot_posts)}개 · 대표 {len(featured)}개")
    return status


def main() -> int:
    try:
        build()
    except FileNotFoundError as exc:
        log("ERROR", f"필요한 파일 없음: {exc}")
        return 2
    except Exception as exc:  # noqa: BLE001
        log("ERROR", f"빌드 실패: {exc}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
