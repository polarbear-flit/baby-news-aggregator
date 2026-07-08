"""クラスタ重複除去のテスト — AC-3（同一PRはハイライトに1件まで）。"""

import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.ai_ranker import dedupe_by_cluster  # noqa: E402


class TestDedupeByCluster(unittest.TestCase):
    def test_same_cluster_only_one_representative(self):
        articles = [
            {
                "title": "ALOBABY無香 - PR TIMES",
                "ai_cluster_id": 5,
                "ai_value_score": 90,
            },
            {
                "title": "ALOBABY無香 - 共同通信",
                "ai_cluster_id": 5,
                "ai_value_score": 25,
            },
            {"title": "コンビ新CS", "ai_cluster_id": 2, "ai_value_score": 80},
        ]
        result = dedupe_by_cluster(articles)
        # 代表が先頭、重複は末尾へ降格
        reps = [a for a in result if not a.get("cluster_duplicate")]
        dups = [a for a in result if a.get("cluster_duplicate")]
        self.assertEqual(len(reps), 2)
        self.assertEqual(len(dups), 1)
        # 上位2件（ハイライト候補）にクラスタ5は1件だけ
        top2 = result[:2]
        cluster_ids_top = [a["ai_cluster_id"] for a in top2]
        self.assertEqual(cluster_ids_top.count(5), 1)

    def test_no_cluster_id_treated_independently(self):
        articles = [
            {"title": "A", "ai_value_score": 90},
            {"title": "B", "ai_value_score": 80},
        ]
        result = dedupe_by_cluster(articles)
        self.assertEqual(len(result), 2)
        self.assertFalse(any(a.get("cluster_duplicate") for a in result))


if __name__ == "__main__":
    unittest.main()
