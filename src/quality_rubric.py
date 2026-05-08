"""News Quality Rubric の適用層。

`docs/rubrics/baby_goods_news_quality_rubric.md` で定義した4軸を、
記事dictに source_quality_score / business_relevance_score / actionability_score /
importance / fact_summary / business_implication / why_it_matters として付加する。

設計方針:
- 既存の AI評価結果（ai_value_score, ai_value_axis, why_matters_jp, action_hint_jp）と
  source_type を入力に、Rubric準拠の 1-5 スケールに正規化するだけの薄い層。
- 既存フィールドは破壊せず、新フィールドを追加する。
- ロジックは純関数に保ち、テストしやすくする。
"""
from typing import Optional


# === Source Quality（source_type → 1-5）===
SOURCE_QUALITY_MAP: dict[str, int] = {
    "official_recall":     5,
    "official_regulation": 5,
    "official_safety":     5,
    "brand_official":      4,
    "retailer_official":   4,
    "market_research":     4,
    "pr_wire":             3,
    "google_news":         2,
    "seo_media":           1,
}

# value_axis → business_relevance（1-5）
VALUE_AXIS_RELEVANCE_MAP: dict[str, int] = {
    "safety":          5,
    "regulation":      5,
    "competitor":      4,
    "product_launch":  4,
    "retail":          4,
    "market":          4,
    "consumer_trend":  3,
    "noise":           1,
}

# importance しきい値
HIGH_COMBINED_MIN = 4.0
HIGH_RELEVANCE_MIN = 4
MEDIUM_COMBINED_MIN = 3.0


def derive_source_quality_score(article: dict) -> int:
    """source_type から source_quality_score (1-5) を返す。"""
    source_type = article.get("source_type") or "google_news"
    return SOURCE_QUALITY_MAP.get(source_type, 2)


def derive_business_relevance_score(article: dict) -> int:
    """AI の value_axis と value_score から business_relevance_score (1-5) を返す。

    AI評価が無い場合（フォールバック動作中）はルールスコアと source_type から推定する。
    """
    axis = article.get("ai_value_axis")
    if axis:
        return VALUE_AXIS_RELEVANCE_MAP.get(axis, 3)

    # AI評価が無い場合: source_quality と rule score から推定
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
    # 動詞始まりかつ十分な長さで具体的な動作と判定
    length = len(hint)
    # 具体的動詞のヒューリスティック
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

    強制 High: safety/regulation かつ value_score >= 80
    強制 Low: is_relevant=False または link_status=failed
    """
    if article is not None:
        # 強制 Low: AI が無関係と判定 / リンク切れ
        if article.get("ai_is_relevant") is False:
            return "Low"
        if article.get("link_status") == "failed":
            return "Low"
        # 強制 High: 重大な safety / regulation
        axis = article.get("ai_value_axis")
        score = article.get("ai_value_score", 0) or 0
        if axis in ("safety", "regulation") and score >= 80:
            return "High"

    combined = (source_q + relevance + actionability) / 3
    if combined >= HIGH_COMBINED_MIN and relevance >= HIGH_RELEVANCE_MIN:
        return "High"
    if combined >= MEDIUM_COMBINED_MIN:
        return "Medium"
    return "Low"


def apply_rubric(article: dict) -> dict:
    """記事dictに Rubric準拠のフィールドを追加して返す（破壊的変更）。

    付加するフィールド:
    - source_quality_score: 1-5
    - business_relevance_score: 1-5
    - actionability_score: 1-5
    - importance: High / Medium / Low
    - fact_summary: 事実要約（RSSのsummary or タイトル）
    - business_implication: 事業示唆（AI の why_matters_jp を流用）
    - why_it_matters: business_implication の別名（テンプレート可読性のため）
    """
    source_q = derive_source_quality_score(article)
    relevance = derive_business_relevance_score(article)
    action = derive_actionability_score(article)
    importance = compute_importance(source_q, relevance, action, article)

    # fact_summary: RSS の summary を1〜2文程度に整形
    fact = (article.get("summary") or "").strip()
    # 改行や連続スペースを正規化
    fact = " ".join(fact.split())[:200]
    if not fact:
        fact = (article.get("title") or "")[:200]

    why = (article.get("why_matters_jp") or "").strip()

    article.update({
        "source_quality_score": source_q,
        "business_relevance_score": relevance,
        "actionability_score": action,
        "importance": importance,
        "fact_summary": fact,
        "business_implication": why,  # 事業への意味
        "why_it_matters": why,  # テンプレート用エイリアス
    })
    return article


def apply_rubric_to_all(articles: list[dict]) -> list[dict]:
    """記事リスト全件に Rubric を適用。"""
    return [apply_rubric(a) for a in articles]
