"""配信済み記憶（cross-day dedup）のテスト — AC-1/AC-2 の機械判定。"""

import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.delivered import (  # noqa: E402
    is_already_delivered,
    prune_delivered,
    split_by_delivery,
    upsert_delivered,
)


class TestIsAlreadyDelivered(unittest.TestCase):
    def test_same_url_is_redelivery(self):
        store = {
            "articles": [
                {
                    "url_norm": "https://example.com/a",
                    "title_norm": "x",
                    "cluster_key": "",
                    "last_delivered": "2026-07-07",
                }
            ]
        }
        art = {"url": "https://example.com/a/", "title": "全然違うタイトル"}
        self.assertTrue(is_already_delivered(art, store))

    def test_similar_title_is_redelivery(self):
        store = {
            "articles": [
                {
                    "url_norm": "u1",
                    "title_norm": "アップリカクルリラビッテエックスプラスac発売",
                    "cluster_key": "",
                    "last_delivered": "2026-07-07",
                }
            ]
        }
        art = {
            "url": "https://other.example/b",
            "title": "アップリカ「クルリラ ビッテ エックス プラス AC」発売！",
        }
        self.assertTrue(is_already_delivered(art, store))

    def test_fresh_article_passes(self):
        store = {"articles": []}
        art = {"url": "https://example.com/new", "title": "コンビが新工場を建設"}
        self.assertFalse(is_already_delivered(art, store))

    def test_cluster_key_match_is_redelivery(self):
        """別媒体版（タイトルは大きく違うがクラスタ代表が一致）を捕捉。"""
        store = {
            "articles": [
                {
                    "url_norm": "u1",
                    "title_norm": "全然別の文字列zzz",
                    "cluster_key": "アロベビーベビーソープ無香タイプ新登場",
                    "last_delivered": "2026-07-07",
                }
            ]
        }
        art = {
            "url": "https://wire.example/c",
            "title": "別タイトル",
            "cluster_key": "アロベビーベビーソープ無香タイプ新登場",
        }
        self.assertTrue(is_already_delivered(art, store))


class TestSplitByDelivery(unittest.TestCase):
    def test_split_marks_flags(self):
        store = {
            "articles": [
                {
                    "url_norm": "https://example.com/seen",
                    "title_norm": "既報記事",
                    "cluster_key": "",
                    "last_delivered": "2026-07-07",
                }
            ]
        }
        articles = [
            {"url": "https://example.com/seen", "title": "既報記事"},
            {"url": "https://example.com/new", "title": "新着のニュース"},
        ]
        fresh, redelivered = split_by_delivery(articles, store)
        self.assertEqual(len(fresh), 1)
        self.assertEqual(len(redelivered), 1)
        self.assertTrue(redelivered[0]["redelivery"])
        self.assertFalse(fresh[0]["redelivery"])


class TestUpsertDelivered(unittest.TestCase):
    def test_new_article_added(self):
        store = {"articles": []}
        upsert_delivered(
            store,
            [
                {"url": "https://example.com/x", "title": "新商品発表"},
            ],
            today="2026-07-08",
        )
        self.assertEqual(len(store["articles"]), 1)
        rec = store["articles"][0]
        self.assertEqual(rec["first_seen"], "2026-07-08")
        self.assertEqual(rec["delivered_count"], 1)

    def test_existing_article_bumps_count(self):
        store = {"articles": []}
        art = {"url": "https://example.com/x", "title": "新商品発表"}
        upsert_delivered(store, [art], today="2026-07-08")
        upsert_delivered(store, [art], today="2026-07-09")
        self.assertEqual(len(store["articles"]), 1)
        self.assertEqual(store["articles"][0]["delivered_count"], 2)
        self.assertEqual(store["articles"][0]["last_delivered"], "2026-07-09")


class TestPruneDelivered(unittest.TestCase):
    def test_prune_removes_old_records(self):
        store = {
            "articles": [
                {
                    "url_norm": "u",
                    "title_norm": "t",
                    "cluster_key": "",
                    "last_delivered": "2026-05-01",
                }
            ]
        }
        pruned = prune_delivered(store, today="2026-07-08", keep_days=30)
        self.assertEqual(len(pruned["articles"]), 0)

    def test_prune_keeps_recent_records(self):
        store = {
            "articles": [
                {
                    "url_norm": "u",
                    "title_norm": "t",
                    "cluster_key": "",
                    "last_delivered": "2026-07-05",
                }
            ]
        }
        pruned = prune_delivered(store, today="2026-07-08", keep_days=30)
        self.assertEqual(len(pruned["articles"]), 1)


if __name__ == "__main__":
    unittest.main()
