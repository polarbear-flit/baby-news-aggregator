"""直近N日のgit履歴から docs/index.html の上位記事重複率を計測する。

AC-1（連続2日の配信で同一/類似タイトルが0件）の自動判定に使う。
連続するコミット間で「ニュース一覧」上位N件のタイトルを比較し、
完全一致または fuzz>=THRESHOLD の重複が1件でもあれば NG（exit 1）。

使い方:
    python -X utf8 scripts/check_overlap.py [top_n] [threshold]
"""

import re
import subprocess
import sys

try:
    from rapidfuzz import fuzz

    HAS_RAPIDFUZZ = True
except ImportError:
    HAS_RAPIDFUZZ = False

TOP_N = int(sys.argv[1]) if len(sys.argv) > 1 else 7
THRESHOLD = int(sys.argv[2]) if len(sys.argv) > 2 else 80


def top_titles(rev: str, n: int) -> list[str]:
    """指定リビジョンの docs/index.html から上位n件の記事タイトルを抽出。"""
    out = subprocess.run(
        ["git", "show", f"{rev}:docs/index.html"],
        capture_output=True,
    ).stdout.decode("utf-8", errors="ignore")
    # 「ニュース一覧」の記事タイトルリンク（redelivery=既報タイルも含む）
    links = re.findall(
        r'class="font-semibold text-indigo-700[^"]*"[^>]*>\s*(.*?)\s*</a>', out, re.S
    )
    titles = [re.sub(r"\s+", " ", t).strip() for t in links]
    return [t for t in titles if t][:n]


def is_dup(a: str, b: str) -> bool:
    if a == b:
        return True
    if HAS_RAPIDFUZZ:
        return fuzz.ratio(a, b) >= THRESHOLD
    return False


def main() -> int:
    revs = subprocess.run(
        ["git", "log", "--format=%h", "-8", "--", "docs/index.html"],
        capture_output=True,
        text=True,
    ).stdout.split()
    if len(revs) < 2:
        print("比較対象のコミットが不足しています。")
        return 0

    ng = 0
    for newer, older in zip(revs, revs[1:]):
        new_t = top_titles(newer, TOP_N)
        old_t = top_titles(older, TOP_N)
        dups = [n for n in new_t for o in old_t if is_dup(n, o)]
        status = "NG" if dups else "OK"
        if dups:
            ng += 1
        sample = dups[0][:50] if dups else ""
        print(
            f"[{status}] {newer} vs {older}: 上位{TOP_N}件の重複 {len(dups)} 件  {sample}"
        )

    print(f"\n重複が出た日: {ng} 日（0 が目標）")
    return 1 if ng else 0


if __name__ == "__main__":
    sys.exit(main())
