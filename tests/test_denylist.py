"""ドメインdenylist・鮮度・キーワード穴修正のテスト — AC-4/AC-5。"""

import os
import sys
import unittest
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.config import KEYWORDS, MAX_ARTICLES_PER_FEED  # noqa: E402
from src.fetcher import (  # noqa: E402
    MAX_ARTICLE_AGE_DAYS,
    filter_by_keywords,
    is_denylisted,
    is_seo_market_report,
    is_too_old,
)


class TestDenylist(unittest.TestCase):
    def test_denylisted_domain_in_url(self):
        art = {
            "title": "P&Gの調査",
            "url": "https://richardajkeys.com/x",
            "source_name": "",
        }
        self.assertTrue(is_denylisted(art))

    def test_denylisted_by_trailing_media_name(self):
        # Google News のリダイレクトURLでも、タイトル末尾の媒体名で捕捉
        art = {
            "title": "おしゃぶりの市場規模、シェア、2034 - Fortune Business Insights",
            "url": "https://news.google.com/articles/xyz",
            "source_name": "Fortune Business Insights",
        }
        self.assertTrue(is_denylisted(art))

    def test_mybest_ranking_denied(self):
        art = {
            "title": "カトージのベビーカーおすすめ人気ランキング - マイベスト",
            "url": "https://my-best.com/123",
            "source_name": "マイベスト",
        }
        self.assertTrue(is_denylisted(art))

    def test_legit_article_not_denied(self):
        art = {
            "title": "コンビが新チャイルドシートを発売 - PR TIMES",
            "url": "https://prtimes.jp/x",
            "source_name": "PR TIMES",
        }
        self.assertFalse(is_denylisted(art))


class TestSeoMarketReport(unittest.TestCase):
    def test_future_year_range_forecast_rejected(self):
        art = {
            "title": "ベビーベッド市場：製品タイプ別―2026年～2032年の世界市場予測",
            "summary": "",
        }
        self.assertTrue(is_seo_market_report(art))

    def test_ai_monitor_2032_rejected(self):
        art = {
            "title": "AIベビーモニターの世界市場（2026年～2032年）分析レポート",
            "summary": "",
        }
        self.assertTrue(is_seo_market_report(art))

    def test_million_usd_cagr_rejected(self):
        art = {
            "title": "HMO乳児用ミルク市場分析レポート：2026年4649百万米ドル、成長率10.8%",
            "summary": "",
        }
        self.assertTrue(is_seo_market_report(art))

    def test_domestic_survey_not_rejected(self):
        """正規の国内調査は誤爆しないこと。"""
        art = {
            "title": "ベビー関連ビジネス市場に関する調査を実施（2026年）",
            "summary": "",
        }
        self.assertFalse(is_seo_market_report(art))

    def test_normal_product_news_not_rejected(self):
        art = {
            "title": "ピジョンが新型哺乳瓶を11月発売",
            "summary": "授乳サポート機能を強化",
        }
        self.assertFalse(is_seo_market_report(art))


class TestFreshnessWindow(unittest.TestCase):
    def test_window_is_14_days(self):
        self.assertEqual(MAX_ARTICLE_AGE_DAYS, 14)

    def test_old_article_rejected(self):
        old = datetime.now(timezone.utc) - timedelta(days=30)
        self.assertTrue(is_too_old({"published_dt": old}))

    def test_recent_article_kept(self):
        recent = datetime.now(timezone.utc) - timedelta(days=3)
        self.assertFalse(is_too_old({"published_dt": recent}))

    def test_unknown_date_kept(self):
        self.assertFalse(is_too_old({"published_dt": None}))


class TestKeywordHoleFix(unittest.TestCase):
    def test_bare_baby_keyword_present(self):
        self.assertIn("ベビー", KEYWORDS["general"])

    def test_baby_related_market_survey_passes(self):
        """「ベビー関連ビジネス市場調査」が拾えること（旧版で落ちていた最高価値記事）。"""
        art = {
            "title": "ベビー関連ビジネス市場に関する調査を実施（2026年）",
            "summary": "",
            "matched_keywords": [],
        }
        result = filter_by_keywords([art])
        self.assertEqual(len(result), 1)

    def test_kodomo_yohin_passes(self):
        art = {
            "title": "しまむら、ベビー・子ども用品「バースデイ」EC開設",
            "summary": "",
            "matched_keywords": [],
        }
        result = filter_by_keywords([art])
        self.assertEqual(len(result), 1)


class TestPerFeedMaxArticles(unittest.TestCase):
    def test_default_max_articles_unchanged(self):
        self.assertEqual(MAX_ARTICLES_PER_FEED, 20)


if __name__ == "__main__":
    unittest.main()
