import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

MODULE = Path(__file__).resolve().parents[1] / "scripts" / "build_reader_feed.py"
spec = importlib.util.spec_from_file_location("reader_feed", MODULE)
reader = importlib.util.module_from_spec(spec)
spec.loader.exec_module(reader)


class ReaderFeedTests(unittest.TestCase):
    def write(self, folder, data):
        path = Path(folder) / "feed.json"
        path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
        return path

    def test_unchanged_content_keeps_previous_generated_at(self):
        with tempfile.TemporaryDirectory() as folder:
            path = self.write(folder, {"generatedAt": "2026-11-15T07:15:00+09:00", "posts": [1, 2]})
            feed = {"generatedAt": "2026-11-15T20:37:00+09:00", "posts": [1, 2]}
            reader.keep_previous_generated_at(feed, path)
            self.assertEqual(feed["generatedAt"], "2026-11-15T07:15:00+09:00")
            self.assertEqual(list(feed), ["generatedAt", "posts"])

    def test_changed_content_or_missing_file_uses_new_generated_at(self):
        with tempfile.TemporaryDirectory() as folder:
            path = self.write(folder, {"generatedAt": "2026-11-15T07:15:00+09:00", "posts": [1]})
            feed = {"generatedAt": "2026-11-15T20:37:00+09:00", "posts": [1, 2]}
            reader.keep_previous_generated_at(feed, path)
            self.assertEqual(feed["generatedAt"], "2026-11-15T20:37:00+09:00")
            missing = {"generatedAt": "2026-11-15T20:37:00+09:00", "posts": []}
            reader.keep_previous_generated_at(missing, Path(folder) / "none.json")
            self.assertEqual(missing["generatedAt"], "2026-11-15T20:37:00+09:00")


if __name__ == "__main__":
    unittest.main()
