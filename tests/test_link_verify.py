"""リンク検証のテスト。

要件:
- URLが無効な記事を検出できる
- 配信に乗る上位だけ検証される（コスト管理）

ネットワーク呼び出しは requests.head/get をモックして再現性を担保する。
"""
import os
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.fetcher import verify_link, verify_links_batch  # noqa: E402


class _FakeResp:
    def __init__(self, status_code: int):
        self.status_code = status_code

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


class TestVerifyLink(unittest.TestCase):
    def test_empty_url_returns_skipped(self):
        self.assertEqual(verify_link(""), "skipped")
        self.assertEqual(verify_link(None), "skipped")  # type: ignore[arg-type]

    def test_2xx_returns_ok(self):
        with patch("src.fetcher.requests.head", return_value=_FakeResp(200)):
            self.assertEqual(verify_link("https://example.com/ok"), "ok")

    def test_3xx_returns_ok(self):
        with patch("src.fetcher.requests.head", return_value=_FakeResp(302)):
            self.assertEqual(verify_link("https://example.com/redirect"), "ok")

    def test_404_returns_failed(self):
        # HEAD 4xx → GET でも 4xx → failed
        with patch("src.fetcher.requests.head", return_value=_FakeResp(404)):
            with patch("src.fetcher.requests.get", return_value=_FakeResp(404)):
                self.assertEqual(verify_link("https://example.com/notfound"), "failed")

    def test_head_405_get_200_returns_ok(self):
        """Google News のような HEAD 405 でも GET 200 なら ok"""
        # HEAD 405 → GET 200 → ok
        with patch("src.fetcher.requests.head", return_value=_FakeResp(405)):
            with patch("src.fetcher.requests.get", return_value=_FakeResp(200)):
                self.assertEqual(verify_link("https://news.google.com/articles/xyz"), "ok")

    def test_connection_error_returns_failed(self):
        with patch("src.fetcher.requests.head", side_effect=ConnectionError("boom")):
            with patch("src.fetcher.requests.get", side_effect=ConnectionError("boom")):
                self.assertEqual(verify_link("https://offline.example/"), "failed")


class TestVerifyLinksBatch(unittest.TestCase):
    def test_only_top_n_verified(self):
        """先頭 max_count 件のみ検証され、それ以外は link_status=skipped"""
        articles = [{"url": f"https://example.com/{i}"} for i in range(10)]
        with patch("src.fetcher.verify_link", return_value="ok") as m:
            verify_links_batch(articles, max_count=3)
        # 検証されたのは先頭3件
        self.assertEqual(m.call_count, 3)
        # 上位3件は ok、残りは skipped
        for a in articles[:3]:
            self.assertEqual(a["link_status"], "ok")
        for a in articles[3:]:
            self.assertEqual(a["link_status"], "skipped")

    def test_failed_status_set_on_invalid(self):
        articles = [{"url": "https://invalid.example/"}]
        with patch("src.fetcher.verify_link", return_value="failed"):
            verify_links_batch(articles, max_count=5)
        self.assertEqual(articles[0]["link_status"], "failed")


if __name__ == "__main__":
    unittest.main()
