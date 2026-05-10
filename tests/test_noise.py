"""ノイズ判定のテスト — 業界動向特化版。

要件:
- リコール語（リコール/回収/recall/自主回収）が HARD_NOISE で完全除外される
- 「西松屋 + 選び方ガイド」のような企業名+SEOコラムが除外される（CRITICAL_OVERRIDE が空のため救済なし）
- 「東京ばな奈 新商品」はベビー用品文脈がなければ除外される
- 過去年（2018-2025）が検出される
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.fetcher import is_hard_noise, is_old_topic_title, filter_by_keywords  # noqa: E402


class TestRecallIsHardNoise(unittest.TestCase):
    """ユーザー要望: リコールはチャットに出さない（HARD_NOISE で完全除外）"""

    def test_recall_in_title_is_noise(self):
        """タイトルに「リコール」が含まれていれば HARD_NOISE"""
        article = {"title": "ピジョン哺乳瓶リコールのお知らせ", "summary": ""}
        self.assertTrue(is_hard_noise(article))

    def test_kaishuu_in_title_is_noise(self):
        """「回収」も HARD_NOISE"""
        article = {"title": "コンビ ベビーカー自主回収", "summary": ""}
        self.assertTrue(is_hard_noise(article))

    def test_recall_english_is_noise(self):
        """英語の recall も HARD_NOISE"""
        article = {"title": "Pampers diaper recall in US", "summary": ""}
        self.assertTrue(is_hard_noise(article))

    def test_recall_in_summary_is_noise(self):
        """要約にリコール語があれば HARD_NOISE"""
        article = {
            "title": "ベビーカーの新展開",
            "summary": "リコール対象商品について",
        }
        self.assertTrue(is_hard_noise(article))


class TestEnterpriseNameNotSavedFromNoise(unittest.TestCase):
    """CRITICAL_OVERRIDE が空のため、企業名は noise 救済しない"""

    def test_seimatsuya_choice_guide_is_noise(self):
        """「西松屋 + 選び方ガイド」はノイズ（企業名で救われない）"""
        article = {"title": "西松屋のベビー服選び方ガイド", "summary": ""}
        self.assertTrue(is_hard_noise(article))

    def test_pigeon_recall_is_noise(self):
        """「ピジョン + リコール」もノイズ（リコール語が HARD_NOISE）"""
        article = {"title": "ピジョン哺乳瓶リコール対象商品", "summary": ""}
        self.assertTrue(is_hard_noise(article))

    def test_pigeon_new_product_is_not_noise(self):
        """「ピジョン + 新商品」は noise でない（HARD_NOISE 語が無い）"""
        article = {"title": "ピジョン、新型哺乳瓶を発売", "summary": "授乳サポート機能を強化"}
        self.assertFalse(is_hard_noise(article))


class TestUnrelatedBrandNoise(unittest.TestCase):
    def test_burger_king_is_noise(self):
        article = {"title": "バーガーキングが新キャンペーン開始", "summary": ""}
        self.assertTrue(is_hard_noise(article))

    def test_tokyo_banana_is_noise(self):
        article = {"title": "東京ばな奈の新商品が話題に", "summary": ""}
        self.assertTrue(is_hard_noise(article))

    def test_starbucks_is_noise(self):
        """ユーザー報告: スタバの新作が混入していた"""
        article = {"title": "スターバックス、新作フラペチーノを発売", "summary": ""}
        self.assertTrue(is_hard_noise(article))

    def test_lifeguard_is_noise(self):
        """ユーザー報告: ライフガードサワーが混入していた"""
        article = {"title": "ライフガードサワー新発売", "summary": ""}
        self.assertTrue(is_hard_noise(article))

    def test_monteil_is_noise(self):
        """ユーザー報告: モンテール5月新商品が混入していた"""
        article = {"title": "モンテール、5月の新商品ラインナップ発表", "summary": ""}
        self.assertTrue(is_hard_noise(article))


class TestNonBabyAgeGroupNoise(unittest.TestCase):
    """ユーザー要望: 対象は 0〜未就学児 まで。中学生以降は除外。"""

    def test_high_school_student_is_noise(self):
        """ユーザー報告: 高校生の支援問題が混入していた"""
        article = {"title": "高校生の支援につながりにくい問題", "summary": ""}
        self.assertTrue(is_hard_noise(article))

    def test_middle_school_is_noise(self):
        article = {"title": "中学生向けの新教材を発表", "summary": ""}
        self.assertTrue(is_hard_noise(article))

    def test_university_is_noise(self):
        article = {"title": "大学生協が新サービス", "summary": ""}
        self.assertTrue(is_hard_noise(article))

    def test_baby_article_not_noise(self):
        """同じ記事に「赤ちゃん」「乳幼児」があれば未就学児外語が無いので noise でない"""
        article = {
            "title": "ピジョン、新型哺乳瓶を発売",
            "summary": "乳幼児向けの授乳サポート機能を強化",
        }
        self.assertFalse(is_hard_noise(article))


class TestImageGalleryNoise(unittest.TestCase):
    def test_image_gallery_is_noise(self):
        article = {"title": "ピジョンの新製品 画像3/34", "summary": ""}
        self.assertTrue(is_hard_noise(article))

    def test_photo_gallery_is_noise(self):
        article = {"title": "新作ベビーカー フォトギャラリー", "summary": ""}
        self.assertTrue(is_hard_noise(article))


class TestRegionalNoise(unittest.TestCase):
    def test_closing_is_noise(self):
        article = {"title": "アカチャンホンポ某店閉店のお知らせ", "summary": ""}
        self.assertTrue(is_hard_noise(article))


class TestFilterByKeywords(unittest.TestCase):
    def test_tokyo_banana_dropped_without_baby_context(self):
        articles = [{
            "title": "東京ばな奈の新商品",
            "summary": "新作スイーツ",
            "matched_keywords": [],
        }]
        result = filter_by_keywords(articles)
        self.assertEqual(len(result), 0)

    def test_pigeon_baby_kept(self):
        articles = [{
            "title": "ピジョンが新型哺乳瓶を発表",
            "summary": "授乳サポート機能を強化",
            "matched_keywords": [],
        }]
        result = filter_by_keywords(articles)
        self.assertEqual(len(result), 1)
        self.assertIn("哺乳瓶", result[0]["matched_keywords"])

    def test_starbucks_uri_age_dropped(self):
        """『市場』『売上』だけの記事はベビー特化語が無いので除外（KEYWORDS["general"] 厳格化）"""
        articles = [{
            "title": "スターバックス、新作で売上前年比20%増",
            "summary": "市場シェアが拡大",
            "matched_keywords": [],
        }]
        result = filter_by_keywords(articles)
        self.assertEqual(len(result), 0)

    def test_general_business_terms_alone_dropped(self):
        """『新製品』『メーカー』『EC』単独ではベビー文脈と判定しない"""
        articles = [{
            "title": "あるメーカーの新製品が売上拡大",
            "summary": "ECサイトで人気",
            "matched_keywords": [],
        }]
        result = filter_by_keywords(articles)
        self.assertEqual(len(result), 0)


class TestOldYearDetection(unittest.TestCase):
    def test_2018_in_title_detected(self):
        article = {"title": "ユニ・チャーム、2018年のおむつ戦略", "summary": ""}
        self.assertTrue(is_old_topic_title(article))

    def test_2018_in_summary_detected(self):
        article = {
            "title": "ユニ・チャームのおむつ戦略",
            "summary": "2018年に発表された同社の中期計画では",
        }
        self.assertTrue(is_old_topic_title(article))

    def test_2026_not_detected_as_old(self):
        article = {"title": "ベビー用品市場の2026年最新動向", "summary": ""}
        self.assertFalse(is_old_topic_title(article))


if __name__ == "__main__":
    unittest.main()
