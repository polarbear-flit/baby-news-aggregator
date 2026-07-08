"""Telegram配信フォーマットのテスト。

要件:
- 配信文に Fact / Why / URL / Action / Source / 軸ラベル / importance が含まれる
- HTML特殊文字がエスケープされる
- importance=Low は配信から除外する設計（送信ロジック側）
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from main import format_article_block, AXIS_LABELS  # noqa: E402


class TestFormatArticleBlock(unittest.TestCase):
    def test_contains_all_required_fields(self):
        article = {
            "title": "ピジョン、新型哺乳瓶発売",
            "url": "https://example.com/news",
            "source_name": "PR TIMES",
            "fact_summary": "ピジョン製哺乳瓶の新シリーズ展開",
            "why_it_matters": "国内主要メーカーの新商品、競合観察必須",
            "action_hint_jp": "競合品との比較表を作成",
            "importance": "High",
            "ai_value_axis": "manufacturer",
        }
        block = format_article_block(1, article)
        self.assertIn("【High】", block)
        self.assertIn("メーカー", block)  # axis label
        self.assertIn("Source:", block)
        self.assertIn("PR TIMES", block)
        self.assertIn("URL:", block)
        self.assertIn("https://example.com/news", block)
        self.assertIn("Fact:", block)
        self.assertIn("ピジョン製哺乳瓶", block)
        self.assertIn("Why:", block)
        self.assertIn("競合観察必須", block)
        self.assertIn("Action:", block)
        self.assertIn("比較表を作成", block)

    def test_html_special_chars_escaped(self):
        article = {
            "title": "A&B<test>",
            "url": "https://example.com/?q=a&b",
            "source_name": "<媒体>",
            "fact_summary": "fact <br>",
            "why_it_matters": "matters & more",
            "action_hint_jp": "",
            "importance": "Medium",
            "ai_value_axis": "retail",
        }
        block = format_article_block(1, article)
        self.assertNotIn("<test>", block)
        self.assertIn("&lt;test&gt;", block)

    def test_axis_label_included(self):
        for axis in [
            "manufacturer",
            "retail",
            "market",
            "consumer_trend",
            "product_launch",
            "industry",
        ]:
            article = {
                "title": "test",
                "url": "",
                "source_name": "src",
                "fact_summary": "",
                "why_it_matters": "",
                "action_hint_jp": "",
                "importance": "Medium",
                "ai_value_axis": axis,
            }
            block = format_article_block(1, article)
            label = AXIS_LABELS.get(axis, axis)
            self.assertIn(label, block, f"{axis} のラベル {label} が出力にない")

    def test_no_url_shows_dash(self):
        article = {
            "title": "テスト",
            "url": "",
            "source_name": "src",
            "fact_summary": "",
            "why_it_matters": "",
            "action_hint_jp": "",
            "importance": "Medium",
            "ai_value_axis": "retail",
        }
        block = format_article_block(1, article)
        self.assertIn("URL: —", block)

    def test_ai_fact_labeled_explicitly(self):
        """fact_source='ai' のときは『Fact (AI要約):』と表示される"""
        article = {
            "title": "テスト",
            "url": "https://example.com",
            "source_name": "PR TIMES",
            "fact_summary": "AI が本文から推測した事実",
            "fact_source": "ai",
            "why_it_matters": "",
            "action_hint_jp": "",
            "importance": "High",
            "ai_value_axis": "manufacturer",
        }
        block = format_article_block(1, article)
        self.assertIn("Fact (AI要約):", block)
        self.assertNotIn(" Fact: ", block)  # 単純な"Fact:" は出ない

    def test_rss_fact_uses_plain_label(self):
        """fact_source='rss' のときは通常の『Fact:』表示"""
        article = {
            "title": "テスト",
            "url": "https://example.com",
            "source_name": "Pigeon 公式",
            "fact_summary": "RSS の summary 本文",
            "fact_source": "rss",
            "why_it_matters": "",
            "action_hint_jp": "",
            "importance": "High",
            "ai_value_axis": "manufacturer",
        }
        block = format_article_block(1, article)
        self.assertIn("Fact: ", block)
        self.assertNotIn("Fact (AI要約)", block)


if __name__ == "__main__":
    unittest.main()
