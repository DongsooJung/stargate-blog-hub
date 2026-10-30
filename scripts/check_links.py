#!/usr/bin/env python3
"""blog.stargateedu.co.kr 주요 페이지의 링크를 실제 요청해 404 등 깨진 링크를 찾는다.

검사 범위
  - 허브 주요 페이지(/, /posts/, /math/, /reading/, /career-trends/)의 <a href>
  - math/posts.json · posts/posts.json 의 문제 페이지·외부 원문 링크
  - 스타게이트 도메인(*.stargateedu.co.kr, stargateedu.co.kr)은 항상 검사,
    외부 도메인은 CHECK_EXTERNAL=1 일 때만 검사(봇 차단으로 인한 오탐 방지)

깨진 링크가 있으면 ::error 주석을 남기고 exit 1, BROKEN_OUT 파일에 목록을 기록한다.
"""
from __future__ import annotations

import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor

BASE = os.environ.get("BASE_URL", "https://blog.stargateedu.co.kr/")
PAGES = ["", "posts/", "math/", "reading/", "career-trends/"]
FEEDS = ["math/posts.json", "posts/posts.json"]
CHECK_EXTERNAL = os.environ.get("CHECK_EXTERNAL") == "1"
OUT = os.environ.get("BROKEN_OUT", "broken-links.txt")
UA = {"User-Agent": "Mozilla/5.0 (stargate-link-check)"}
HREF = re.compile(r"""href\s*=\s*["']([^"'#]+)""", re.I)


def get(url: str, method: str = "GET"):
    req = urllib.request.Request(url, headers=UA, method=method)
    try:
        with urllib.request.urlopen(req, timeout=20) as res:
            return res.status, res.read() if method == "GET" else b""
    except urllib.error.HTTPError as e:
        return e.code, b""
    except Exception as e:  # 네트워크 오류
        return f"ERR {type(e).__name__}", b""


def is_ours(url: str) -> bool:
    host = urllib.parse.urlparse(url).hostname or ""
    return host == "stargateedu.co.kr" or host.endswith(".stargateedu.co.kr")


def collect() -> dict[str, set[str]]:
    found: dict[str, set[str]] = {}

    def add(url, src):
        url = url.strip()
        if not url.startswith("http") or "${" in url or "{" in url:
            return
        if is_ours(url) or CHECK_EXTERNAL:
            found.setdefault(url.split("#")[0], set()).add(src)

    for p in PAGES:
        page = urllib.parse.urljoin(BASE, p)
        status, body = get(page)
        found.setdefault(page, set()).add("(주요 페이지)")
        if status != 200:
            continue
        for href in HREF.findall(body.decode("utf-8", "ignore")):
            if href.startswith(("mailto:", "tel:", "javascript:", "data:")):
                continue
            add(urllib.parse.urljoin(page, href), page)

    for f in FEEDS:
        status, body = get(urllib.parse.urljoin(BASE, f))
        if status != 200:
            found.setdefault(urllib.parse.urljoin(BASE, f), set()).add("(피드)")
            continue
        for post in json.loads(body).get("posts", []):
            for key in ("canonical", "external_url", "research_url"):
                if post.get(key):
                    add(post[key], f)
            if f.startswith("math/") and post.get("id"):
                add(urllib.parse.urljoin(BASE, f"math/problems/{post['id']}/"), f)
    return found


def main() -> int:
    links = collect()
    with ThreadPoolExecutor(8) as ex:
        results = dict(zip(links, ex.map(lambda u: get(u)[0], links)))
    broken = {u: s for u, s in results.items() if s != 200}
    print(f"::notice title=링크 검사::검사 {len(results)}개 · 깨짐 {len(broken)}개")
    lines = []
    for url, status in sorted(broken.items()):
        srcs = ", ".join(sorted(links[url]))[:200]
        lines.append(f"- [{status}] {url}  ← {srcs}")
        print(f"::error title=깨진 링크 {status}::{url} (출처: {srcs})")
    with open(OUT, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines))
    return 1 if broken else 0


if __name__ == "__main__":
    sys.exit(main())
