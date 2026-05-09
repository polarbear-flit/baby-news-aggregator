"""ルールスコアで絞った候補を Claude API で再評価する — 業界動向特化版。

設計方針:
- 目的を「ベビー用品EC事業の業界動向把握」に統一。
- リコール・規制系の評価軸は撤廃（HARD_NOISE で入口排除済み）。
- value_axis は manufacturer / retail / market / consumer_trend / product_launch / industry / noise の7軸。
- AI が is_relevant=False と判定した記事は除外。
- ANTHROPIC_API_KEY 未設定/API失敗時はフォールバック動作。
"""
import json
import os

DEFAULT_MODEL = "claude-haiku-4-5-20251001"
MAX_CANDIDATES = 30
MAX_OUTPUT_TOKENS = 12000

RANK_TOOL = {
    "name": "rank_baby_news",
    "description": "Rank baby goods business news for a Japanese EC category manager.",
    "strict": True,
    "input_schema": {
        "type": "object",
        "properties": {
            "items": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "article_id": {
                            "type": "string",
                            "description": "入力で渡されたid（文字列）",
                        },
                        "is_relevant": {
                            "type": "boolean",
                            "description": "ベビー用品EC事業のカテゴリ担当が読む価値があれば true",
                        },
                        "value_score": {
                            "type": "integer",
                            "minimum": 0,
                            "maximum": 100,
                            "description": "事業価値スコア。80+=必読、50+=チェック推奨、30未満=ノイズ",
                        },
                        "value_axis": {
                            "type": "string",
                            "enum": [
                                "manufacturer",     # メーカー動向（新商品・戦略・業績）
                                "retail",           # 小売動向（西松屋・赤本・量販店・EC施策）
                                "market",           # 市場規模・シェア・売上トレンド
                                "consumer_trend",   # 消費者行動・ライフスタイル変化
                                "product_launch",   # 新商品・新サービス発売
                                "industry",         # その他業界動向（提携・買収・展示会等）
                                "noise",            # ベビー用品EC事業に無関係
                            ],
                            "description": "記事の主軸",
                        },
                        "why_matters_jp": {
                            "type": "string",
                            "minLength": 5,
                            "description": "なぜ商品担当に重要か。80文字以内・日本語・結論ファースト",
                        },
                        "action_hint_jp": {
                            "type": "string",
                            "minLength": 5,
                            "description": "今日取るべき次アクション。10〜60文字・日本語・動詞始まり",
                        },
                    },
                    "required": [
                        "article_id", "is_relevant", "value_score",
                        "value_axis", "why_matters_jp", "action_hint_jp",
                    ],
                },
            }
        },
        "required": ["items"],
    },
}


def _build_prompt(compact: list[dict]) -> str:
    from datetime import datetime, timezone, timedelta

    today = datetime.now(timezone(timedelta(hours=9))).strftime("%Y-%m-%d")
    return f"""あなたは日本のベビー用品EC事業のカテゴリマネージャー向け「業界動向ニュース」編集者です。
本日は {today}（JST）です。
以下の{len(compact)}件の記事を1件ずつ評価し、rank_baby_news ツールの items 配列に **必ず{len(compact)}件すべて** 含めて返してください。

【目的】
カテゴリ担当が「メーカー動向 / 小売動向 / 市場・消費者トレンド / 新商品」を毎朝5分で把握できる Daily Industry Intelligence。
**リコール・回収・安全性関連の記事は対象外**（既に入口で除外済み）。万一含まれていたら is_relevant=false にする。

【評価方針（重要度順）】
1. **メーカー動向**：ピジョン/コンビ/アップリカ/カトージ/リッチェル/ユニチャーム/花王の新商品・戦略・業績 → manufacturer
2. **小売動向**：西松屋/赤ちゃん本舗/アカチャンホンポ/トイザらス/ニトリ/イオン/楽天/Amazon のベビー用品EC施策・PB・出店・販売戦略 → retail
3. **市場・消費者トレンド**：市場規模・シェア・出生数・消費者行動・D2C/サブスク変化 → market / consumer_trend
4. **新商品**：哺乳瓶・ベビーカー・チャイルドシート・おむつ・スキンケア等の新商品・リニューアル → product_launch
5. **業界横断**：展示会・業界レポート・提携・買収 → industry

【除外（is_relevant=false）】
- リコール・回収・自主回収（万一すり抜けた場合）
- 一般大人向け食品・大人化粧品・健康食品
- 子育てライフスタイルコラム・芸能人の子育て話題
- 「おすすめランキング」「選び方ガイド」「育児あるある」「画像ギャラリー」
- 一般小売の食品部門・ベビー以外のPR

【鮮度ルール — 厳守】
本日から30日以上前の話題は基本 is_relevant=false。
⚠️ Google News RSSは古い記事を再インデックスすると pubDate を更新するため、**published 日付は信用しないこと**:
- タイトル/要約に「2018年」〜「2025年」「昨年」「去年」が含まれる場合は古い記事 → is_relevant=false
- 「○○年版」「20XX年X月X日に発表」など過去年が記事の主題 → is_relevant=false
- 例外: 「2018年〜2026年の市場推移」のような時系列分析記事は最新トレンドとして残してよい

【スコア配分】
- value_score=85+ は本当に重要な業界動向のみ（主要メーカー/小売の新発表、市場の大きな変化等）
- 一般的な新商品・ECニュースは 60〜80
- ベビー用品関連だが事業判断に直結しない記事は 30〜50
- 同じ value_axis を5件以上 score 80+ にしない（多様性確保）

【各項目の出力ルール】
- article_id: 入力の id をそのまま文字列で返す
- value_score: 0-100。85+は必読
- why_matters_jp: 事業/商品判断にどう効くかを1文（80文字以内・結論ファースト）
- action_hint_jp: 商品担当が今日取るべき動作を動詞始まりで（10〜60文字）
  例: 「対象SKUの取扱有無を在庫確認」「西松屋の新PB商品と当社品の価格比較表を作成」「楽天のベビー特集ページの構成を確認」
- ノイズ記事も items に含めて is_relevant=false にする。why と action は短くて構わない（5文字以上）

【記事リスト】
{json.dumps(compact, ensure_ascii=False, indent=2)}
"""


