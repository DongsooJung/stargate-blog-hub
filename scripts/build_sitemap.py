"""blog.stargateedu.co.kr sitemap.xml 생성기.

공개 HTML 페이지(각 폴더의 index.html과 루트의 *.html)를 찾아 sitemap.xml을 만듭니다.
수학 하루 한 문제가 발행될 때마다 워크플로에서 다시 실행해 새 문제 주소를 반영합니다.

사용법: python3 scripts/build_sitemap.py
"""
from __future__ import annotations

import subprocess
from pathlib import Path
from xml.sax.saxutils import escape

ROOT = Path(__file__).resolve().parent.parent
BASE = "https://blog.stargateedu.co.kr"

# 공개 페이지가 아닌 폴더·파일
EXCLUDE_DIRS = {".git", ".github", "android", "api", "scripts", "supabase", "templates", "tests", "node_modules", "assets"}
EXCLUDE_FILES = {"404.html"}


def last_modified(path: Path) -> str | None:
    """git 마지막 커밋 날짜(YYYY-MM-DD). 얕은 클론 등으로 못 구하면 생략합니다."""
    try:
        out = subprocess.run(
            ["git", "log", "-1", "--format=%cs", "--", str(path.relative_to(ROOT))],
            cwd=ROOT, capture_output=True, text=True, check=True,
        ).stdout.strip()
        return out or None
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None


def page_url(path: Path) -> str:
    rel = path.relative_to(ROOT).as_posix()
    if rel == "index.html":
        return BASE + "/"
    if rel.endswith("/index.html"):
        return f"{BASE}/{rel[: -len('index.html')]}"
    return f"{BASE}/{rel}"


def collect() -> list[Path]:
    pages = []
    for path in sorted(ROOT.rglob("*.html")):
        rel_parts = path.relative_to(ROOT).parts
        if rel_parts[0] in EXCLUDE_DIRS or path.name in EXCLUDE_FILES:
            continue
        # 폴더 안에서는 index.html만 공개 주소로 봅니다.
        if len(rel_parts) > 1 and path.name != "index.html":
            continue
        pages.append(path)
    return pages


def priority(url: str) -> str:
    if url == BASE + "/":
        return "1.0"
    if "/math/problems/" in url:
        return "0.6"
    return "0.8"


def main() -> None:
    lines = ['<?xml version="1.0" encoding="UTF-8"?>',
             '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    pages = collect()
    for path in pages:
        url = page_url(path)
        lines.append("  <url>")
        lines.append(f"    <loc>{escape(url)}</loc>")
        lm = last_modified(path)
        if lm:
            lines.append(f"    <lastmod>{lm}</lastmod>")
        lines.append(f"    <priority>{priority(url)}</priority>")
        lines.append("  </url>")
    lines.append("</urlset>")
    (ROOT / "sitemap.xml").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"sitemap.xml: {len(pages)}개 주소")


if __name__ == "__main__":
    main()
