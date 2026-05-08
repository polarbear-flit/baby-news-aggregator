"""Quality Rubric のテスト。

要件:
- 公式ソース記事が高スコアになる
- 子育て一般コラムが低スコアになる
- 配信文に Fact / Why it matters / URL が含まれる（main.py側のテストと併せて確認）
"""
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
    def test_official_recall_is_5(self):
        """消費者庁リコール等 official_recall は最高スコア5"""
        article = {"source_type": "official_recall"}
        self.assertEqual(derive_source_quality_score(article), 5)

    def test_brand_official_is_4(self):
        article = {"source_type": "brand_official"}
        self.assertEqual(derive_source_quality_score(article), 4)

    def test_pr_wire_is_3(self):
        article = {"source_type": "pr_wire"}
        self.assertEqual(derive_source_quality_score(article), 3)

    def test_seo_media_is_1(self):
        """SEOまとめサイト等は最低スコア1"""
        article = {"source_type": "seo_media"}
        self.assertEqual(derive_source_quality_score(article), 1)

    def test_unknown_source_default_2(self):
        article = {"source_type": "unknown_source"}
        self.assertEqual(derive_source_quality_score(article), 2)


class TestBusinessRelevanceScore(unittest.TestCase):
    def test_safety_axis_is_5(self):
        article = {"ai_value_axis": "safety"}
        self.assertEqual(derive_business_relevance_score(article), 5)

    def test_competitor_axis_is_4(self):
        article = {"ai_value_axis": "competitor"}
        self.assertEqual(derive_business_relevance_score(article), 4)

    def test_noise_axis_is_1(self):
        """ノイズ判定軸は最低スコア1"""
        article = {"ai_value_axis": "noise"}
        self.assertEqual(derive_business_relevance_score(article), 1)

    def test_no_ai_axis_uses_rule_score(self):
        """AI評価が無い場合はルールスコアから推定"""
        article = {"score": 90}
        self.assertEqual(derive_business_relevance_score(article), 4)
        article = {"score": 10}
        self.assertEqual(derive_business_relevance_score(article), 1)


class TestActionabilityScore(unittest.TestCase):
    def test_concrete_long_action_is_5(self):
        """具体的動詞かつ20文字以上は最高スコア5"""
        article = {"action_hint_jp": "対象SKUの取扱有無を全店舗で在庫確認"}
        self.assertEqual(derive_actionability_score(article), 5)

    def test_concrete_short_action_is_4(self):
        article = {"action_hint_jp": "競合品と比較表を作成"}
        self.assertEqual(derive_actionability_score(article), 4)

    def test_no_action_is_1(self):
        article = {"action_hint_jp": ""}
        self.assertEqual(derive_actionability_score(article), 1)
        article = {"action_hint_jp": "特になし"}
        self.assertEqual(derive_actionability_score(article), 1)


class TestComputeImportance(unittest.TestCase):
    def test_high_combined(self):
        """3軸とも高ければ High"""
        self.assertEqual(compute_importance(5, 5, 5), "High")
        self.assertEqual(compute_importance(4, 4, 4), "High")

    def test_medium_combined(self):
        self.assertEqual(compute_importance(3, 3, 3), "Medium")

    def test_low_combined(self):
        self.assertEqual(compute_importance(2, 1, 1), "Low")

    def test_high_relevance_required(self):
        """combined>=4 でも relevance<4 なら Medium 止まり"""
        self.assertEqual(compute_importance(5, 3, 5), "Medium")

    def test_safety_high_score_forced_high(self):
        """safety軸かつ value_score>=80 は強制 High"""
        article = {"ai_value_axis": "safety", "ai_value_score": 90}
        self.assertEqual(compute_importance(2, 2, 2, article), "High")

    def test_link_failed_forced_low(self):
        """link_status=failed は強制 Low"""
        article = {"link_status": "failed"}
        self.assertEqual(compute_importance(5, 5, 5, article), "Low")

    def test_irrelevant_forced_low(self):
        """ai_is_relevant=False は強制 Low"""
        article = {"ai_is_relevant": False}
        self.assertEqual(compute_importance(5, 5, 5, article), "Low")


class TestApplyRubric(unittest.TestCase):
    def test_official_recall_article_becomes_high(self):
        """公式ソースの主要メーカーリコールは High になる"""
        article = {
            "title": "ピジョン哺乳瓶リコール",
            "url": "https://example.com/recall",
            "source_type": "official_recall",
            "ai_value_axis": "safety",
            "ai_value_score": 90,
            "why_matters_jp": "国内主要メーカーのリコール、即在庫確認必須",
            "action_hint_jp": "対象SKUの取扱有無を在庫確認",
            "summary": "消費者庁が哺乳瓶のリコールを公表",
        }
        apply_rubric(article)
        self.assertEqual(article["importance"], "High")
        self.assertEqual(article["source_quality_score"], 5)
        self.assertEqual(article["business_relevance_score"], 5)
        self.assertGreaterEqual(article["actionability_score"], 4)

    def test_kosodate_column_becomes_low(self):
        """子育てコラム（SEO転載）は Low になる"""
        article = {
            "title": "【2026年版】ベビーカーおすすめランキング",
            "url": "https://example.com/ranking",
            "source_type": "seo_media",
            "ai_value_axis": "noise",
            "ai_value_score": 5,
            "ai_is_relevant": False,
            "why_matters_jp": "",
            "action_hint_jp": "",
            "summary": "ランキング記事",
        }
        apply_rubric(article)
        self.assertEqual(article["importance"], "Low")
        self.assertEqual(article["source_quality_score"], 1)
        self.assertEqual(article["business_relevance_score"], 1)
        self.assertEqual(article["actionability_score"], 1)

    def test_required_fields_added(self):
        """apply_rubric後に必須フィールドが揃う"""
        article = {
            "title": "テスト",
            "summary": "サマリ",
            "source_type": "google_news",
        }
        apply_rubric(article)
        for field in [
            "source_quality_score", "business_relevance_score",
            "actionability_score", "importance",
            "fact_summary", "business_implication", "why_it_matters",
        ]:
            self.assertIn(field, article, f"{field} が付与されていない")

    def test_apply_to_all_preserves_count(self):
        articles = [
            {"title": "a", "source_type": "google_news"},
            {"title": "b", "source_type": "official_recall"},
        ]
        result = apply_rubric_to_all(articles)
        self.assertEqual(len(result), 2)


if __name__ == "__main__":
    unittest.main()
