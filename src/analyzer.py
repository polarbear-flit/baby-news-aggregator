from collections import Counter
from datetime import datetime, timezone, timedelta

from src.config import KEYWORDS, TREND_WINDOW_DAYS


CATEGORY_LABEL = {
    "feeding":    "🍼 授乳・哺乳瓶",
    "mobility":   "👶 ベビーカー",
    "car_safety": "🚗 チャイルドシート",
    "diaper":     "🧸 おむつ",
    "wipes":      "💧 おしりふき",
    "skincare":   "🌿 スキンケア",
    "general":    "📰 一般",
}


def count_keyword_freq(articles: list[dict]) -> Counter:
    freq: Counter = Counter()
    for a in articles:
        for kw in a["matched_keywords"]:
            freq[kw] += 1
    return freq


def count_category_freq(articles: list[dict]) -> Counter:
    freq: Counter = Counter()
    for a in articles:
        # カテゴリはsource_configのものではなく、マッチしたキーワードから判定
        matched_cats: set[str] = set()
        text = (a["title"] + " " + a["summary"]).lower()
        for cat, kw_list in KEYWORDS.items():
            for kw in kw_list:
                if kw.lower() in text:
                    matched_cats.add(cat)
        for cat in matched_cats:
            freq[cat] += 1
    return freq


def calc_trending_keywords(current_freq: Counter, history: list[dict]) -> list[dict]:
    """過去履歴と比較して増加率上位5件を返す"""
    # 過去TREND_WINDOW_DAYS日のfreqを集計
    past_freq: Counter = Counter()
    cutoff = datetime.now(timezone.utc) - timedelta(days=TREND_WINDOW_DAYS)
    for record in history:
        try:
            ts = datetime.fromisoformat(record.get("date", ""))
            if ts.tzinfo is None:
                ts = ts.replace(tzinfo=timezone.utc)
            if ts < cutoff:
                continue
        except Exception:
            pass
        for kw, cnt in record.get("keyword_freq", {}).items():
            past_freq[kw] += cnt

    trending = []
    for kw, cnt in current_freq.items():
        past_cnt = past_freq.get(kw, 0)
        if past_cnt == 0:
            rate = float(cnt)
        else:
            rate = (cnt - past_cnt) / past_cnt
        trending.append({"keyword": kw, "count": cnt, "rate": round(rate, 2)})

    trending.sort(key=lambda x: x["rate"], reverse=True)
    return trending[:5]


def score_articles(articles: list[dict]) -> list[dict]:
    """キーワード数・リコール含有・新しさでスコア付け"""
    now = datetime.now(timezone.utc)
    scored = []
    for a in articles:
        score = len(a["matched_keywords"])
        text = (a["title"] + " " + a["summary"]).lower()
        if "recall" in text or "リコール" in text:
            score += 5
        if "safety" in text or "安全" in text:
            score += 2
        try:
            age_hours = (now - a["published_dt"]).total_seconds() / 3600
            if age_hours < 24:
                score += 3
            elif age_hours < 72:
                score += 1
        except Exception:
            pass
        scored.append({**a, "score": score})

    scored.sort(key=lambda x: x["score"], reverse=True)
    return scored


def generate_category_insight(category: str, articles: list[dict], freq: Counter) -> str:
    """カテゴリ別の示唆テキストを生成"""
    count = freq.get(category, 0)
    label = CATEGORY_LABEL.get(category, category)
    recall_count = sum(
        1 for a in articles
        if ("recall" in a["title"].lower() or "リコール" in a["title"])
        and category in _detect_categories(a)
    )
    if recall_count > 0:
        return f"{label}: {count}件の記事中{recall_count}件がリコール関連。安全動向の要確認。"
    elif count >= 5:
        return f"{label}: {count}件と活発。市場トレンドを把握するチャンス。"
    elif count >= 2:
        return f"{label}: {count}件を収集。引き続き動向を追う。"
    else:
        return f"{label}: 今期は{count}件。比較的静穏。"


def _detect_categories(article: dict) -> set[str]:
    text = (article["title"] + " " + article["summary"]).lower()
    cats = set()
    for cat, kw_list in KEYWORDS.items():
        for kw in kw_list:
            if kw.lower() in text:
                cats.add(cat)
    return cats


def generate_overall_insights(
    category_freq: Counter,
    trending: list[dict],
    hot_articles: list[dict],
) -> list[str]:
    insights = []

    # 最多カテゴリ
    if category_freq:
        top_cat, top_cnt = category_freq.most_common(1)[0]
        label = CATEGORY_LABEL.get(top_cat, top_cat)
        insights.append(f"最も注目度が高いカテゴリは {label}（{top_cnt}件）です。")

    # トレンドキーワード
    if trending:
        kw_names = "、".join(t["keyword"] for t in trending[:3])
        insights.append(f"急上昇キーワード: {kw_names}。前期比での増加が目立ちます。")

    # リコール数
    recall_count = sum(
        1 for a in hot_articles
        if "recall" in a["title"].lower() or "リコール" in a["title"]
    )
    if recall_count > 0:
        insights.append(f"リコール関連記事が{recall_count}件。安全・品質リスクへの注意が必要です。")

    # 記事総数
    insights.append(f"今回収集した記事は合計{len(hot_articles)}件です。")

    return insights


def analyze(articles: list[dict], history: list[dict]) -> dict:
    """全分析を実行してAnalysisResult dictを返す"""
    keyword_freq = count_keyword_freq(articles)
    category_freq = count_category_freq(articles)
    trending = calc_trending_keywords(keyword_freq, history)
    hot_articles = score_articles(articles)

    category_insights = {
        cat: generate_category_insight(cat, articles, category_freq)
        for cat in KEYWORDS
    }
    overall_insights = generate_overall_insights(category_freq, trending, articles)

    return {
        "keyword_freq": dict(keyword_freq.most_common(20)),
        "category_freq": dict(category_freq),
        "trending": trending,
        "hot_articles": hot_articles[:10],
        "category_insights": category_insights,
        "overall_insights": overall_insights,
        "category_label": CATEGORY_LABEL,
        "cat_keywords": KEYWORDS,  # テンプレートのフィルター判定に使用
    }
