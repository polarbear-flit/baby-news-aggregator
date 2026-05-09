"""AIリランカーのテスト — 業界動向特化版。

要件:
- AI未設定でもBotは落ちない
- RANK_TOOL に "strict": True
- value_axis enum が業界動向7軸（safety/regulation を含まない）
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.ai_ranker import RANK_TOOL, ai_rank_articles  # noqa: E402


class TestAIRankerStrict(unittest.TestCase):
    def test_strict_mode_enabled(self):
        self.assertTrue(RANK_TOOL.get("strict") is True)

    def test_value_axis_industry_focused(self):
        """value_axis enum が業界動向7軸であること（safety/regulation を含まない）"""
        item_props = RANK_TOOL["input_schema"]["properties"]["items"]["items"]["properties"]
        axis_enum = item_props["value_axis"]["enum"]
        for axis in ["manufacturer", "retail", "market", "consumer_trend",
                     "product_launch", "industry", "noise"]:
            self.assertIn(axis, axis_enum, f"{axis} が enum にない")
        self.assertNotIn("safety", axis_enum)
        self.assertNotIn("regulation", axis_enum)

    def test_required_fields_present(self):
        item_props = RANK_TOOL["input_schema"]["properties"]["items"]["items"]["properties"]
        for field in [
            "article_id", "is_relevant", "value_score",
            "value_axis", "fact_summary_jp", "why_matters_jp", "action_hint_jp",
        ]:
            self.assertIn(field, item_props)

    def test_fact_summary_in_required(self):
        """fact_summary_jp が required に入っていること（薄いRSSサマリの代替）"""
        required = RANK_TOOL["input_schema"]["properties"]["items"]["items"]["required"]
        self.assertIn("fact_summary_jp", required)


class TestAIRankerFallback(unittest.TestCase):
    def setUp(self):
        self._saved_key = os.environ.pop("ANTHROPIC_API_KEY", None)

    def tearDown(self):
        if self._saved_key is not None:
            os.environ["ANTHROPIC_API_KEY"] = self._saved_key

    def test_no_api_key_returns_input(self):
        articles = [{"title": "テスト記事", "url": "https://example.com/1", "score": 50}]
        result, ai_used = ai_rank_articles(articles)
        self.assertEqual(result, articles)
        self.assertFalse(ai_used)

    def test_empty_input_returns_empty(self):
        result, ai_used = ai_rank_articles([])
        self.assertEqual(result, [])
        self.assertFalse(ai_used)

    def test_does_not_crash(self):
        articles = [{"title": "test", "url": ""}]
        try:
            ai_rank_articles(articles)
        except Exception as e:
            self.fail(f"ai_rank_articles が例外を投げた: {e}")


class TestDiversifyTop(unittest.TestCase):
    def test_manufacturer_dominated_input_diversifies(self):
        """主要動向が manufacturer 一色でも、他軸が混ざっていれば top5 に含まれる。"""
        from main import diversify_top
        articles = [
            {"title": f"mfr_{i}", "ai_value_score": 90 - i, "ai_value_axis": "manufacturer"}
            for i in range(5)
        ] + [
            {"title": "retail_1", "ai_value_score": 70, "ai_value_axis": "retail"},
            {"title": "retail_2", "ai_value_score": 68, "ai_value_axis": "retail"},
            {"title": "market_1", "ai_value_score": 65, "ai_value_axis": "market"},
            {"title": "market_2", "ai_value_score": 62, "ai_value_axis": "market"},
        ]
        result = diversify_top(articles, top_n=5, max_per_axis=2)
        top5_axes = [a["ai_value_axis"] for a in result[:5]]
        # cap=2 が満たせる十分な多様性があれば 2 件に収まる
        self.assertLessEqual(top5_axes.count("manufacturer"), 2)
        self.assertEqual(len(result), len(articles))

    def test_no_change_when_already_diverse(self):
        from main import diversify_top
        articles = [
            {"title": "a", "ai_value_score": 90, "ai_value_axis": "manufacturer"},
            {"title": "b", "ai_value_score": 85, "ai_value_axis": "retail"},
            {"title": "c", "ai_value_score": 80, "ai_value_axis": "market"},
            {"title": "d", "ai_value_score": 75, "ai_value_axis": "consumer_trend"},
            {"title": "e", "ai_value_score": 70, "ai_value_axis": "product_launch"},
        ]
        result = diversify_top(articles, top_n=5, max_per_axis=2)
        self.assertEqual([a["title"] for a in result], ["a", "b", "c", "d", "e"])


if __name__ == "__main__":
    unittest.main()
