"""AIリランカーのテスト。

要件:
- AI未設定時(ANTHROPIC_API_KEY無し)でもBotは落ちない（フォールバック動作）
- RANK_TOOL に "strict": True が設定されている
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.ai_ranker import RANK_TOOL, ai_rank_articles  # noqa: E402


class TestAIRankerStrict(unittest.TestCase):
    def test_strict_mode_enabled(self):
        """RANK_TOOL に strict=True が設定されていること"""
        self.assertTrue(
            RANK_TOOL.get("strict") is True,
            "RANK_TOOL は strict=True で定義されているべき",
        )

    def test_required_fields_present(self):
        """必須フィールドが揃っていること"""
        item_props = RANK_TOOL["input_schema"]["properties"]["items"]["items"]["properties"]
        for field in [
            "article_id", "is_relevant", "value_score",
            "value_axis", "why_matters_jp", "action_hint_jp",
        ]:
            self.assertIn(field, item_props, f"{field} がスキーマにない")


class TestAIRankerFallback(unittest.TestCase):
    def setUp(self):
        # 一時的に API キーを退避
        self._saved_key = os.environ.pop("ANTHROPIC_API_KEY", None)

    def tearDown(self):
        if self._saved_key is not None:
            os.environ["ANTHROPIC_API_KEY"] = self._saved_key

    def test_no_api_key_returns_input(self):
        """ANTHROPIC_API_KEY 未設定時は入力をそのまま返し、ai_used=False"""
        articles = [
            {"title": "テスト記事", "url": "https://example.com/1", "score": 50},
        ]
        result, ai_used = ai_rank_articles(articles)
        self.assertEqual(result, articles)
        self.assertFalse(ai_used)

    def test_empty_input_returns_empty(self):
        """空入力は空のまま返す"""
        result, ai_used = ai_rank_articles([])
        self.assertEqual(result, [])
        self.assertFalse(ai_used)

    def test_does_not_crash_without_anthropic_lib(self):
        """anthropicが未インストールでもクラッシュしない（フォールバック）

        実際のテストでは anthropic がインストールされている場合もあるが、
        テストの目的は「ai_rank_articles が例外を投げないこと」。
        """
        articles = [{"title": "test", "url": ""}]
        try:
            ai_rank_articles(articles)
        except Exception as e:
            self.fail(f"ai_rank_articles が例外を投げた: {e}")


class TestDiversifyTop(unittest.TestCase):
    """diversify_top で上位 top_n 件の value_axis が偏らないことを確認。"""

    def test_safety_dominated_input_diversifies(self):
        """全件 safety の入力に他軸が混ざっていれば上位は多様化される"""
        from main import diversify_top
        articles = [
            {"title": f"safety_{i}", "ai_value_score": 90 - i, "ai_value_axis": "safety"}
            for i in range(5)
        ] + [
            {"title": "launch_1", "ai_value_score": 70, "ai_value_axis": "product_launch"},
            {"title": "retail_1", "ai_value_score": 65, "ai_value_axis": "retail"},
            {"title": "market_1", "ai_value_score": 60, "ai_value_axis": "market"},
        ]
        result = diversify_top(articles, top_n=5, max_per_axis=2)
        top5_axes = [a["ai_value_axis"] for a in result[:5]]
        # safety は最大2件まで
        self.assertLessEqual(top5_axes.count("safety"), 2, f"top5={top5_axes}")
        # 結果は元の長さを保持
        self.assertEqual(len(result), len(articles))

    def test_no_change_when_already_diverse(self):
        """もともと多様なら順序変更なし"""
        from main import diversify_top
        articles = [
            {"title": "a", "ai_value_score": 90, "ai_value_axis": "safety"},
            {"title": "b", "ai_value_score": 85, "ai_value_axis": "product_launch"},
            {"title": "c", "ai_value_score": 80, "ai_value_axis": "retail"},
            {"title": "d", "ai_value_score": 75, "ai_value_axis": "market"},
            {"title": "e", "ai_value_score": 70, "ai_value_axis": "competitor"},
        ]
        result = diversify_top(articles, top_n=5, max_per_axis=2)
        self.assertEqual([a["title"] for a in result], ["a", "b", "c", "d", "e"])

    def test_safety_axis_capped_at_one(self):
        """デフォルトでは safety/regulation は最大1件まで（リコール一色防止）"""
        from main import diversify_top
        articles = [
            {"title": f"safety_{i}", "ai_value_score": 95 - i, "ai_value_axis": "safety"}
            for i in range(3)
        ] + [
            {"title": f"reg_{i}", "ai_value_score": 80 - i, "ai_value_axis": "regulation"}
            for i in range(2)
        ] + [
            {"title": "launch_1", "ai_value_score": 70, "ai_value_axis": "product_launch"},
            {"title": "retail_1", "ai_value_score": 65, "ai_value_axis": "retail"},
            {"title": "market_1", "ai_value_score": 60, "ai_value_axis": "market"},
        ]
        result = diversify_top(articles, top_n=5)
        top5_axes = [a["ai_value_axis"] for a in result[:5]]
        # safety と regulation はそれぞれ最大1件
        self.assertEqual(top5_axes.count("safety"), 1, f"top5={top5_axes}")
        self.assertEqual(top5_axes.count("regulation"), 1, f"top5={top5_axes}")


if __name__ == "__main__":
    unittest.main()
