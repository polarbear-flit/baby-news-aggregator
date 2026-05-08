"""Telegram配信フォーマットのテスト。

要件:
- 配信文に Fact / Why it matters / URL が含まれる（Rubric準拠）
- High はフルブロック、Medium は1行に圧縮
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from main import format_high_block, format_medium_line  # noqa: E402


class TestHighBlockFormat(unittest.TestCase):
    def test_contains_fact_why_url(self):
        """High ブロックに Fact / Why it matters / URL が含まれる"""
        article = {
            "title": "ピジョン哺乳瓶リコール",
            "url": "https://example.com/recall",
            "source_name": "消費者庁リコール",
            "fact_summary": "ピジョン製の哺乳瓶でガラス片混入の疑い",
            "why_it_matters": "国内主要メーカー、即在庫確認必須",
            "action_hint_jp": "対象SKUの取扱有無を在庫確認",
        }
        block = format_high_block(article)
        self.assertIn("【High】", block)
        self.assertIn("Source:", block)
        self.assertIn("消費者庁リコール", block)
        self.assertIn("URL:", block)
        self.assertIn("https://example.com/recall", block)
        self.assertIn("Fact:", block)
        self.assertIn("ピジョン製の哺乳瓶でガラス片混入", block)
        self.assertIn("Why it matters:", block)
        self.assertIn("即在庫確認必須", block)
        self.assertIn("Action hint:", block)
        self.assertIn("在庫確認", block)

    def test_no_url_shows_dash(self):
        """URLが空でもブロックは生成され、URL欄は—になる"""
        article = {
            "title": "テスト",
            "url": "",
            "source_name": "テスト媒体",
            "fact_summary": "",
            "why_it_matters": "",
            "action_hint_jp": "",
        }
        block = format_high_block(article)
        self.assertIn("URL: —", block)

    def test_html_special_chars_escaped(self):
        """記事に < や & が含まれていても安全にエスケープされる"""
        article = {
            "title": "A&B<test>",
            "url": "https://example.com/?q=a&b",
            "source_name": "<媒体>",
            "fact_summary": "fact <br>",
            "why_it_matters": "matters & more",
            "action_hint_jp": "",
        }
        block = format_high_block(article)
        # &lt; / &amp; などにエスケープされていること
        self.assertNotIn("<test>", block)  # 生の<test>は無い
        self.assertIn("&lt;test&gt;", block)


class TestMediumLineFormat(unittest.TestCase):
    def test_contains_index_title_source(self):
        """Medium 行は index・タイトル・ソース・scoreを含む"""
        article = {
            "title": "ピジョン新商品発売",
            "url": "https://example.com/news",
            "source_name": "GNews: 哺乳瓶・授乳",
            "ai_value_score": 65,
        }
        line = format_medium_line(1, article)
        self.assertIn("【Medium】", line)
        self.assertIn("1.", line)
        self.assertIn("ピジョン新商品発売", line)
        self.assertIn("GNews", line)
        self.assertIn("65", line)


if __name__ == "__main__":
    unittest.main()
