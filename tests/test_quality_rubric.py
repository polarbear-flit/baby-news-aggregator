"""Quality Rubric のテスト — 業界動向特化版。"""
import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.quality_rubric import (  # noqa: E402
    apply_rubric,
    apply_rubric_to_all,
    compute_importance,
    derive_actionability_score,
    derive_business_relevance_score,
    derive_source_quality_score,
)


class TestSourceQualityScore(unittest.TestCase):
    def test_brand_official_is_5(self):
        self.assertEqual(derive_source_quality_score({"source_type": "brand_official"}), 5)

    def test_market_research_is_5(self):
        self.assertEqual(derive_source_quality_score({"source_type": "market_research"}), 5)

    def test_pr_wire_is_3(self):
        self.assertEqual(derive_source_quality_score({"source_type": "pr_wire"}), 3)

    def test_seo_media_is_1(self):
        self.assertEqual(derive_source_quality_score({"source_type": "seo_media"}), 1)


class TestBusinessRelevanceScore(unittest.TestCase):
    def test_manufacturer_is_5(self):
        self.assertEqual(derive_business_relevance_score({"ai_value_axis": "manufacturer"}), 5)

    def test_retail_is_5(self):
        self.assertEqual(derive_business_relevance_score({"ai_value_axis": "retail"}), 5)

    def test_market_is_4(self):
        self.assertEqual(derive_business_relevance_score({"ai_value_axis": "market"}), 4)

    def test_noise_is_1(self):
        self.assertEqual(derive_business_relevance_score({"ai_value_axis": "noise"}), 1)


class TestActionabilityScore(unittest.TestCase):
    def test_concrete_long_action_is_5(self):
        article = {"action_hint_jp": "対象SKUの取扱有無を全店舗で在庫確認"}
        self.assertEqual(derive_actionability_score(article), 5)

    def test_concrete_short_action_is_4(self):
        article = {"action_hint_jp": "競合品と比較表を作成"}
        self.assertEqual(derive_actionability_score(article), 4)

    def test_no_action_is_1(self):
        self.assertEqual(derive_actionability_score({"action_hint_jp": ""}), 1)
        self.assertEqual(derive_actionability_score({"action_hint_jp": "特になし"}), 1)


class TestComputeImportance(unittest.TestCase):
    """閾値: High >= 3.5 + relevance>=4 / Medium >= 2.5 / Low それ以外"""

    def test_high_combined(self):
        self.assertEqual(compute_importance(5, 5, 5), "High")
        self.assertEqual(compute_importance(4, 4, 4), "High")
        # 業界焦点ソース追加で source_q=4, relevance=4, action=3 などが High に届く
        self.assertEqual(compute_importance(4, 4, 3), "High")  # combined=3.67

    def test_medium_combined(self):
        self.assertEqual(compute_importance(3, 3, 3), "Medium")
        self.assertEqual(compute_importance(2, 4, 3), "Medium")  # combined=3.0

    def test_low_combined(self):
        self.assertEqual(compute_importance(2, 1, 1), "Low")
        self.assertEqual(compute_importance(1, 2, 2), "Low")  # combined=1.67

    def test_high_relevance_required(self):
        """combined>=3.5 でも relevance<4 なら Medium 止まり"""
        self.assertEqual(compute_importance(5, 3, 5), "Medium")

    def test_link_failed_forced_low(self):
        article = {"link_status": "failed"}
        self.assertEqual(compute_importance(5, 5, 5, article), "Low")

    def test_irrelevant_forced_low(self):
        article = {"ai_is_relevant": False}
        self.assertEqual(compute_importance(5, 5, 5, article), "Low")

    def test_no_safety_forced_high_rule(self):
        """旧版の「safety×80+ → 強制 High」は撤廃されている"""
        article = {"ai_value_axis": "manufacturer", "ai_value_score": 90}
        # combined=2.0 < 2.5 なので Low
        result = compute_importance(2, 2, 2, article)
        self.assertEqual(result, "Low")


