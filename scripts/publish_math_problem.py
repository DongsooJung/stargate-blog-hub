#!/usr/bin/env python3
"""Publish exactly one queued math problem as a blog post.

Default is dry-run. Use --publish to write math/posts.json, math/publish-state.json,
math/problems/<id>/index.html, and a Naver-ready draft payload.
"""
from __future__ import annotations

import argparse
import html
import json
import os
import sys
import urllib.request
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
POSTS_PATH = ROOT / "math" / "posts.json"
STATE_PATH = ROOT / "math" / "publish-state.json"
DEFAULT_SOURCE = "https://stargateedu.co.kr/research/math/archive/problems.json"
KST = ZoneInfo("Asia/Seoul")


def load_json(path: Path, default):
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def fetch_source(url: str):
    req = urllib.request.Request(url, headers={"User-Agent": "stargate-math-publisher/1.0"})
    with urllib.request.urlopen(req, timeout=20) as res:
        return json.loads(res.read().decode("utf-8"))


def choose_problem(source, state):
    published = set(state.get("published", []))
    for problem in source.get("problems", []):
        if problem.get("blog_status") == "queued" and problem.get("id") not in published:
            return problem
    return None


def build_post(problem, now):
    pid = problem["id"]
    title = f"[오늘의 수학] {problem['title']} — {problem['series']} {problem['level']}"
    summary = f"{problem['topic']} 문제입니다. 핵심은 {problem['insight']}"
    research_url = problem.get("research_url") or f"/research/math/archive/?id={pid}"
    if research_url.startswith("/"):
        research_url = "https://stargateedu.co.kr" + research_url
    return {
        "id": pid,
        "title": title,
        "date": now.strftime("%Y-%m-%d"),
        "published_at": now.isoformat(timespec="seconds"),
        "series": problem["series"],
        "level": problem["level"],
        "topic": problem["topic"],
        "difficulty": problem["difficulty"],
        "problem": problem["problem"],
        "hint": problem["insight"],
        "answer": problem["answer"],
        "solution": problem["solution"],
        "summary": summary,
        "research_url": research_url,
        "canonical": f"https://blog.stargateedu.co.kr/math/problems/{pid}/",
        "copyright_note": "교육용 재구성 문제이며 실제 기출 원문을 그대로 복제하지 않습니다."
    }


def render_page(post):
    steps = "".join(
        f'<li><span>{i}</span><p>{html.escape(step)}</p></li>'
        for i, step in enumerate(post["solution"], 1)
    )
    return f'''<!doctype html>
<html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{html.escape(post['title'])} | Stargate Math</title>
<meta name="description" content="{html.escape(post['summary'])}">
<link rel="canonical" href="{html.escape(post['canonical'])}">
<style>*{{box-sizing:border-box}}body{{margin:0;font-family:"Noto Sans KR","Malgun Gothic",sans-serif;color:#182038;line-height:1.72;background:#f7f9fc}}a{{color:#0b3d91}}.w{{width:min(880px,calc(100% - 34px));margin:auto}}nav{{background:#0b1738;color:#fff}}nav .w{{min-height:58px;display:flex;align-items:center;justify-content:space-between}}nav a{{color:#fff;text-decoration:none}}header{{padding:64px 0 48px;background:linear-gradient(145deg,#0b1738,#24466e);color:#fff}}header small{{color:#f1c77a;font-weight:800}}header h1{{font-size:clamp(30px,5vw,46px);line-height:1.24;margin:10px 0}}header p{{color:#dce3f2}}main{{padding:44px 0}}.box{{background:#fff;border:1px solid #e3e8f2;border-radius:16px;padding:22px;margin-bottom:18px}}.problem{{font-size:1.16rem;font-weight:700}}.hint{{border-left:4px solid #d9a441;background:#fff8e8}}ol{{list-style:none;padding:0;display:grid;gap:10px}}li{{display:grid;grid-template-columns:34px 1fr;gap:10px;align-items:start}}li span{{width:30px;height:30px;border-radius:9px;background:#0b1738;color:#f1c77a;display:grid;place-items:center;font-weight:900}}li p{{margin:2px 0}}.answer{{font-size:1.35rem;font-weight:900;color:#0b1738}}.note{{font-size:.87rem;color:#66708d}}footer{{padding:24px;background:#07102a;color:#9aa4bf;text-align:center}}</style></head>
<body><nav><div class="w"><a href="/math/"><b>STARGATE MATH</b></a><a href="/">Blog Hub</a></div></nav>
<header><div class="w"><small>{html.escape(post['series'])} · {html.escape(post['level'])} · 난도 {post['difficulty']}/5</small><h1>{html.escape(post['title'])}</h1><p>{html.escape(post['topic'])} · {html.escape(post['date'])}</p></div></header>
<main><div class="w"><section class="box"><h2>오늘의 문제</h2><p class="problem">{html.escape(post['problem'])}</p></section><section class="box hint"><h2>힌트</h2><p>{html.escape(post['hint'])}</p></section><section class="box"><h2>단계별 풀이</h2><ol>{steps}</ol></section><section class="box"><h2>정답</h2><p class="answer">{html.escape(post['answer'])}</p><p><a href="{html.escape(post['research_url'])}">연구 아카이브에서 다시 보기 →</a></p><p class="note">{html.escape(post['copyright_note'])}</p></section></div></main>
<footer>© 2026 Stargate Corporation · One Problem a Day</footer></body></html>'''


