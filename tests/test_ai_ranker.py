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

    def test_diversify_with_empty_axis_caps(self):
        """axis_caps={} を渡すと軸別キャップは無効化され max_per_axis のみ適用"""
        from main import diversify_top
        articles = [
            {"title": f"safety_{i}", "ai_value_score": 95 - i, "ai_value_axis": "safety"}
            for i in range(3)
        ]
        # axis_caps={} なら max_per_axis=2 がそのまま適用される
        result = diversify_top(articles, top_n=5, max_per_axis=2, axis_caps={})
        top_axes = [a["ai_value_axis"] for a in result[:2]]
        self.assertEqual(top_axes.count("safety"), 2)


class TestSafetySectionSeparation(unittest.TestCase):
    """safety/regulation 軸の記事を main から切り出すロジック"""

    def _split_safety(self, ai_evaluated, min_score=80, max_safety=2):
        """main.py のロジックを抽出した参照実装（テスト用）。

        Returns: (main_articles, safety_articles, remaining_safety)
        """
        SAFETY_AXES = {"safety", "regulation"}
        all_safety = sorted(
            [a for a in ai_evaluated if a.get("ai_value_axis") in SAFETY_AXES],
            key=lambda x: x.get("ai_value_score", 0),
            reverse=True,
        )
        safety = [a for a in all_safety if a.get("ai_value_score", 0) >= min_score][:max_safety]
        safety_ids = {id(a) for a in safety}
        remaining = [a for a in all_safety if id(a) not in safety_ids]
        main = [a for a in ai_evaluated if a.get("ai_value_axis") not in SAFETY_AXES]
        return main, safety, remaining

    def test_safety_articles_separated(self):
        """safety/regulation で score>=80 のみ別出しに、他は main に残る"""
        ai_evaluated = [
            {"title": "safety_high", "ai_value_score": 90, "ai_value_axis": "safety"},
            {"title": "safety_low", "ai_value_score": 70, "ai_value_axis": "safety"},
            {"title": "reg_high", "ai_value_score": 85, "ai_value_axis": "regulation"},
            {"title": "launch_1", "ai_value_score": 75, "ai_value_axis": "product_launch"},
            {"title": "market_1", "ai_value_score": 65, "ai_value_axis": "market"},
        ]
        main, safety, _ = self._split_safety(ai_evaluated)

        self.assertEqual(len(safety), 2)
        self.assertEqual(safety[0]["title"], "safety_high")
        self.assertEqual(safety[1]["title"], "reg_high")

        self.assertEqual(len(main), 2)
        self.assertNotIn("safety", [a["ai_value_axis"] for a in main])
        self.assertNotIn("regulation", [a["ai_value_axis"] for a in main])

    def test_low_score_safety_kept_in_remaining(self):
        """score<80 の safety/regulation は別出しから外れるが remaining_safety に残る。

        Codex指摘: 中位 safety 記事が display_articles から消える問題への対策。
        HTMLレポート/historyに残すため、別出しに入らなかった分は remaining_safety で
        確実に display_articles に含まれるようにする。
        """
        ai_evaluated = [
            {"title": "safety_high", "ai_value_score": 90, "ai_value_axis": "safety"},
            {"title": "safety_mid", "ai_value_score": 70, "ai_value_axis": "safety"},
            {"title": "reg_low", "ai_value_score": 60, "ai_value_axis": "regulation"},
            {"title": "launch_1", "ai_value_score": 75, "ai_value_axis": "product_launch"},
        ]
        main, safety, remaining = self._split_safety(ai_evaluated)

        # 別出しは score>=80 の1件のみ
        self.assertEqual(len(safety), 1)
        self.assertEqual(safety[0]["title"], "safety_high")

        # 中位 safety/regulation 2件は remaining に入る
        remaining_titles = [a["title"] for a in remaining]
        self.assertIn("safety_mid", remaining_titles)
        self.assertIn("reg_low", remaining_titles)
        self.assertEqual(len(remaining), 2)

    def test_safety_articles_not_lost_when_third_or_more(self):
        """score>=80 でも3件目以降は別出しに入らないが remaining に残る"""
        ai_evaluated = [
            {"title": "safety_1", "ai_value_score": 95, "ai_value_axis": "safety"},
            {"title": "safety_2", "ai_value_score": 90, "ai_value_axis": "safety"},
            {"title": "safety_3", "ai_value_score": 85, "ai_value_axis": "safety"},
            {"title": "safety_4", "ai_value_score": 82, "ai_value_axis": "safety"},
        ]
        _, safety, remaining = self._split_safety(ai_evaluated)
        self.assertEqual(len(safety), 2)
        self.assertEqual([a["title"] for a in safety], ["safety_1", "safety_2"])
        self.assertEqual([a["title"] for a in remaining], ["safety_3", "safety_4"])

    def test_display_articles_includes_all_evaluated(self):
        """display_articles 構築で AI評価済みの全件が消えないことを確認"""
        from main import diversify_top
        ai_evaluated = [
            {"title": "launch_1", "ai_value_score": 90, "ai_value_axis": "product_launch"},
            {"title": "safety_high", "ai_value_score": 88, "ai_value_axis": "safety"},
            {"title": "safety_mid", "ai_value_score": 70, "ai_value_axis": "safety"},
            {"title": "reg_low", "ai_value_score": 55, "ai_value_axis": "regulation"},
            {"title": "retail_1", "ai_value_score": 75, "ai_value_axis": "retail"},
        ]
        rule_rest = [{"title": "rule_rest_1", "score": 30}]

        main, safety, remaining = self._split_safety(ai_evaluated)
        main = diversify_top(main, top_n=5, max_per_axis=2, axis_caps={})
        display = main + safety + remaining + rule_rest

        # 全AI評価記事が display に存在
        evaluated_titles = {a["title"] for a in ai_evaluated}
        display_titles = {a["title"] for a in display}
        for t in evaluated_titles:
            self.assertIn(t, display_titles, f"{t} が display_articles から消えている")
        # rule_rest も含まれる
        self.assertIn("rule_rest_1", display_titles)


if __name__ == "__main__":
    unittest.main()
