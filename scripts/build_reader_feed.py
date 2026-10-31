#!/usr/bin/env python3
"""blog.stargateedu.co.kr 공개 페이지와 RSS로 읽기 앱용 feed.json을 만든다.

새 서버는 두지 않는다. 허브 빌더가 같은 파일을 같이 쓰면 앱은 그 주소를 먼저 읽는다.
"""

from __future__ import annotations

import json
import re
import urllib.request
from datetime import datetime, timedelta, timezone
from html.parser import HTMLParser
from pathlib import Path
from xml.etree import ElementTree

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "app" / "feed.json"
KST = timezone(timedelta(hours=9))
HUB = "https://blog.stargateedu.co.kr/"
UA = "stargate-blog-reader/1.0"
ALLOW_TAGS = {"p", "br", "h2", "h3", "h4", "ul", "ol", "li", "blockquote", "strong", "em", "a", "pre", "code"}

TOPICS = [
    {"id": "realestate", "name": "부동산·경제", "blurb": "아파트 시황, 금리, 거시경제"},
    {"id": "math-ai", "name": "수학·AI", "blurb": "KOI, 서술형 AI, 학습·연구"},
    {"id": "politics", "name": "정치·데이터", "blurb": "정치 이슈, 지표, 사회 통계"},
    {"id": "city", "name": "도시·연구", "blurb": "스마트도시, 공간계량, 인구"},
    {"id": "books", "name": "출판·서평", "blurb": "책 추천, 독후감, 출판 기록"},
]

CHANNELS = [
    {
        "id": "naver-market",
        "name": "스타게이트",
        "platform": "Naver",
        "topic": "부동산·경제",
        "blurb": "아파트 시황과 금리, 정책이 만드는 시장의 흐름.",
        "url": "https://blog.naver.com/stargate8224",
        "read": "external",
    },
    {
        "id": "naver-lab",
        "name": "스타게이트연구소",
        "platform": "Naver",
        "topic": "수학·AI",
        "blurb": "수학·정보올림피아드와 AI 연구·강의 기록.",
        "url": "https://blog.naver.com/stargate8225",
        "read": "external",
    },
    {
        "id": "blogger",
        "name": "STARGATE · Google Blog",
        "platform": "Blogger",
        "topic": "수학·AI",
        "blurb": "AI 활용과 교육, 일상에서 이어지는 생각의 기록.",
        "url": "https://jds0688.blogspot.com/",
        "read": "in-app",
    },
    {
        "id": "tistory",
        "name": "별로 향하는 문",
        "platform": "Tistory",
        "topic": "정치·데이터",
        "blurb": "정치와 사회를 지표와 데이터로 읽는 글.",
        "url": "https://dongsoo.tistory.com/",
        "read": "in-app",
    },
    {
        "id": "math",
        "name": "STARGATE MATH",
        "platform": "STARGATE",
        "topic": "수학·AI",
        "blurb": "수학 글을 아카이브에서 읽습니다.",
        "url": "https://blog.stargateedu.co.kr/math/",
        "read": "in-app",
    },
    {
        "id": "notion",
        "name": "Notion Archive",
        "platform": "Notion",
        "topic": "도시·연구",
        "blurb": "교육·AI·연구·창업 기록을 모은 아카이브.",
        "url": "https://blog.stargateedu.co.kr/#notion-blog",
        "read": "in-app",
    },
    {
        "id": "youtube",
        "name": "YouTube 우주인",
        "platform": "YouTube",
        "topic": "수학·AI",
        "blurb": "강의와 연구, AI 활용을 영상으로 만납니다.",
        "url": "https://www.youtube.com/@DONGSOO-MAIN/streams",
        "read": "external",
    },
    {
        "id": "instagram",
        "name": "소셜 네트워크",
        "platform": "Instagram",
        "topic": "수학·AI",
        "blurb": "교육·AI·비즈니스 소식과 일상의 짧은 기록.",
        "url": "https://www.instagram.com/jds0688/",
        "read": "external",
    },
]

