import importlib.util
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import feedparser

MODULE = Path(__file__).resolve().parents[1] / "scripts" / "build_hub_index.py"
spec = importlib.util.spec_from_file_location("hub", MODULE)
hub = importlib.util.module_from_spec(spec)
spec.loader.exec_module(hub)


class HubBuilderTests(unittest.TestCase):
    def test_titles_decode_entities_but_preserve_meaningful_hashes_and_math(self):
        self.assertEqual(hub.clean_title("# 도시 &amp;mdash; 연구 &amp;middot; AI"), "도시 — 연구 · AI")
        self.assertEqual(hub.clean_title("C#과 #AI, x < y &amp; z > 0"), "C#과 #AI, x < y & z > 0")
        self.assertEqual(hub.clean_title("A &notable &copycat"), "A &notable &copycat")
        self.assertEqual(hub.clean_title("\n ##   새 글\n  제목  "), "새 글 제목")
        self.assertEqual(hub.clean_title(None), "제목 없음")

    def test_korean_date_and_timestamp_use_offset_not_utc_calendar_day(self):
        parsed = feedparser.parse(b'<feed xmlns="http://www.w3.org/2005/Atom"><entry><title>test</title><published>2026-10-16T15:10:00Z</published></entry></feed>')
        entry = parsed.entries[0]
        self.assertEqual(hub.parse_pubdate(entry), "2026-10-17")
        self.assertEqual(hub.parse_timestamp(entry).isoformat(), "2026-10-17T00:10:00+09:00")
        self.assertEqual(hub.parse_timestamp({"published": "Fri, 16 Oct 2026 11:18:10 +0000"}).hour, 20)
        self.assertEqual(hub.parse_timestamp({"published": "bad", "updated": "2026-10-16T20:00:00+09:00"}).hour, 20)
        self.assertIsNone(hub.parse_timestamp({"published": "bad"}))

    def test_deduplication_removes_tracking_but_keeps_article_identifiers(self):
        tracked = "https://blog.naver.com/stargate8224/123?fromRss=true&trackingCode=rss&utm_source=a#comments"
        self.assertEqual(hub.clean_url(tracked), "https://blog.naver.com/stargate8224/123")
        self.assertEqual(hub.clean_url("http://blog.naver.com:80/stargate8224/123"), hub.clean_url(tracked))
        self.assertEqual(hub.clean_url("https://m.blog.naver.com/PostView.naver?blogId=stargate8224&logNo=123"), hub.clean_url(tracked))
        self.assertEqual(hub.clean_url("https://jds0688.blogspot.com/2026/10/ai.html?m=1"), "https://jds0688.blogspot.com/2026/10/ai.html")
        self.assertNotEqual(hub.clean_url("https://example.com/post?id=1"), hub.clean_url("https://example.com/post?id=2"))
        self.assertIn("notable=2", hub.clean_url("https://example.com/post?id=1&notable=2"))
        self.assertEqual(hub.clean_url("https://example.com/post?id=1&amp;page=2"), "https://example.com/post?id=1&page=2")
        self.assertEqual(hub.clean_url("javascript:alert(1)"), "")
        self.assertEqual(hub.clean_url("https://user:password@example.com/post"), "")

    def test_full_timestamps_sort_same_day_and_duplicate_keeps_latest(self):
        posts = [
            {"link": "https://example.com/first", "sort_key": 10, "title": "old"},
            {"link": "https://example.com/second", "sort_key": 20, "title": "second"},
            {"link": "https://example.com/first", "sort_key": 30, "title": "new"},
        ]
        self.assertEqual([p["title"] for p in hub.select_posts(posts)], ["new", "second"])
        self.assertEqual(hub.article_key("https://youtu.be/k4Y7OwPw_rk"), hub.article_key("https://www.youtube.com/watch?v=k4Y7OwPw_rk"))
        self.assertEqual(hub.article_key("https://www.youtube.com/shorts/k4Y7OwPw_rk"), hub.article_key("https://www.youtube.com/watch?v=k4Y7OwPw_rk"))

    def test_duplicates_do_not_consume_per_feed_limit_and_all_posts_are_sorted(self):
        entries = [{"title": f"# 글 {i}", "link": f"https://example.com/post/{i}", "published": f"2026-10-16T{i:02}:00:00+09:00"} for i in range(1,8)]
        entries.insert(0, {**entries[6], "link": entries[6]["link"]+"?utm_source=rss"})
        parsed = feedparser.FeedParserDict(entries=entries, bozo=False)
        with patch.object(hub.feedparser, "parse", return_value=parsed):
            posts = hub.fetch_feed("test", {"url":"https://example.com/rss", "icon":"x", "color":"#000"})
        self.assertEqual(len(posts), 5)
        self.assertEqual([p["title"] for p in posts], ["글 7", "글 6", "글 5", "글 4", "글 3"])
        self.assertTrue(all(p["published_at"].endswith("+09:00") for p in posts))

    def test_template_escapes_decoded_html_and_keeps_counter_and_eight_channels(self):
        posts = [{"link":"https://example.com/post", "title":hub.clean_title("&lt;script&gt;bad&lt;/script&gt; &amp; OK"), "channel":"test", "icon":"x", "color":"#000", "date":"2026-10-16", "published_at":"2026-10-16T20:00:00+09:00", "display_date":"2026.10.16", "display_time":"20:00"}]
        html = hub.render(posts)
        self.assertIn("&lt;script&gt;bad&lt;/script&gt; &amp; OK", html)
        self.assertNotIn("<script>bad</script>", html)
        self.assertEqual(html.count('class="channel"'), 8)
        self.assertIn('href="https://jds0688.blogspot.com/"', html)
        self.assertEqual(html.count('id="blog-visitor-counter"'), 1)
        self.assertLess(html.index('id="latest"'), html.index('id="categories"'))
        self.assertLess(html.index('id="categories"'), html.index('id="channels"'))
        self.assertLess(html.index('id="channels"'), html.index('id="notion-blog"'))

    def test_total_collection_failure_does_not_replace_existing_homepage(self):
        with tempfile.TemporaryDirectory() as folder:
            output = Path(folder) / "index.html"
            output.write_text("last good page", encoding="utf8")
            with patch.object(hub, "OUTPUT_PATH", output), patch.object(hub, "fetch_feed", return_value=[]):
                self.assertEqual(hub.main(), 1)
            self.assertEqual(output.read_text(encoding="utf8"), "last good page")


if __name__ == "__main__":
    unittest.main()
