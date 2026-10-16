import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import build_hub_index as hub  # noqa: E402


ROOT = Path(__file__).resolve().parents[1]


def channel(**overrides):
    data = dict(
        id="naver-estate",
        name="스타게이트",
        description="설명",
        url="https://blog.naver.com/stargate8224",
        platform="네이버",
        topic="부동산·경제",
        icon="📒",
        color="#03C75A",
        rss="https://example.test/rss",
        order=10,
        link_label="바로가기",
        external=True,
    )
    data.update(overrides)
    return hub.Channel(**data)


def post(channel_obj, link, title="제목", when=None, summary="요약"):
    return hub.make_post(channel_obj, title=title, link=link, when=when, summary=summary)


class TextTests(unittest.TestCase):
    def test_decodes_entities_and_strips_heading_hash(self):
        self.assertEqual(hub.clean_title("# 서울 &amp;mdash; 가압류"), "서울 — 가압류")
        self.assertEqual(hub.clean_title("도시공학 &middot; 물류"), "도시공학 · 물류")
        self.assertEqual(hub.clean_title("C# 입문"), "C# 입문")
        self.assertEqual(hub.clean_title("&#39;모두의 AI&#39;"), "'모두의 AI'")

    def test_keeps_hash_inside_title(self):
        self.assertEqual(hub.clean_title("문제 #12 해설"), "문제 #12 해설")

    def test_summary_drops_repeated_title_and_markdown(self):
        title = "맑은 하늘"
        raw = "맑은 하늘 맑은 하늘 **한줄요약** : 테스트 ## 본문"
        self.assertEqual(hub.clean_summary(raw, title), "한줄요약 : 테스트 본문")
        self.assertIn("C#", hub.clean_summary("C# 입문 안내", "다른 제목"))


class UrlTests(unittest.TestCase):
    def test_canonical_removes_tracking(self):
        left = hub.canonical_url("https://blog.naver.com/stargate8224/1?fromRss=true&trackingCode=rss")
        right = hub.canonical_url("https://blog.naver.com/stargate8224/1")
        self.assertEqual(left, right)

    def test_dedupe_keeps_newer(self):
        ch = channel()
        older = post(ch, "https://blog.naver.com/stargate8224/1?fromRss=true", when=datetime(2026, 10, 1, tzinfo=hub.KST))
        newer = post(ch, "https://blog.naver.com/stargate8224/1", title="새 제목", when=datetime(2026, 10, 2, tzinfo=hub.KST))
        result = hub.dedupe_posts([older, newer])
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["title"], "새 제목")


class SortTests(unittest.TestCase):
    def test_same_day_uses_time_and_kst_date(self):
        ch = channel()
        morning = post(ch, "https://example.test/a", when=datetime(2026, 10, 3, 9, 0, tzinfo=hub.KST))
        evening = post(ch, "https://example.test/b", when=datetime(2026, 10, 3, 18, 30, tzinfo=hub.KST))
        ordered = hub.sort_posts([morning, evening])
        self.assertEqual(ordered[0]["link"], "https://example.test/b")
        utc = datetime(2026, 10, 15, 15, 30, tzinfo=timezone.utc)
        self.assertEqual(utc.astimezone(hub.KST).strftime("%Y-%m-%d"), "2026-10-16")


