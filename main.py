import html
import json
import os
from datetime import datetime, timezone, timedelta

import requests

from src.ai_ranker import ai_rank_articles
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


# 軸別の上限。リコール（safety）は「本当に重要なもの1件」だけにし、
# 規制（regulation）も1件まで。それ以外は最大2件まで。
DEFAULT_AXIS_CAPS: dict[str, int] = {
    "safety": 1,
    "regulation": 1,
}


def diversify_top(
    articles: list[dict],
    top_n: int = 5,
    max_per_axis: int = 2,
    axis_caps: dict[str, int] | None = None,
) -> list[dict]:
    """上位 top_n 件で軸の偏りを抑える多様化。

    - axis_caps で軸ごとの上限を指定（safety=1 など）
    - 指定がない軸は max_per_axis (デフォルト2) を上限とする
    - 並び順は score 降順を維持しつつ、軸キャップを超えた記事は後ろに繰り下げる

    例: max_per_axis=2 / axis_caps={"safety": 1} で
        入力 [s1, s2, s3, p1, p2, m1] (s=safety) →
        出力 [s1, p1, p2, m1, s2, s3]
    """
    if not articles:
        return articles

    if axis_caps is None:
        axis_caps = DEFAULT_AXIS_CAPS

    selected: list[dict] = []
    deferred: list[dict] = []
    axis_count: dict[str, int] = {}

    for a in articles:
        if len(selected) >= top_n:
            deferred.append(a)
            continue
        axis = (
            a.get("ai_value_axis")
            or a.get("source_type")
            or a.get("category")
            or "unknown"
        )
        cap = axis_caps.get(axis, max_per_axis)
        if axis_count.get(axis, 0) >= cap:
            deferred.append(a)
            continue
        selected.append(a)
        axis_count[axis] = axis_count.get(axis, 0) + 1

    # top_n 未満なら制約緩和して埋める
    while len(selected) < top_n and deferred:
        selected.append(deferred.pop(0))

    return selected + deferred


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

    def _format_article_line(idx: int, a: dict) -> str:
        link = _article_link(a)
        why = a.get("why_matters_jp", "")
        axis = a.get("ai_value_axis", "")
        score = a.get("ai_value_score", a.get("score", ""))
        if why:
            label = _esc(axis or a.get("source_name", ""))
            return f"{idx}. {link}\n   <i>{label}</i> · score {score} — {_esc(why)[:90]}"
        source = _esc(a.get("source_name", ""))
        return f"{idx}. {link}\n   <i>{source}</i> · score {score}"

    if hot:
        highlights = "\n".join(_format_article_line(i, a) for i, a in enumerate(hot, start=1))
    else:
        highlights = "該当なし"

    # ⚠️ Telegramチャットにはリコール/安全情報を出さない方針（ユーザー要望）。
    # safety_articles は HTMLレポートに独立セクションとして残す（renderer/template側）。

    # 「今日のアクション」: ハイライト上位から最大3件
    action_lines = []
    for a in hot[:5]:
        if len(action_lines) >= 3:
            break
        hint = (a.get("action_hint_jp") or "").strip()
        if hint and hint.lower() not in ("特になし", "なし", "n/a", "none", "null"):
            action_lines.append(f"・{_esc(hint)[:60]}")
    action_section = (
        "<b>今日のアクション</b>\n" + "\n".join(action_lines) + "\n\n"
        if action_lines else ""
    )

    trending = analysis.get("trending", [])
    trend_text = "、".join(_esc(t["keyword"]) for t in trending[:3]) if trending else "なし"

    # AI実行ステータス（未実行の場合はTelegram末尾に明示）
    ai_status = ""
    if not analysis.get("ai_used", True):
        ai_status = "\n⚠️ AI評価未実行（API障害orキー未設定）。ルールスコアのみで並んでいます"

    message = (
        f"📰 <b>ベビー用品ニュース</b> {today}\n"
        f"━━━━━━━━━━━━━\n"
        f"<b>今日のハイライト</b>\n"
        f"{highlights}\n\n"
        f"{action_section}"
        f"<b>カテゴリ別</b>\n"
        f"{cat_lines}\n\n"
        f"<b>急上昇</b>: {trend_text}\n\n"
        f"合計 {len(articles)} 件{ai_status}\n"
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

    # AIリランカー: ルールスコア上位 MAX_CANDIDATES (=30) 件を Claude API で再評価。
    # MAX_CANDIDATES と rule_top の件数を揃えて、未評価で意図せず落ちる記事を防ぐ。
    # API未設定/失敗時はフォールバックでルールスコアのまま使う。
    from src.ai_ranker import MAX_CANDIDATES
    print("AI評価中...")
    rule_top = analysis["hot_articles"][:MAX_CANDIDATES]
    rule_rest = analysis["hot_articles"][MAX_CANDIDATES:MAX_ARTICLES_DISPLAY]
    ai_evaluated, ai_used = ai_rank_articles(rule_top)

    # safety/regulation はメインハイライトから除外し、HTML 上で別セクションに切り出す。
    # ユーザー要望: 「リコールはTelegramチャットには不要。HTMLレポートでは重要1-2件を別だし」
    # ただし score<80 の中位 safety/regulation も remaining_safety として保持し、
    # HTMLレポート/履歴から消えないようにする（Codex指摘対応）。
    SAFETY_AXES = {"safety", "regulation"}
    SAFETY_MIN_SCORE = 80  # 別出しに昇格する基準（本当に重要なもの）

    all_safety_ai = sorted(
        [a for a in ai_evaluated if a.get("ai_value_axis") in SAFETY_AXES],
        key=lambda x: x.get("ai_value_score", 0),
        reverse=True,
    )
    safety_articles = [
        a for a in all_safety_ai
        if a.get("ai_value_score", 0) >= SAFETY_MIN_SCORE
    ][:2]  # 別出しに使うのは score >= 80 の上位2件のみ
    # 別出しに入らなかった safety/regulation（score<80 や 3件目以降）
    _safety_ids = {id(a) for a in safety_articles}
    remaining_safety = [a for a in all_safety_ai if id(a) not in _safety_ids]

    main_articles = [
        a for a in ai_evaluated
        if a.get("ai_value_axis") not in SAFETY_AXES
    ]

    # メインハイライトは多様化（safety無いので axis_caps は不要）
    main_articles = diversify_top(main_articles, top_n=5, max_per_axis=2, axis_caps={})

    # 表示用 = メインハイライト + 別出し安全 + 残りの安全 + AI評価圏外
    # remaining_safety を入れることで HTML/history に中位 safety/regulation も残る
    display_articles = main_articles + safety_articles + remaining_safety + rule_rest

    # send_telegram で参照されるフィールドを差し替え
    analysis["hot_articles"] = main_articles
    analysis["safety_articles"] = safety_articles
    analysis["ai_used"] = ai_used

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