TOPIC_BY_NOTION = {
    "도시·연구": "도시·연구",
    "AI·테크": "수학·AI",
    "교육·입시": "수학·AI",
    "출판·서평": "출판·서평",
    "창업·경영": "부동산·경제",
    "시사·정치": "정치·데이터",
    "공지": "도시·연구",
}

BLOGGER_TOPIC = {
    "지역별 공공데이터를 비교할 때 분모부터 확인하기": "도시·연구",
}


def fetch(url: str) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(request, timeout=30) as response:
        return response.read()


def local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def text_of(node: ElementTree.Element | None) -> str:
    if node is None or node.text is None:
        return ""
    return node.text.strip()


def child_text(node: ElementTree.Element, name: str) -> str:
    for child in list(node):
        if local_name(child.tag) == name:
            value = "".join(child.itertext()).strip()
            if value:
                return value
    return ""


class _Sanitizer(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self.skip = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag = tag.lower()
        if tag in {"script", "style", "iframe", "object", "embed"}:
            self.skip += 1
            return
        if self.skip or tag not in ALLOW_TAGS:
            return
        if tag == "a":
            href = ""
            for key, value in attrs:
                if key.lower() == "href" and value and value.startswith(("http://", "https://")):
                    href = value.replace('"', "%22")
            if not href:
                return
            self.parts.append(f'<a href="{href}" target="_blank" rel="noopener">')
            return
        if tag == "br":
            self.parts.append("<br>")
            return
        self.parts.append(f"<{tag}>")

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if tag in {"script", "style", "iframe", "object", "embed"}:
            if self.skip:
                self.skip -= 1
            return
        if self.skip or tag not in ALLOW_TAGS or tag == "br":
            return
        self.parts.append(f"</{tag}>")

    def handle_data(self, data: str) -> None:
        if self.skip:
            return
        self.parts.append(
            data.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        )


def light_markdown(text: str) -> str:
    if "**" not in text and "##" not in text and "#" not in text:
        return text
    text = re.sub(r"(?m)^### (.+)$", r"<h3>\1</h3>", text)
    text = re.sub(r"(?m)^## (.+)$", r"<h2>\1</h2>", text)
    text = re.sub(r"(?m)^# (.+)$", r"<h2>\1</h2>", text)
    text = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", text)
    text = re.sub(r"(?m)^\s*---\s*$", "", text)
    return text


def sanitize(html: str) -> str:
    parser = _Sanitizer()
    parser.feed(html or "")
    parser.close()
    cleaned = "".join(parser.parts)
    cleaned = re.sub(r"(?:<br>\s*){3,}", "<br><br>", cleaned)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    cleaned = re.sub(r"(?m)^[ \t]*#{1,3}[ \t]+(.+)$", r"<h2>\1</h2>", cleaned)
    cleaned = re.sub(r"(?m)^[ \t]*---[ \t]*$", "", cleaned)
    cleaned = cleaned.strip()
    if cleaned and not re.search(r"<(p|h2|h3|h4|ul|ol|blockquote|pre)\b", cleaned):
        chunks = [chunk.strip() for chunk in re.split(r"(?:<br>\s*){2,}", cleaned) if chunk.strip()]
        cleaned = "".join(f"<p>{chunk}</p>" for chunk in chunks) if chunks else cleaned
    return cleaned


def plain(html: str, limit: int = 180) -> str:
    text = re.sub(r"<[^>]+>", " ", html or "")
    text = re.sub(r"\s+", " ", text).strip()
    if len(text) <= limit:
        return text
    return text[: limit - 1].rstrip() + "…"


def canonical(url: str) -> str:
    url = (url or "").strip()
    url = re.sub(r"^http://", "https://", url)
    url = url.split("#", 1)[0].split("?", 1)[0]
    return url.rstrip("/")


def channel_for(url: str) -> str | None:
    host = re.sub(r"^https://", "", canonical(url)).split("/", 1)[0]
    path = canonical(url)
    if "stargate8224" in path:
        return "naver-market"
    if "stargate8225" in path:
        return "naver-lab"
    if host.endswith("blogspot.com"):
        return "blogger"
    if host.endswith("tistory.com"):
        return "tistory"
    if "notion.com" in host or "stargateedu.co.kr" in host:
        return "notion"
    if "youtube.com" in host or "youtu.be" in host:
        return "youtube"
    if "instagram.com" in host:
        return "instagram"
    return None


def topic_for(channel_id: str, title: str, category: str | None = None) -> str:
    if channel_id == "blogger" and title in BLOGGER_TOPIC:
        return BLOGGER_TOPIC[title]
    if category and category in TOPIC_BY_NOTION:
        return TOPIC_BY_NOTION[category]
    for channel in CHANNELS:
        if channel["id"] == channel_id:
            return channel["topic"]
    return "도시·연구"


def slug(url: str) -> str:
    token = canonical(url).rstrip("/").split("/")[-1]
    token = re.sub(r"[^0-9A-Za-z가-힣._-]+", "-", token).strip("-")
    return token[:80] or "post"


def parse_hub(html: str) -> tuple[str, list[dict]]:
    generator = ""
    match = re.search(r'<meta name="generator" content="([^"]+)"', html)
    if match:
        generator = match.group(1)
    items = []
    pattern = re.compile(
        r'<article class="latest-item">(.*?)</article>',
        re.S,
    )
    for block in pattern.findall(html):
        href = re.search(r'href="(https?://[^"]+)"', block)
        title = re.search(r'rel="noopener">([^<]+)</a>', block)
        when = re.search(r'datetime="([^"]+)"', block)
        if not (href and title and when):
            continue
        url = href.group(1)
        channel_id = channel_for(url)
        if not channel_id:
            continue
        items.append(
            {
                "title": title.group(1).strip(),
                "url": url,
                "publishedAt": when.group(1),
                "channelId": channel_id,
            }
        )
    return generator, items


def parse_rss(xml_bytes: bytes) -> dict[str, dict]:
    root = ElementTree.fromstring(xml_bytes)
    found: dict[str, dict] = {}
    for node in root.iter():
        if local_name(node.tag) != "item" and local_name(node.tag) != "entry":
            continue
        link = child_text(node, "link")
        if not link:
            for child in list(node):
                if local_name(child.tag) == "link":
                    link = child.attrib.get("href") or "".join(child.itertext()).strip()
                    if link:
                        break
        title = child_text(node, "title")
        body = child_text(node, "encoded") or child_text(node, "content") or child_text(node, "description") or child_text(node, "summary")
        if link and title:
            found[canonical(link)] = {"title": title, "body": body}
    return found


def rss_lookup(indexes: list[dict[str, dict]], url: str) -> dict | None:
    key = canonical(url)
    for index in indexes:
        if key in index:
            return index[key]
    return None


def post_record(raw: dict, indexes: list[dict[str, dict]], on_home: bool) -> dict:
    channel_id = raw["channelId"]
    channel = next(item for item in CHANNELS if item["id"] == channel_id)
    extra = rss_lookup(indexes, raw["url"])
    body_html = sanitize(light_markdown(extra["body"])) if extra else ""
    read = channel["read"]
    if read == "in-app" and not plain(body_html, 40):
        read = "external"
        body_html = ""
    if read == "external":
        body_html = ""
    summary = raw.get("summary") or plain(extra["body"] if extra else "", 180)
    return {
        "id": f"{channel_id}-{slug(raw['url'])}",
        "title": raw["title"],
        "url": raw["url"],
        "publishedAt": raw["publishedAt"],
        "channelId": channel_id,
        "topic": raw.get("topic") or topic_for(channel_id, raw["title"], raw.get("category")),
        "summary": summary,
        "bodyHtml": body_html or None,
        "read": read,
        "onHome": on_home,
    }


def notion_posts(payload: dict) -> list[dict]:
    posts = []
    for item in payload.get("posts", []):
        body = sanitize(light_markdown(item.get("html") or ""))
        published = item.get("date") or "2026-01-01"
        if len(published) == 10:
            published = f"{published}T12:00:00+09:00"
        url = item.get("external_url") or item.get("notion_url") or HUB
        posts.append(
            {
                "id": "notion-" + item["id"].replace("-", ""),
                "title": item["title"],
                "url": url,
                "publishedAt": published,
                "channelId": "notion",
                "topic": topic_for("notion", item["title"], item.get("category")),
                "category": item.get("category") or "",
                "summary": item.get("summary") or plain(body, 180),
                "bodyHtml": body or None,
                "read": "in-app" if body else "external",
                "onHome": False,
            }
        )
    return posts


def collection_report(posts: list[dict], notion_generated_at: str) -> dict:
    """채널별 수집 결과. 허브 빌더가 같은 목록을 feed.json으로 쓸 때도 이 모양을 유지한다."""
    home = [post for post in posts if post["onHome"]]
    rows = []
    for channel in CHANNELS:
        count = sum(1 for post in home if post["channelId"] == channel["id"])
        archive = sum(1 for post in posts if post["channelId"] == channel["id"] and not post["onHome"])
        if channel["id"] in {"notion", "math"} and archive:
            status = "archive"
        elif channel["id"] in {"youtube", "instagram", "math"}:
            status = "origin-only"
        elif count:
            status = "ok"
        else:
            status = "missing"
        rows.append(
            {
                "id": channel["id"],
                "name": channel["name"],
                "read": channel["read"],
                "homeCount": count,
                "archiveCount": archive,
                "status": status,
            }
        )
    stale = str(notion_generated_at or "").startswith("2026-09-12")
    return {
        "channels": rows,
        "notionGeneratedAt": notion_generated_at,
        "notionStatus": "unchanged-file" if stale else "updated",
        "missing": [row["id"] for row in rows if row["status"] == "missing"],
    }


def math_body(item: dict) -> str:
    steps = "".join(f"<li>{step}</li>" for step in item.get("solution") or [])
    html_body = (
        f"<p>{item.get('problem') or ''}</p>"
        f"<h2>힌트</h2><p>{item.get('hint') or ''}</p>"
        f"<h2>단계별 풀이</h2><ol>{steps}</ol>"
        f"<h2>정답</h2><p>{item.get('answer') or ''}</p>"
        f"<p>{item.get('copyright_note') or ''}</p>"
    )
    return sanitize(html_body)


def math_posts(payload: dict) -> list[dict]:
    posts = []
    for item in payload.get("posts") or []:
        published = item.get("published_at") or ""
        if len(published) == 10:
            published = f"{published}T12:00:00+09:00"
        if not published and item.get("date"):
            published = f"{item['date']}T12:00:00+09:00"
        posts.append(
            {
                "id": "math-" + re.sub(r"[^0-9A-Za-z_-]", "", item["id"]),
                "title": item["title"],
                "url": item.get("canonical") or "https://blog.stargateedu.co.kr/math/",
                "publishedAt": published or "2026-01-01T12:00:00+09:00",
                "channelId": "math",
                "topic": "수학·AI",
                "summary": item.get("summary") or item.get("problem") or "",
                "bodyHtml": math_body(item),
                "read": "in-app",
                "onHome": False,
            }
        )
    return posts


def daily_problem(payload: dict) -> dict:
    item = (payload.get("posts") or [None])[0]
    if not item:
        return {
            "title": "하루 한 문제",
            "status": "자동발행 준비",
            "detail": "발행 피드를 확인하는 중입니다.",
            "href": "https://blog.stargateedu.co.kr/math/",
            "phase": 4,
        }
    return {
        "title": "하루 한 문제",
        "status": " · ".join(part for part in (item.get("series"), item.get("level")) if part),
        "detail": item.get("problem") or "",
        "problemId": "math-" + re.sub(r"[^0-9A-Za-z_-]", "", item["id"]),
        "href": item.get("canonical") or "https://blog.stargateedu.co.kr/math/",
        "sourceUpdatedAt": payload.get("updated_at"),
        "phase": 4,
    }


def visitors() -> dict:
    endpoint = "https://stargate.stargate8225.workers.dev/api/blog-visitors"
    try:
        payload = json.loads(fetch(endpoint).decode("utf-8"))
        today = payload["today"]
        total = payload["total"]
        day = payload["date"]
    except Exception:
        today, total, day = 0, 0, datetime.now(KST).date().isoformat()
    return {
        "date": day,
        "today": today,
        "total": total,
        "source": "firebase",
        "endpoint": endpoint,
        "note": "같은 브라우저 하루 1회. 누적은 일별 방문 합계. 실시간 조회는 blog.stargateedu.co.kr 출처만 허용됩니다.",
    }


def main() -> None:
    hub_html = fetch(HUB).decode("utf-8", "replace")
    generator, home = parse_hub(hub_html)
    if len(home) != 20:
        raise SystemExit(f"홈 최신 글이 20편이 아닙니다: {len(home)}")
    indexes = [
        parse_rss(fetch("https://dongsoo.tistory.com/rss")),
        parse_rss(fetch("https://jds0688.blogspot.com/feeds/posts/default?alt=rss")),
        parse_rss(fetch("https://rss.blog.naver.com/stargate8224.xml")),
        parse_rss(fetch("https://rss.blog.naver.com/stargate8225.xml")),
    ]
    notion = json.loads(fetch(HUB + "posts/posts.json").decode("utf-8"))
    math = json.loads(fetch(HUB + "math/posts.json").decode("utf-8"))
    posts = [post_record(item, indexes, True) for item in home]
    posts.extend(notion_posts(notion))
    posts.extend(math_posts(math))
    feed = {
        "generatedAt": datetime.now(KST).isoformat(timespec="seconds"),
        "hub": {
            "url": HUB,
            "generator": generator,
            "proposalBaseline": "2026-10-24 06:04 KST",
        },
        "visitors": visitors(),
        "topics": TOPICS,
        "channels": CHANNELS,
        "posts": posts,
        "daily": daily_problem(math),
        "collection": collection_report(posts, notion.get("generated_at") or ""),
        "web": {
            "feedback": "https://blog.stargateedu.co.kr/#feedback",
            "survey": "https://blog.stargateedu.co.kr/#survey",
            "community": "https://blog.stargateedu.co.kr/#community",
            "play": "https://play.google.com/store/apps/details?id=kr.co.stargateedu.twa&referrer=utm_source%3Dblog-reader",
            "origin": "https://blog.stargateedu.co.kr/app/",
            "privacy": "https://stargateedu.co.kr/privacy.html",
        },
        "publisher": {
            "name": "STARGATE",
            "legalName": "주식회사 별의문",
            "email": "ceo@stargateedu.co.kr",
            "package": "kr.co.stargateedu.blog",
        },
        "notionArchive": {
            "generatedAt": notion.get("generated_at"),
            "count": notion.get("count"),
            "source": HUB + "posts/posts.json",
        },
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(feed, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    home_reads = {}
    for post in posts:
        if post["onHome"]:
            home_reads[post["read"]] = home_reads.get(post["read"], 0) + 1
    print(f"wrote {OUT} posts={len(posts)} home={sum(1 for p in posts if p['onHome'])} reads={home_reads}")


if __name__ == "__main__":
    main()
