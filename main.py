from src.fetcher import fetch_all_feeds
from src.analyzer import analyze
from src.renderer import render
import json
import os
import sys
from datetime import datetime, timezone, timedelta

from src.config import HISTORY_PATH, OUTPUT_PATH, TREND_WINDOW_DAYS


def load_history() -> list[dict]:
    """data/history.json読み込み。なければ[]"""
    if not os.path.exists(HISTORY_PATH):
        return []
    try:
        with open(HISTORY_PATH, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []


def save_history(history: list[dict], keyword_freq: dict, article_count: int) -> None:
    """今日のデータを先頭に追加、30日超は削除して保存"""
    jst = timezone(timedelta(hours=9))
    today = datetime.now(jst).isoformat()

    new_record = {
        "date": today,
        "article_count": article_count,
        "keyword_freq": keyword_freq,
    }

    # 30日より古いレコードを削除
    cutoff = datetime.now(timezone.utc) - timedelta(days=TREND_WINDOW_DAYS)
    kept = []
    for r in history:
        try:
            ts = datetime.fromisoformat(r["date"])
            if ts.tzinfo is None:
                ts = ts.replace(tzinfo=timezone.utc)
            if ts >= cutoff:
                kept.append(r)
        except Exception:
            pass

    updated = [new_record] + kept

    os.makedirs(os.path.dirname(HISTORY_PATH), exist_ok=True)
    with open(HISTORY_PATH, "w", encoding="utf-8") as f:
        json.dump(updated, f, ensure_ascii=False, indent=2)
    print(f"[OK] history保存: {len(updated)}件")


def main() -> None:
    print("=== Baby News Aggregator 起動 ===")

    # 1. フィード取得
    print("フィード取得中...")
    articles = fetch_all_feeds()
    print(f"取得完了: {len(articles)} 件")

    if not articles:
        print("[WARN] 記事が0件です。HTMLは生成しますが内容は空になります。")

    # 2. 履歴読み込み
    history = load_history()
    print(f"履歴読み込み: {len(history)} レコード")

    # 3. 分析
    print("分析中...")
    analysis = analyze(articles, history)

    # 4. レンダリング
    print("HTML生成中...")
    html = render(articles, analysis)

    # 5. docs/index.html書き込み
    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"[OK] 出力: {OUTPUT_PATH}")

    # 6. 履歴保存
    save_history(history, analysis["keyword_freq"], len(articles))

    print("=== 完了 ===")


if __name__ == "__main__":
    main()