class FailureTests(unittest.TestCase):
    def test_one_channel_failure_keeps_cache(self):
        ok = channel(id="naver-math", name="수학", platform="네이버", topic="수학·AI")
        failed = channel(id="blogger", name="블로거", platform="Blogger", topic="사회·데이터", rss="https://example.test/b")
        cached = post(failed, "https://jds0688.blogspot.com/2020/01/note.html", title="이전 글",
                      when=datetime(2020, 1, 2, tzinfo=hub.KST))
        fresh = post(ok, "https://blog.naver.com/stargate8225/9", title="새 글",
                     when=datetime(2026, 10, 8, tzinfo=hub.KST))

        def fetcher(ch):
            if ch.id == "blogger":
                return [], "timeout"
            return [fresh], None

        posts, status, fresh_map = hub.assemble(
            [ok, failed],
            fetcher,
            {"blogger": {"posts": [cached], "last_success_at": "2026-10-01T03:00:00+09:00"}},
            {},
            datetime(2026, 10, 16, 11, 0, tzinfo=hub.KST),
        )
        titles = {item["title"] for item in posts}
        self.assertEqual(titles, {"새 글", "이전 글"})
        self.assertIn("naver-math", fresh_map)
        self.assertNotIn("blogger", fresh_map)
        self.assertTrue(status["kept_cache"])
        self.assertFalse(status["all_failed"])
        blogger = next(row for row in status["channels"] if row["id"] == "blogger")
        self.assertFalse(blogger["ok"])
        self.assertTrue(blogger["used_cache"])

    def test_all_failure_preserves_existing_posts(self):
        ch = channel()
        cached = post(ch, "https://blog.naver.com/stargate8224/1", title="유지",
                      when=datetime(2026, 9, 1, tzinfo=hub.KST))

        def fetcher(_ch):
            return [], "HTTP 500"

        posts, status, fresh_map = hub.assemble(
            [ch],
            fetcher,
            {"naver-estate": {"posts": [cached], "last_success_at": "2026-10-01T03:00:00+09:00"}},
            {},
            datetime(2026, 10, 16, 11, 0, tzinfo=hub.KST),
        )
        self.assertEqual([item["title"] for item in posts], ["유지"])
        self.assertTrue(status["all_failed"])
        self.assertEqual(fresh_map, {})
        self.assertIn("기존 글 목록을 유지", hub.status_message(status))


class RenderTests(unittest.TestCase):
    def test_template_exposes_operator_and_blogger(self):
        channels, featured_urls = hub.load_config(ROOT / "config" / "channels.json")
        self.assertEqual(len(channels), 8)
        self.assertIn("blogger", {item.id for item in channels})
        blogger = next(item for item in channels if item.id == "blogger")
        self.assertEqual(blogger.platform, "Blogger")
        self.assertTrue(blogger.rss.endswith("alt=rss"))
        html = hub.render(
            ROOT / "templates" / "허브_템플릿.html",
            channels=channels,
            featured=[],
            posts=[],
            post_count=0,
            updated="2026-10-16 11:00 KST",
            status_message="마지막 수집 시각 · 2026-10-16 11:00 KST",
            all_failed=False,
            partial=False,
            platforms=hub.platforms_for(channels),
            topics=hub.TOPICS,
            generated_at="2026-10-16T11:00:00+09:00",
        )
        self.assertIn("<h1>정동수의 지식과 연구</h1>", html)
        self.assertIn("STARGATE · Google Blog", html)
        self.assertIn("업데이트 확인", html)
        self.assertIn("검색 범위는 이 페이지에 수집된 글", html)
        self.assertIn("이 주제의 수집된 글은 아직 없습니다", html)
        self.assertIn("검색어·필터 초기화", html)
        self.assertNotIn("Facebook", html)
        self.assertGreaterEqual(len(featured_urls), 1)

    def test_community_copy_distinguishes_storage(self):
        text = (ROOT / "community.js").read_text(encoding="utf-8")
        self.assertIn("게시글이 등록되었습니다.", text)
        self.assertIn("이 기기에 임시 저장되었습니다. 다른 방문자에게는 보이지 않습니다.", text)
        self.assertIn("작성한 내용은 그대로 두었습니다. 다시 시도해 주세요.", text)
        self.assertIn("소중한 의견이 제출되었습니다. 감사합니다.", text)


class ConfigTests(unittest.TestCase):
    def test_channels_drive_cards_and_feeds(self):
        channels, _featured = hub.load_config(ROOT / "config" / "channels.json")
        rss = [item for item in channels if item.has_rss]
        self.assertEqual([item.platform for item in rss], ["네이버", "네이버", "티스토리", "Blogger", "YouTube"])
        instagram = next(item for item in channels if item.id == "instagram")
        self.assertFalse(instagram.has_rss)
        self.assertIn("instagram.com/jds0688", instagram.url)
        self.assertNotIn("Facebook", instagram.description)


if __name__ == "__main__":
    unittest.main()
