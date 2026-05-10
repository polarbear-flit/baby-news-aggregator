"""Baby News Aggregator エントリーポイント — 業界動向特化版。

設計:
1. fetch_all_feeds: 業界動向ソースから記事収集（リコール系は撤廃）
2. analyze: ルールスコア
3. ai_rank_articles: Claude API で再評価（manufacturer/retail/market/...の7軸）
4. apply_rubric_to_all: 4軸 1-5 スコア + importance 付与
5. verify_links_batch: Telegram上位 7件のリンク検証
6. send_telegram: 業界カテゴリ別ハイライト配信
7. render: HTMLレポート生成
"""
import html
import json
import os
from datetime import datetime, timezone, timedelta

import requests

from src.ai_ranker import ai_rank_articles, generate_daily_summary
from src.analyzer import analyze
from src.config import (
    DEFAULT_REPORT_URL, HISTORY_PATH, MAX_ARTICLES_DISPLAY,
    OUTPUT_PATH, TREND_WINDOW_DAYS,
)
from src.fetcher import fetch_all_feeds, verify_links_batch
from src.quality_rubric import apply_rubric_to_all
from src.renderer import render


def load_history() -> list[dict]:
    if not os.path.exists(HISTORY_PATH):
        return []
    try:
        with open(HISTORY_PATH, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []


def save_history(history: list[dict], keyword_freq: dict, article_count: int) -> None:
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


# === 業界カテゴリラベル（Telegram/HTML共通）===
AXIS_LABELS = {
    "manufacturer":   "🏭 メーカー",
    "retail":         "🏬 小売・EC",
    "market":         "📊 市場",
    "consumer_trend": "👥 消費者トレンド",
    "product_launch": "🆕 新商品",
    "industry":       "📰 業界横断",
}


def diversify_top(
    articles: list[dict],
    top_n: int = 5,
    max_per_axis: int = 2,
) -> list[dict]:
    """上位 top_n 件で同じ軸が max_per_axis を超えないよう多様化。"""
    if not articles:
        return articles

    selected: list[dict] = []
    deferred: list[dict] = []
    axis_count: dict[str, int] = {}

    for a in articles:
        if len(selected) >= top_n:
            deferred.append(a)
            continue
        axis = a.get("ai_value_axis") or a.get("source_type") or "unknown"
        if axis_count.get(axis, 0) >= max_per_axis:
            deferred.append(a)
            continue
        selected.append(a)
        axis_count[axis] = axis_count.get(axis, 0) + 1

    while len(selected) < top_n and deferred:
        selected.append(deferred.pop(0))

    return selected + deferred


def _esc(value: str) -> str:
    return html.escape(str(value or ""), quote=False)


def _esc_attr(value: str) -> str:
    return html.escape(str(value or ""), quote=True)


def _article_link(article: dict, max_len: int = 80) -> str:
    title = _esc(article.get("title", ""))[:max_len]
    url = article.get("url", "")
    if not url:
        return title
    return f'<a href="{_esc_attr(url)}">{title}</a>'


def format_article_block(idx: int, a: dict) -> str:
    """importance + 業界軸ラベル付きの統一記事ブロックを生成。

    [N] 【importance】 軸ラベル
        タイトル
        Source: 媒体名
        Fact: 事実要約
        Why: 事業への意味
        Action: 次アクション
        URL: 記事を開く
    """
    imp = a.get("importance", "Medium")
    axis = a.get("ai_value_axis") or "industry"
    axis_label = AXIS_LABELS.get(axis, axis)
    title_link = _article_link(a, max_len=80)
    source = _esc(a.get("source_name", ""))
    url = a.get("url", "")
    url_disp = f'<a href="{_esc_attr(url)}">記事を開く</a>' if url else "—"
    fact = _esc(a.get("fact_summary", ""))[:140]
    fact_source = a.get("fact_source", "rss")
    # AI 生成の事実要約は「Fact (AI要約):」と明示し、RSS 事実データと区別する
    fact_label = "Fact (AI要約)" if fact_source == "ai" else "Fact"
    why = _esc(a.get("why_it_matters") or a.get("why_matters_jp") or "")[:140]
    hint = _esc(a.get("action_hint_jp", ""))[:80]

    lines = [
        f"<b>[{idx}] 【{imp}】 {axis_label}</b>",
        f"  {title_link}",
        f"  Source: {source}",
    ]
    if fact:
        lines.append(f"  {fact_label}: {fact}")
    if why:
        lines.append(f"  Why: {why}")
    if hint:
        lines.append(f"  Action: {hint}")
    lines.append(f"  URL: {url_disp}")
    return "\n".join(lines)


def send_telegram(analysis: dict, articles: list[dict]) -> None:
    """Telegram に業界動向サマリを送信。リコール/安全情報は完全除外。"""
    token = os.environ.get("BABY_NEWS_BOT_TOKEN")
    chat_id = os.environ.get("BABY_NEWS_CHAT_ID")
    if not token or not chat_id:
        print("[SKIP] Telegram: 環境変数未設定")
        return

    report_url = os.environ.get("BABY_NEWS_REPORT_URL", DEFAULT_REPORT_URL)
    jst = timezone(timedelta(hours=9))
    today = datetime.now(jst).strftime("%Y/%m/%d")

    cat_labels = {
        "feeding": "🍼 授乳", "mobility": "👶 ベビーカー",
        "car_safety": "🚗 チャイルドシート", "diaper": "🧸 おむつ",
        "wipes": "💧 おしりふき", "skincare": "🌿 スキンケア",
        "general": "📰 一般",
    }
    cat_lines = " / ".join(
        f"{cat_labels.get(k, _esc(k))}: {v}件"
        for k, v in sorted(analysis["category_freq"].items(), key=lambda x: -x[1])
        if v > 0
    ) or "なし"

    hot = analysis.get("hot_articles", articles)[:5]

    if hot:
        # importance=Low は配信から除外
        visible = [a for a in hot if a.get("importance") != "Low"]
        blocks = [format_article_block(i, a) for i, a in enumerate(visible, start=1)]
        highlights = "\n\n".join(blocks) if blocks else "本日は High/Medium 該当なし"
    else:
        highlights = "該当なし"

    # 今日の業界動向サマリ（AI生成 2-3 文、冒頭に表示）
    daily_summary = analysis.get("daily_summary", "")
    summary_section = (
        f"<b>📌 今日の業界動向</b>\n{_esc(daily_summary)}\n\n"
        if daily_summary else ""
    )

    # 「今日のアクション」（High優先で最大3件、Lowは除外）
    action_lines = []
    for a in sorted(hot, key=lambda x: 0 if x.get("importance") == "High" else 1):
        if len(action_lines) >= 3:
            break
        if a.get("importance") == "Low":
            continue
        hint = (a.get("action_hint_jp") or "").strip()
        if hint and hint.lower() not in ("特になし", "なし", "n/a", "none", "null"):
            action_lines.append(f"・{_esc(hint)[:60]}")
    action_section = (
        "<b>今日のアクション</b>\n" + "\n".join(action_lines) + "\n\n"
        if action_lines else ""
    )

    trending = analysis.get("trending", [])
    trend_text = "、".join(_esc(t["keyword"]) for t in trending[:3]) if trending else "なし"

    ai_status = ""
    if not analysis.get("ai_used", True):
        ai_status = "\n⚠️ AI評価未実行（API障害orキー未設定）。ルールスコアのみ"

    message = (
        f"📰 <b>ベビー用品 業界動向</b> {today}\n"
        f"━━━━━━━━━━━━━\n"
        f"{summary_section}"
        f"<b>今日のハイライト</b>\n\n"
        f"{highlights}\n\n"
        f"{action_section}"
        f"<b>カテゴリ別</b>: {cat_lines}\n"
        f"<b>急上昇</b>: {trend_text}\n"
        f"合計 {len(articles)} 件{ai_status}\n"
        f"━━━━━━━━━━━━━\n"
        f'<a href="{_esc_attr(report_url)}">日次レポートを開く</a>'
    )

    inline_keyboard = [[{"text": "📄 日次レポート", "url": report_url}]]
    for i, a in enumerate(hot[:3], start=1):
        if a.get("url") and a.get("importance") != "Low":
            inline_keyboard.append([{"text": f"記事 {i}", "url": a["url"]}])

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
    print("=== Baby News Aggregator (業界動向特化版) 起動 ===")

    print("フィード取得中...")
    articles = fetch_all_feeds()
    print(f"取得完了（フィルタ後）: {len(articles)} 件")

    if not articles:
        print("[WARN] 記事が0件です。HTMLは生成しますが内容は空になります。")

    history = load_history()
    print(f"履歴読み込み: {len(history)} レコード")

    print("分析・スコアリング中...")
    analysis = analyze(articles, history)

    # AIリランカー
    from src.ai_ranker import MAX_CANDIDATES
    print("AI評価中...")
    rule_top = analysis["hot_articles"][:MAX_CANDIDATES]
    rule_rest = analysis["hot_articles"][MAX_CANDIDATES:MAX_ARTICLES_DISPLAY]
    ai_evaluated, ai_used = ai_rank_articles(rule_top)

    # 多様性フィルター（同軸最大2件）
    ai_evaluated = diversify_top(ai_evaluated, top_n=5, max_per_axis=2)

    display_articles = ai_evaluated + rule_rest

    # Quality Rubric 適用
    print("Quality Rubric 適用中...")
    display_articles = apply_rubric_to_all(display_articles)
    ai_evaluated = apply_rubric_to_all(ai_evaluated)

    # 配信前リンク検証（上位7件のみ）
    print("リンク検証中（上位7件）...")
    verify_links_batch(ai_evaluated[:7], max_count=7)
    for a in ai_evaluated[:7]:
        if a.get("link_status") == "failed":
            a["importance"] = "Low"

    analysis["hot_articles"] = ai_evaluated
    analysis["ai_used"] = ai_used

    # 今日の業界動向サマリ（AI生成、上位8件から 2-3 文）
    # Codex指摘: importance=Low や link_status=failed の記事は配信されないので
    # daily_summary の入力からも除外する（隠した記事をサマリで先頭にしない）
    print("今日の業界動向サマリ生成中...")
    summary_input = [
        a for a in ai_evaluated
        if a.get("importance") != "Low"
        and a.get("link_status") != "failed"
    ][:8]
    daily_summary = generate_daily_summary(summary_input)
    analysis["daily_summary"] = daily_summary

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