class TestApplyRubric(unittest.TestCase):
    def test_manufacturer_high_score_becomes_high(self):
        """主要メーカー公式の重要発表は High"""
        article = {
            "title": "ピジョン、新型哺乳瓶発売",
            "url": "https://example.com/news",
            "source_type": "brand_official",
            "ai_value_axis": "manufacturer",
            "ai_value_score": 90,
            "why_matters_jp": "国内主要メーカーの新商品、競合観察必須",
            "action_hint_jp": "競合品との比較表を作成",
            "summary": "ピジョンが新型哺乳瓶を発売",
        }
        apply_rubric(article)
        self.assertEqual(article["importance"], "High")
        self.assertEqual(article["source_quality_score"], 5)
        self.assertEqual(article["business_relevance_score"], 5)

    def test_seo_ranking_becomes_low(self):
        """SEOランキング系は Low"""
        article = {
            "title": "ベビーカーおすすめランキング",
            "url": "https://example.com/ranking",
            "source_type": "seo_media",
            "ai_value_axis": "noise",
            "ai_is_relevant": False,
            "why_matters_jp": "",
            "action_hint_jp": "",
            "summary": "",
        }
        apply_rubric(article)
        self.assertEqual(article["importance"], "Low")
        self.assertEqual(article["source_quality_score"], 1)
        self.assertEqual(article["business_relevance_score"], 1)

    def test_required_fields_added(self):
        article = {"title": "テスト", "summary": "サマリ", "source_type": "google_news"}
        apply_rubric(article)
        for field in [
            "source_quality_score", "business_relevance_score",
            "actionability_score", "importance",
            "fact_summary", "fact_source",
            "business_implication", "why_it_matters",
        ]:
            self.assertIn(field, article)

    def test_apply_to_all_preserves_count(self):
        articles = [
            {"title": "a", "source_type": "google_news"},
            {"title": "b", "source_type": "brand_official"},
        ]
        result = apply_rubric_to_all(articles)
        self.assertEqual(len(result), 2)


class TestFactSourceLabeling(unittest.TestCase):
    """Implementation Quality Rubric §4 (Data Consistency):
    AI 生成の事実要約と RSS 事実データを fact_source で区別する。

    UIで「Fact (AI要約):」と「Fact:」を表示分けして、ユーザーが
    AI推測と元記事の事実を判別できるようにする。
    """

    def test_fact_source_ai_when_ai_fact_present(self):
        article = {
            "title": "テスト",
            "summary": "RSS本文",
            "ai_fact_summary": "AIが本文から要約した事実",
            "source_type": "google_news",
        }
        apply_rubric(article)
        self.assertEqual(article["fact_source"], "ai")
        self.assertIn("AIが本文から要約", article["fact_summary"])

    def test_fact_source_rss_when_no_ai(self):
        article = {
            "title": "テスト",
            "summary": "RSS本文",
            "source_type": "google_news",
        }
        apply_rubric(article)
        self.assertEqual(article["fact_source"], "rss")
        self.assertEqual(article["fact_summary"], "RSS本文")

    def test_fact_source_title_when_no_summary(self):
        article = {
            "title": "タイトルだけ",
            "summary": "",
            "source_type": "google_news",
        }
        apply_rubric(article)
        self.assertEqual(article["fact_source"], "title")
        self.assertEqual(article["fact_summary"], "タイトルだけ")

    def test_empty_ai_fact_falls_back_to_rss(self):
        """ai_fact_summary が空白だけの場合は RSS にフォールバック"""
        article = {
            "title": "T",
            "summary": "RSS",
            "ai_fact_summary": "   ",
            "source_type": "google_news",
        }
        apply_rubric(article)
        self.assertEqual(article["fact_source"], "rss")


if __name__ == "__main__":
    unittest.main()
