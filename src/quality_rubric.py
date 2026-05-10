"""News Quality Rubric の適用層 — 業界動向特化版。

`docs/rubrics/baby_goods_news_quality_rubric.md` で定義した4軸を、
記事dictに source_quality_score / business_relevance_score / actionability_score /
importance / fact_summary / business_implication / why_it_matters として付加する。

旧版にあった「safety/regulation 強制 High」ルールは撤廃。
リコール・規制系の記事は HARD_NOISE で入口排除済みのため、Rubric では考慮しない。
"""
from typing import Optional


# === Source Quality（source_type → 1-5）===
SOURCE_QUALITY_MAP: dict[str, int] = {
    "brand_official":    5,
    "retailer_official": 5,
    "market_research":   5,
    "trade_press":       4,
    "pr_wire":           3,
    "google_news":       2,
    "seo_media":         1,
}

# value_axis → business_relevance（1-5）— 業界動向7軸
VALUE_AXIS_RELEVANCE_MAP: dict[str, int] = {
    "manufacturer":    5,
    "retail":          5,
    "product_launch":  4,
    "market":          4,
    "consumer_trend":  3,
    "industry":        3,
    "noise":           1,
}

# importance しきい値（旧 4.0/3.0 では Google News (source_q=2) が High に届きにくく
# 全件 Low になる問題があったため、業界焦点ソース追加と同時に緩和）
HIGH_COMBINED_MIN = 3.5
HIGH_RELEVANCE_MIN = 4
MEDIUM_COMBINED_MIN = 2.5


def derive_source_quality_score(article: dict) -> int:
    """source_type から source_quality_score (1-5) を返す。"""
    source_type = article.get("source_type") or "google_news"
    return SOURCE_QUALITY_MAP.get(source_type, 2)


def derive_business_relevance_score(article: dict) -> int:
    """AI の value_axis と value_score から business_relevance_score (1-5) を返す。"""
    axis = article.get("ai_value_axis")
    if axis:
        return VALUE_AXIS_RELEVANCE_MAP.get(axis, 3)

    rule_score = article.get("score", 0)
    if rule_score >= 80:
        return 4
    if rule_score >= 50:
        return 3
    if rule_score >= 25:
        return 2
    return 1


def derive_actionability_score(article: dict) -> int:
    """action_hint_jp の有無・具体性から actionability_score (1-5) を返す。"""
    hint = (article.get("action_hint_jp") or "").strip()
    if not hint or hint.lower() in ("特になし", "なし", "n/a", "none", "null"):
        return 1
    length = len(hint)
    concrete_verbs = ("確認", "作成", "見直", "比較", "調査", "更新", "展開", "計画", "検討", "発注")
    has_concrete_verb = any(v in hint for v in concrete_verbs)
    if length >= 18 and has_concrete_verb:
        return 5
    if length >= 10 and has_concrete_verb:
        return 4
    if length >= 10:
        return 3
    return 2


def compute_importance(
    source_q: int,
    relevance: int,
    actionability: int,
    article: Optional[dict] = None,
) -> str:
    """3軸スコアから importance: High / Medium / Low を決定。

    強制ルール:
    - is_relevant=False → Low
    - link_status=failed → Low
    （safety/regulation 強制 High は撤廃）
    """
    if article is not None:
        if article.get("ai_is_relevant") is False:
            return "Low"
        if article.get("link_status") == "failed":
            return "Low"

    combined = (source_q + relevance + actionability) / 3
    if combined >= HIGH_COMBINED_MIN and relevance >= HIGH_RELEVANCE_MIN:
        return "High"
    if combined >= MEDIUM_COMBINED_MIN:
        return "Medium"
    return "Low"


def apply_rubric(article: dict) -> dict:
    """記事dictに Rubric準拠のフィールドを追加して返す（破壊的変更）。"""
    source_q = derive_source_quality_score(article)
    relevance = derive_business_relevance_score(article)
    action = derive_actionability_score(article)
    importance = compute_importance(source_q, relevance, action, article)

    # fact_summary: AI生成 (ai_fact_summary) を優先、なければ RSS summary、最後にタイトル
    # fact_source で「事実データ」と「AI推測要約」を区別する（Data Consistency 確保）。
    # UI 側は fact_source="ai" の場合に「(AI要約)」と明示してユーザーに知らせる。
    ai_fact = (article.get("ai_fact_summary") or "").strip()
    if ai_fact:
        fact = " ".join(ai_fact.split())[:200]
        fact_source = "ai"
    else:
        rss_fact = (article.get("summary") or "").strip()
        rss_fact = " ".join(rss_fact.split())[:200]
        if rss_fact:
            fact = rss_fact
            fact_source = "rss"
        else:
            fact = (article.get("title") or "")[:200]
            fact_source = "title"

    why = (article.get("why_matters_jp") or "").strip()

    article.update({
        "source_quality_score": source_q,
        "business_relevance_score": relevance,
        "actionability_score": action,
        "importance": importance,
        "fact_summary": fact,
        "fact_source": fact_source,
        "business_implication": why,
        "why_it_matters": why,
    })
    return article


def apply_rubric_to_all(articles: list[dict]) -> list[dict]:
    """記事リスト全件に Rubric を適用。"""
    return [apply_rubric(a) for a in articles]
