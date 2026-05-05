import html
import json
import os
from datetime import datetime, timezone, timedelta

import requests

from src.analyzer import analyze
from src.config import (
    DEFAULT_REPORT_URL, HISTORY_PATH, MAX_ARTICLES_DISPLAY,
    OUTPUT_PATH, TREND_WINDOW_DAYS,
)
from src.fetcher import fetch_all_feeds
from src.renderer import render


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


def _esc(value: str) -> str:
    """Telegram HTML parse_mode用の本文エスケープ。"""
    return html.escape(str(value or ""), quote=False)


def _esc_attr(value: str) -> str:
    """HTML属性値（href等）用の厳しめエスケープ。"""
    return html.escape(str(value or ""), quote=True)


def _article_link(article: dict, max_len: int = 70) -> str:
    """タイトル文字列を <a href="...">title</a> に変換。URLが無ければプレーンテキスト。"""
    title = _esc(article.get("title", ""))[:max_len]
    url = article.get("url", "")
    if not url:
        return title
    return f'<a href="{_esc_attr(url)}">{title}</a>'


def send_telegram(analysis: dict, articles: list[dict]) -> None:
    """Telegramにサマリを送信。

    - parse_mode=HTML でタイトルをリンク化
    - reply_markup の Inline Keyboard で「日次レポート」「元記事1〜3」ボタンを付与
    """
    token = os.environ.get("BABY_NEWS_BOT_TOKEN")
    chat_id = os.environ.get("BABY_NEWS_CHAT_ID")
    if not token or not chat_id:
        print("[SKIP] Telegram: 環境変数未設定")
        return

    report_url = os.environ.get("BABY_NEWS_REPORT_URL", DEFAULT_REPORT_URL)

    jst = timezone(timedelta(hours=9))
    today = datetime.now(jst).strftime("%Y/%m/%d")

    cat_labels = {
        "feeding": "🍼 授乳",
        "mobility": "👶 ベビーカー",
        "car_safety": "🚗 チャイルドシート",
        "diaper": "🧸 おむつ",
        "wipes": "💧 おしりふき",
        "skincare": "🌿 スキンケア",
        "general": "📰 一般",
    }
    cat_lines = " / ".join(
        f"{cat_labels.get(k, _esc(k))}: {v}件"
        for k, v in sorted(analysis["category_freq"].items(), key=lambda x: -x[1])
        if v > 0
    ) or "なし"

    hot = analysis.get("hot_articles", articles)[:5]
    if hot:
        highlight_lines = []
        for i, a in enumerate(hot, start=1):
            link = _article_link(a)
            source = _esc(a.get("source_name", ""))
            score = a.get("score", "")
            highlight_lines.append(f"{i}. {link}\n   <i>{source}</i> · score {score}")
        highlights = "\n".join(highlight_lines)
    else:
        highlights = "該当なし"

    trending = analysis.get("trending", [])
    trend_text = "、".join(_esc(t["keyword"]) for t in trending[:3]) if trending else "なし"

    recall_count = sum(
        1 for a in articles
        if any(
            kw in (a.get("title", "") + a.get("summary", "")).lower()
            for kw in ["リコール", "回収", "recall"]
        )
    )
    recall_line = f"\n⚠️ リコール・回収関連: {recall_count}件" if recall_count else ""

    message = (
        f"📰 <b>ベビー用品ニュース</b> {today}\n"
        f"━━━━━━━━━━━━━\n"
        f"<b>今日のハイライト</b>\n"
        f"{highlights}\n\n"
        f"<b>カテゴリ別</b>\n"
        f"{cat_lines}\n\n"
        f"<b>急上昇</b>: {trend_text}{recall_line}\n\n"
        f"合計 {len(articles)} 件\n"
        f"━━━━━━━━━━━━━\n"
        f'<a href="{_esc_attr(report_url)}">日次レポートを開く</a>'
    )

    inline_keyboard = [[{"text": "📄 日次レポート", "url": report_url}]]
    for i, a in enumerate(hot[:3], start=1):
        if a.get("url"):
            inline_keyboard.append([{"text": f"元記事 {i}", "url": a["url"]}])

    payload = {
        "chat_id": chat_id,
        "text": message[:4096],
        "parse_mode": "HTML",
        "disable_web_page_preview": True,
        "reply_markup": {"inline_keyboard": inline_keyboard},
    }

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    resp = requests.post(url, json=payload, timeout=10)
    if resp.ok:
        print("[OK] Telegram送信完了")
    else:
        print(f"[WARN] Telegram送信失敗: {resp.status_code} {resp.text[:200]}")


def main() -> None:
    print("=== Baby News Aggregator 起動 ===")

    print("フィード取得中...")
    articles = fetch_all_feeds()
    print(f"取得完了（フィルタ後）: {len(articles)} 件")

    if not articles:
        print("[WARN] 記事が0件です。HTMLは生成しますが内容は空になります。")

    history = load_history()
    print(f"履歴読み込み: {len(history)} レコード")

    print("分析・スコアリング中...")
    analysis = analyze(articles, history)

    # スコア順上位N件を表示・通知に使う
    display_articles = analysis["hot_articles"][:MAX_ARTICLES_DISPLAY]

    print("HTML生成中...")
    html_str = render(display_articles, analysis)

    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        f.write(html_str)
    print(f"[OK] 出力: {OUTPUT_PATH}")

    send_telegram(analysis, display_articles)

    save_history(history, analysis["keyword_freq"], len(display_articles))

    print("=== 完了 ===")


if __name__ == "__main__":
    main()
