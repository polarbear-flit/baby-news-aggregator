"""重複除去のテスト。"""

import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.fetcher import normalize_title, deduplicate, _make_group_id  # noqa: E402


class TestNormalizeTitle(unittest.TestCase):
    def test_image_pattern_removed(self):
        n1 = normalize_title("ピジョン新製品 画像1/34")
        n2 = normalize_title("ピジョン新製品 画像3/34")
        self.assertEqual(n1, n2)
        self.assertIn("ピジョン新製品", n1)

    def test_photo_pattern_removed(self):
        n1 = normalize_title("コンビ新ベビーカー 写真1/12")
        n2 = normalize_title("コンビ新ベビーカー 写真5/12")
        self.assertEqual(n1, n2)

    def test_trailing_media_name_removed(self):
        n1 = normalize_title("ベビーカー新発売 | maidonanews")
        n2 = normalize_title("ベビーカー新発売 - 朝日新聞")
        self.assertEqual(n1, n2)

    def test_brackets_removed(self):
        n = normalize_title("ベビー用品の新動向【2026年版】")
        self.assertNotIn("2026", n)


class TestDeduplicate(unittest.TestCase):
    def test_image_articles_deduplicated(self):
        articles = [
            {"title": "ピジョン新製品 画像1/34", "url": "https://a.example.com/1"},
            {"title": "ピジョン新製品 画像3/34", "url": "https://a.example.com/3"},
            {"title": "ピジョン新製品 画像2/34", "url": "https://a.example.com/2"},
        ]
        result = deduplicate(articles)
        self.assertEqual(len(result), 1)

    def test_url_dedup(self):
        articles = [
            {"title": "A", "url": "https://x.example.com/article"},
            {"title": "B", "url": "https://x.example.com/article/"},
        ]
        result = deduplicate(articles)
        self.assertEqual(len(result), 1)

    def test_distinct_articles_kept(self):
        articles = [
            {"title": "ピジョン新商品発表", "url": "https://a.example.com/1"},
            {"title": "コンビベビーカー新発売", "url": "https://b.example.com/2"},
        ]
        result = deduplicate(articles)
        self.assertEqual(len(result), 2)

    def test_duplicate_group_id_assigned(self):
        articles = [
            {"title": "ピジョン新商品発表", "url": "https://a.example.com/1"},
            {"title": "コンビベビーカー新発売", "url": "https://b.example.com/2"},
        ]
        result = deduplicate(articles)
        for a in result:
            self.assertIn("duplicate_group_id", a)
            self.assertTrue(a["duplicate_group_id"])

    def test_same_normalized_title_same_group_id(self):
        nt = normalize_title("ピジョン新製品 画像1/34")
        self.assertEqual(_make_group_id(nt), _make_group_id(nt))


if __name__ == "__main__":
    unittest.main()
