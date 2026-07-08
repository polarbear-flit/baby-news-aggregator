"""記事スコアリング・トレンド検出・カテゴリ分類 — 業界動向特化版。

スコア式:
  source_weight + lang_bonus + key_entity + industry_signal + freshness - soft_noise

旧版にあった「安全 (+25) / 規制 (+20)」のボーナスは撤廃。
業界動向（新商品・市場・売上等）のシグナルを代わりに加点する。
"""

from collections import Counter
from datetime import datetime, timedelta, timezone

from src.config import (
    KEYWORDS,
    TREND_WINDOW_DAYS,
    SOURCE_WEIGHTS,
    KEY_ENTITIES,
    INDUSTRY_TERMS,
    SOFT_NOISE_TERMS,
    CRITICAL_OVERRIDE,
    DOMAIN_ALLOWLIST_BONUS,
)

CATEGORY_LABEL = {
    "feeding": "🍼 授乳・哺乳瓶",
    "mobility": "👶 ベビーカー",
    "car_safety": "🚗 チャイルドシート",
    "diaper": "🧸 おむつ",
    "wipes": "💧 おしりふき",
    "skincare": "🌿 スキンケア",
    "general": "📰 一般",
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
    """過去履歴と比較して増加率上位5件を返す。"""
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


def _contains_any(text: str, words: list[str]) -> bool:
    return any(w.lower() in text for w in words)


def score_articles(articles: list[dict]) -> list[dict]:
    """ソース信頼度 + 言語 + 主要企業 + 業界シグナル + 鮮度 + ソフトノイズ減点でスコア付け。

    安全/規制ボーナスは廃止。業界動向（新商品・市場・売上等）を代わりに加点。
    """
    now = datetime.now(timezone.utc)
    critical_lower = [c.lower() for c in CRITICAL_OVERRIDE]
    scored = []
    for a in articles:
        text = (a.get("title", "") + " " + a.get("summary", "")).lower()
        source_type = a.get("source_type", "google_news")

        # 1) ソース信頼度
        score = SOURCE_WEIGHTS.get(source_type, 5)

        # 2) 言語ボーナス（日本のECカテゴリ担当向けなので日本語優先）
        if a.get("language") == "ja":
            score += 20

        # 3) 業界動向シグナル（新商品・市場・売上・出店・PB等）
        if _contains_any(text, INDUSTRY_TERMS):
            score += 25

        # 4) 主要企業・小売エンティティ
        if _contains_any(text, KEY_ENTITIES):
            score += 15

        # 5) ソフトノイズ減点（CRITICAL_OVERRIDE 該当なら相殺。空のため実質無効化）
        if _contains_any(text, SOFT_NOISE_TERMS):
            if not (critical_lower and _contains_any(text, critical_lower)):
                score -= 20

        # 5.5) 信頼ソース加点（PR TIMES/流通ニュース/ダイヤモンドRM 等）。
        # 記事URLはGoogle Newsリダイレクトなので、URL・媒体名・タイトル末尾で照合。
        allow_blob = (
            (a.get("url", "") or "")
            + " "
            + (a.get("source_name", "") or "")
            + " "
            + (a.get("title", "") or "")
        ).lower()
        for domain, bonus in DOMAIN_ALLOWLIST_BONUS.items():
            if domain in allow_blob:
                score += bonus
                break

        # 6) 鮮度（「今日の」日次ブリーフなので直近を強く優遇。2026-07-08 にカーブを詰めた）
        published_dt = a.get("published_dt")
        if published_dt:
            try:
                age_hours = (now - published_dt).total_seconds() / 3600
                if age_hours <= 24:
                    score += 15
                elif age_hours <= 72:
                    score += 5
                elif age_hours <= 7 * 24:
                    score += 0
                else:
                    score -= 30
            except Exception:
                score -= 25
        else:
            score -= 25

        scored.append({**a, "score": max(0, score)})

    scored.sort(key=lambda x: x["score"], reverse=True)
    return scored


def generate_category_insight(
    category: str, articles: list[dict], freq: Counter
) -> str:
    """カテゴリ別の示唆テキスト。リコール言及を撤廃し、業界動向に焦点。"""
    count = freq.get(category, 0)
    label = CATEGORY_LABEL.get(category, category)
    if count >= 5:
        return f"{label}: {count}件と活発。市場トレンドを把握するチャンス。"
    elif count >= 2:
        return f"{label}: {count}件を収集。引き続き動向を追う。"
    else:
        return f"{label}: 今期は{count}件。比較的静穏。"


def generate_overall_insights(
    category_freq: Counter,
    trending: list[dict],
    hot_articles: list[dict],
) -> list[str]:
    """エグゼクティブサマリー。リコール件数言及は撤廃、業界動向中心。"""
    insights = []

    if category_freq:
        top_cat, top_cnt = category_freq.most_common(1)[0]
        label = CATEGORY_LABEL.get(top_cat, top_cat)
        insights.append(f"最も注目度が高いカテゴリは {label}（{top_cnt}件）です。")

    if trending:
        kw_names = "、".join(t["keyword"] for t in trending[:3])
        insights.append(f"急上昇キーワード: {kw_names}。前期比での増加が目立ちます。")

    insights.append(f"今回収集した記事は合計{len(hot_articles)}件です。")

    return insights


def analyze(articles: list[dict], history: list[dict]) -> dict:
    """全分析を実行して AnalysisResult dict を返す。"""
    scored = score_articles(articles)
    keyword_freq = count_keyword_freq(scored)
    category_freq = count_category_freq(scored)
    trending = calc_trending_keywords(keyword_freq, history)

    category_insights = {
        cat: generate_category_insight(cat, scored, category_freq) for cat in KEYWORDS
    }
    overall_insights = generate_overall_insights(category_freq, trending, scored)

    return {
        "keyword_freq": dict(keyword_freq.most_common(20)),
        "category_freq": dict(category_freq),
        "trending": trending,
        "hot_articles": scored,
        "category_insights": category_insights,
        "overall_insights": overall_insights,
        "category_label": CATEGORY_LABEL,
        "cat_keywords": KEYWORDS,
    }
