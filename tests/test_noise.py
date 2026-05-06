"""ノイズ判定のテスト。

要件:
- 「西松屋 + 選び方」は企業名があってもノイズになる（CRITICAL_OVERRIDEから企業名を外したため）
- 「西松屋 + リコール」はノイズにならない（CRITICAL_OVERRIDEのリコールで救済）
- 「東京ばな奈 新商品」はベビー用品文脈がなければ除外される
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.fetcher import is_hard_noise, filter_by_keywords  # noqa: E402


class TestHardNoise(unittest.TestCase):
    def test_seimatsuya_choice_guide_is_noise(self):
        """企業名(西松屋)があっても「選び方ガイド」「選び方も紹介」はノイズ"""
        cases = [
            "西松屋のベビー服選び方も紹介",
            "西松屋ベビーカー完全ガイド",
            "西松屋でかわいすぎる子供服",
        ]
        for title in cases:
            with self.subTest(title=title):
                article = {"title": title, "summary": ""}
                self.assertTrue(
                    is_hard_noise(article),
                    f"「{title}」はノイズ判定されるべき（企業名でCRITICAL_OVERRIDE救済されてはいけない）",
                )

    def test_seimatsuya_recall_is_not_noise(self):
        """西松屋でも「リコール」が含まれていればCRITICAL_OVERRIDEで救済される"""
        article = {
            "title": "西松屋でリコール対象商品を販売 - 自主回収のお知らせ",
            "summary": "",
        }
        self.assertFalse(is_hard_noise(article))

    def test_image_gallery_is_noise(self):
        """画像ギャラリーはノイズ"""
        article = {
            "title": "ピジョンの新製品 画像3/34",
            "summary": "",
        }
        self.assertTrue(is_hard_noise(article))

    def test_image_gallery_with_recall_is_not_noise(self):
        """画像ギャラリーでもリコールが含まれれば救済される"""
        article = {
            "title": "ピジョンのリコール対象品 画像一覧",
            "summary": "リコール対象の哺乳瓶",
        }
        self.assertFalse(is_hard_noise(article))

    def test_chiiki_news_closing_is_noise(self):
        """地域の閉店ニュースはノイズ"""
        article = {
            "title": "アカチャンホンポ某店閉店のお知らせ",
            "summary": "",
        }
        self.assertTrue(is_hard_noise(article))

    def test_burger_king_is_noise(self):
        """無関係企業（バーガーキング等）はノイズ"""
        article = {
            "title": "バーガーキングが新キャンペーン開始",
            "summary": "",
        }
        self.assertTrue(is_hard_noise(article))


class TestFilterByKeywords(unittest.TestCase):
    def test_tokyo_banana_dropped_without_baby_context(self):
        """東京ばな奈は子供文脈がないので filter_by_keywords で落ちる（matched_keywords無し）"""
        articles = [{
            "title": "東京ばな奈の新商品が話題に",
            "summary": "新作スイーツ",
            "matched_keywords": [],
        }]
        result = filter_by_keywords(articles)
        self.assertEqual(len(result), 0)

    def test_pigeon_baby_kept(self):
        """ピジョン+赤ちゃん文脈は filter_by_keywords で残る"""
        articles = [{
            "title": "ピジョンが新型哺乳瓶を発表",
            "summary": "授乳サポート機能を強化",
            "matched_keywords": [],
        }]
        result = filter_by_keywords(articles)
        self.assertEqual(len(result), 1)
        self.assertIn("哺乳瓶", result[0]["matched_keywords"])


if __name__ == "__main__":
    unittest.main()