def build_naver_payload(post):
    lines = [
        post["title"],
        "",
        f"[{post['series']} · {post['level']} · {post['topic']} · 난도 {post['difficulty']}/5]",
        "",
        "오늘의 문제",
        post["problem"],
        "",
        "힌트",
        post["hint"],
        "",
        "단계별 풀이",
    ]
    for i, step in enumerate(post["solution"], 1):
        lines.append(f"{i}. {step}")
    lines += [
        "",
        f"정답: {post['answer']}",
        "",
        f"연구 아카이브: {post['research_url']}",
        post["copyright_note"],
    ]
    return {
        "id": post["id"],
        "target": "Naver Blog stargate8225",
        "status": "ready_for_manual_or_browser_publish",
        "title": post["title"],
        "body_text": "\n".join(lines),
        "tags": ["수학", "중등수학", post["series"], post["level"], post["topic"], "오늘의수학"],
        "canonical": post["canonical"],
        "research_url": post["research_url"],
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--publish", action="store_true", help="write one new post")
    parser.add_argument("--source", default=os.environ.get("MATH_PROBLEMS_URL", DEFAULT_SOURCE))
    args = parser.parse_args()

    try:
        source = fetch_source(args.source)
    except Exception as exc:
        print(f"ERROR: cannot fetch math source: {exc}", file=sys.stderr)
        return 2

    state = load_json(STATE_PATH, {"published": []})
    problem = choose_problem(source, state)
    if not problem:
        print("No queued unpublished problem remains.")
        return 0

    print(f"NEXT: {problem['id']} | {problem['title']} | answer={problem['answer']}")
    if not args.publish:
        print("DRY-RUN: no files changed. Use --publish to publish one item.")
        return 0

    now = datetime.now(KST)
    post = build_post(problem, now)
    posts_doc = load_json(POSTS_PATH, {"posts": []})
    posts = [p for p in posts_doc.get("posts", []) if p.get("id") != post["id"]]
    posts.insert(0, post)
    posts_doc = {"updated_at": now.isoformat(timespec="seconds"), "source": args.source, "posts": posts}

    target = ROOT / "math" / "problems" / problem["id"] / "index.html"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(render_page(post), encoding="utf-8")
    POSTS_PATH.write_text(json.dumps(posts_doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    naver_target = ROOT / "math" / "naver-queue" / f"{problem['id']}.json"
    naver_target.parent.mkdir(parents=True, exist_ok=True)
    naver_target.write_text(json.dumps(build_naver_payload(post), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    published = state.setdefault("published", [])
    if problem["id"] not in published:
        published.append(problem["id"])
    state["last_published_at"] = now.isoformat(timespec="seconds")
    state["last_problem_id"] = problem["id"]
    STATE_PATH.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"PUBLISHED: {post['canonical']}")
    print(f"NAVER QUEUE: math/naver-queue/{problem['id']}.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
