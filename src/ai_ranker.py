"""ルールスコアで絞った候補をClaude APIで再評価する。

Mia（日本のベビー用品EC事業のカテゴリマネージャー）視点で記事を評価し、
各記事に value_score / value_axis / why_matters_jp / action_hint_jp を付加する。

設計原則:
- ANTHROPIC_API_KEY 未設定時は skip して入力をそのまま返す（Botは止めない）
- API失敗時も skip して入力を返す（フォールバックでルールスコアのまま動作）
- AI が is_relevant=False と判定した記事は除外
- 1日1回・~30件評価で月数百円以内に収まるようHaiku 4.5を既定モデルに採用
"""
import json
import os

DEFAULT_MODEL = "claude-haiku-4-5-20251001"
MAX_CANDIDATES = 30  # AIに渡す最大記事数（コスト管理）

RANK_TOOL = {
    "name": "rank_baby_news",
    "description": "Rank baby product news for a Japanese EC category manager.",
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
                            "description": "商品担当が読む価値があればtrue。ノイズはfalse",
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
                                "safety", "regulation", "product_launch",
                                "competitor", "retail", "market",
                                "consumer_trend", "noise",
                            ],
                            "description": "記事の主軸",
                        },
                        "why_matters_jp": {
                            "type": "string",
                            "minLength": 10,
                            "description": "なぜ商品担当に重要か。80文字以内・日本語・結論ファースト",
                        },
                        "action_hint_jp": {
                            "type": "string",
                            "minLength": 10,
                            "description": "今日取るべき次アクション。10〜60文字・日本語・動詞始まり。空文字や「特になし」は禁止",
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
    return f"""あなたは日本のベビー用品EC事業のカテゴリマネージャー向けニュース編集者です。
本日は {today}（JST）です。
以下の{len(compact)}件の記事を、商品担当が読む価値で評価してください。

【評価方針（重要度順）】
1. 国内のリコール・事故・安全（消費者庁・NITE・PSC・ST規格）は最優先
2. 主要日本ブランド（ピジョン/コンビ/アップリカ/カトージ/リッチェル/ユニチャーム/花王）の新商品・価格改定・販路変化
3. 主要日本小売（西松屋/赤ちゃん本舗/アカチャンホンポ/トイザらス/イオン/ニトリ/Amazon/楽天）の動向
4. 市場規模・消費者行動・EC/D2C変化
5. 海外（CPSC等）リコールは「日本にも輸入されているブランド」の場合のみ価値あり
6. 「おすすめランキング」「選び方ガイド」「育児コラム」「芸能人話題」は noise として弾く

【鮮度ルール（厳守）】
- published が本日から30日以上前の記事は value_score を 30 以下に抑える
- published が90日以上前の記事は基本 noise 扱い（is_relevant=false）
- ただし「現在進行中の重大リコール継続案件」は例外として残してよい

【出力ルール】
- value_score は厳しめに（70以上は意思決定に直結する内容のみ）
- why_matters_jp は「事業/商品判断にどう効くか」を結論ファーストで1文。一般的な感想は禁止
- action_hint_jp は **必ず10文字以上で記入**。動詞始まりで具体的に
  良い例: 「対象SKUの取扱有無を在庫確認」「PSC表示要件を商品ページで確認」「競合品との比較表を作成」
  悪い例: 「特になし」「確認」「" "」「null」← これらは禁止
- ノイズと判断した記事は is_relevant=false にして noise 軸に分類（その場合も why と action はダミーでよいので10文字以上で書く）
- 記事の article_id は入力の id をそのまま返す

【記事リスト】
{json.dumps(compact, ensure_ascii=False, indent=2)}

すべての記事について rank_baby_news ツールで結果を返してください。
"""


def ai_rank_articles(articles: list[dict]) -> list[dict]:
    """ルールスコア上位の記事をAIで再評価し、上位を value_score 降順で返す。

    Args:
        articles: ルールスコア降順の記事リスト
    Returns:
        AI評価で is_relevant=True だった記事を value_score 降順で返す。
        AI失敗時は入力をそのまま返す（フォールバック）。
    """
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("[SKIP] AI ranker: ANTHROPIC_API_KEY 未設定 → ルールスコアのまま使用")
        return articles

    if not articles:
        return articles

    try:
        from anthropic import Anthropic
    except ImportError:
        print("[SKIP] AI ranker: anthropic パッケージ未インストール → ルールスコアのまま使用")
        return articles

    candidates = articles[:MAX_CANDIDATES]
    compact = [
        {
            "id": str(i),
            "title": (a.get("title") or "")[:150],
            "summary": (a.get("summary") or "")[:200],
            "source": a.get("source_name", ""),
            "lang": a.get("language", "ja"),
            # AIに鮮度判断させるため日付（YYYY-MM-DD）を渡す
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
            max_tokens=4000,
            tools=[RANK_TOOL],
            tool_choice={"type": "tool", "name": "rank_baby_news"},
            messages=[{"role": "user", "content": _build_prompt(compact)}],
        )
    except Exception as e:
        print(f"[WARN] AI ranker API失敗: {e} → ルールスコアのまま使用")
        return articles

    tool_use = next(
        (b for b in resp.content if getattr(b, "type", None) == "tool_use"),
        None,
    )
    if tool_use is None:
        print("[WARN] AI ranker: tool_use 出力なし → ルールスコアのまま使用")
        return articles

    items = tool_use.input.get("items", [])
    ai_by_id = {str(item.get("article_id")): item for item in items}

    enriched: list[dict] = []
    dropped = 0
    for i, a in enumerate(candidates):
        ai = ai_by_id.get(str(i))
        if ai is None:
            # AI評価が無かった記事は中位扱いで残す
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
    return enriched
