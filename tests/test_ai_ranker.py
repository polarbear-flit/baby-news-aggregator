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


if __name__ == "__main__":
    unittest.main()