def ai_rank_articles(articles: list[dict]) -> tuple[list[dict], bool]:
    """ルールスコア上位の記事を AI で再評価し、value_score 降順で返す。

    Returns: (enriched_articles, ai_used: bool)
    """
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("[SKIP] AI ranker: ANTHROPIC_API_KEY 未設定 → ルールスコアのまま使用")
        return articles, False

    if not articles:
        return articles, False

    try:
        from anthropic import Anthropic
    except ImportError:
        print("[SKIP] AI ranker: anthropic パッケージ未インストール → ルールスコアのまま使用")
        return articles, False

    candidates = articles[:MAX_CANDIDATES]
    compact = [
        {
            "id": str(i),
            "title": (a.get("title") or "")[:150],
            "summary": (a.get("summary") or "")[:200],
            "source_name": a.get("source_name", ""),
            "source_type": a.get("source_type", ""),
            "url": (a.get("url") or "")[:120],
            "language": a.get("language", "ja"),
            "matched_keywords": (a.get("matched_keywords") or [])[:8],
            "published": (a.get("published") or "")[:10] or "unknown",
            "rule_score": a.get("score", 0),
        }
        for i, a in enumerate(candidates)
    ]

    try:
        client = Anthropic(api_key=api_key)
        model = os.environ.get("ANTHROPIC_MODEL", DEFAULT_MODEL)
        resp = client.messages.create(
            model=model,
            max_tokens=MAX_OUTPUT_TOKENS,
            tools=[RANK_TOOL],
            tool_choice={"type": "tool", "name": "rank_baby_news"},
            messages=[{"role": "user", "content": _build_prompt(compact)}],
        )
        usage = getattr(resp, "usage", None)
        stop_reason = getattr(resp, "stop_reason", "?")
        if usage:
            print(
                f"[DEBUG] AI usage: in={usage.input_tokens} out={usage.output_tokens} "
                f"stop_reason={stop_reason}"
            )
    except Exception as e:
        print(f"[WARN] AI ranker API失敗: {e} → ルールスコアのまま使用")
        return articles, False

    tool_use = next(
        (b for b in resp.content if getattr(b, "type", None) == "tool_use"),
        None,
    )
    if tool_use is None:
        print("[WARN] AI ranker: tool_use 出力なし → ルールスコアのまま使用")
        return articles, False

    items = tool_use.input.get("items", [])
    if not items:
        print(
            f"[WARN] AI ranker: items 空。tool_use.input keys={list(tool_use.input.keys())}"
        )
        return articles, False

    ai_by_id = {str(item.get("article_id")): item for item in items}

    enriched: list[dict] = []
    dropped = 0
    for i, a in enumerate(candidates):
        ai = ai_by_id.get(str(i))
        if ai is None:
            enriched.append({**a, "ai_value_score": -1})
            continue
        if not ai.get("is_relevant", True):
            dropped += 1
            continue
        merged = {
            **a,
            "ai_value_score": ai.get("value_score", 0),
            "ai_value_axis": ai.get("value_axis", ""),
            "why_matters_jp": ai.get("why_matters_jp", ""),
            "action_hint_jp": ai.get("action_hint_jp", ""),
        }
        enriched.append(merged)

    enriched.sort(key=lambda x: x.get("ai_value_score", -1), reverse=True)

    print(
        f"[OK] AI ranker: {len(items)}件評価 / "
        f"{len(enriched)}件採用 / {dropped}件をノイズ除外"
    )
    return enriched, True
