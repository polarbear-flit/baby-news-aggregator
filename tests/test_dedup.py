"""重複除去のテスト。

要件:
- 「画像1/34」「画像3/34」は normalize_title で同一になり、deduplicate で1件に統合される
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.fetcher import normalize_title, deduplicate  # noqa: E402


class TestNormalizeTitle(unittest.TestCase):
    def test_image_pattern_removed(self):
        """画像N/M パターンは除去され、本体タイトルが残る"""
        n1 = normalize_title("ピジョン新製品 画像1/34")
        n2 = normalize_title("ピジョン新製品 画像3/34")
        self.assertEqual(n1, n2)
        self.assertIn("ピジョン新製品", n1)

    def test_photo_pattern_removed(self):
        """写真N/M パターンも同様"""
        n1 = normalize_title("コンビ新ベビーカー 写真1/12")
        n2 = normalize_title("コンビ新ベビーカー 写真5/12")
        self.assertEqual(n1, n2)

    def test_trailing_media_name_removed(self):
        """末尾の媒体名（| メディア名）は除去される"""
        n1 = normalize_title("ベビーカー新発売 | maidonanews")
        n2 = normalize_title("ベビーカー新発売 - 朝日新聞")
        self.assertEqual(n1, n2)

    def test_brackets_removed(self):
        """括弧内文字列は除去される"""
        n = normalize_title("ベビー用品の新動向【2026年版】")
        self.assertNotIn("2026", n)
        self.assertNotIn("年版", n)

    def test_whitespace_removed(self):
        """空白は除去される"""
        n = normalize_title("ピ ジ ョ ン  新   製品")
        self.assertNotIn(" ", n)


class TestDeduplicate(unittest.TestCase):
    def test_image_articles_deduplicated(self):
        """画像1/34 と 画像3/34 は重複扱い"""
        articles = [
            {"title": "ピジョン新製品 画像1/34", "url": "https://a.example.com/1"},
            {"title": "ピジョン新製品 画像3/34", "url": "https://a.example.com/3"},
            {"title": "ピジョン新製品 画像2/34", "url": "https://a.example.com/2"},
        ]
        result = deduplicate(articles)
        # 全て同じ正規化タイトルなので1件に集約
        self.assertEqual(len(result), 1)

    def test_url_dedup(self):
        """同一URLは重複"""
        articles = [
            {"title": "A", "url": "https://x.example.com/article"},
            {"title": "B", "url": "https://x.example.com/article/"},  # 末尾スラッシュ違いも同一
        ]
        result = deduplicate(articles)
        self.assertEqual(len(result), 1)

    def test_distinct_articles_kept(self):
        """異なる記事は両方残る"""
        articles = [
            {"title": "ピジョン哺乳瓶リコール", "url": "https://a.example.com/1"},
            {"title": "コンビベビーカー新発売", "url": "https://b.example.com/2"},
        ]
        result = deduplicate(articles)
        self.assertEqual(len(result), 2)


if __name__ == "__main__":
    unittest.main()
