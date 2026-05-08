"""ルールスコアで絞った候補をClaude APIで再評価する。

Mia（日本のベビー用品EC事業のカテゴリマネージャー）視点で記事を評価し、
各記事に value_score / value_axis / why_matters_jp / action_hint_jp を付加する。

設計原則:
- ANTHROPIC_API_KEY 未設定時は skip して入力をそのまま返す（Botは止めない）
- API失敗時も skip して入力を返す（フォールバックでルールスコアのまま動作）
- AI が is_relevant=False と判定した記事は除外
- 1日1回・~30件評価で月数百円以内に収まるよう Haiku 4.5 を既定モデルに採用
- ai_used フラグを返り値で返し、Telegram通知で「AI未実行」を明示できるようにする
"""
import json
import os

DEFAULT_MODEL = "claude-haiku-4-5-20251001"
MAX_CANDIDATES = 30  # main.py の rule_top と揃える
MAX_OUTPUT_TOKENS = 12000  # 30件×~250tokens の出力に余裕を持たせる

RANK_TOOL = {
    "name": "rank_baby_news",
    "description": "Rank baby product news for a Japanese EC category manager.",
    # 厳格スキーマ検証: required と enum を厳密に守らせる
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
    return f"""あなたは日本のベビー用品EC事業のカテゴリマネージャー向けニュース編集者です。
本日は {today}（JST）です。
以下の{len(compact)}件の記事を1件ずつ評価し、rank_baby_news ツールの items 配列に **必ず{len(compact)}件すべて** 含めて返してください。

【ベビー用品EC事業との関連性 — 厳格に判定】
記事内容が以下のベビー・子供向け商品カテゴリーと直接関係しない場合は **必ず is_relevant=false**:
- 哺乳瓶・授乳・ミルク・離乳食・ベビーフード
- おむつ・おしりふき・ウェットシート
- ベビーカー・チャイルドシート・抱っこ紐
- ベビースキンケア（ローション・ソープ・オイル）
- ベビー服・肌着・スタイ
- 玩具（赤ちゃん・幼児向け）・知育玩具
- ベビーベッド・バウンサー・ハイチェア

無関係なため除外すべき例:
- 一般大人向け食品（サラミ・ハム・塩昆布・菓子等）
- 大人向け化粧品・健康食品
- 一般小売の食品部門・大人向けPR
- 子育てライフスタイルコラム（具体的商品情報なし）
- 芸能人・有名人の子育て話題

【評価方針（重要度順）】
1. 国内のリコール・事故・安全（消費者庁・NITE・PSC・ST規格）— ただしベビー用品関連のみ
2. 主要日本ブランド（ピジョン/コンビ/アップリカ/カトージ/リッチェル/ユニチャーム/花王）の新商品・価格改定・販路変化
3. 主要日本小売（西松屋/赤ちゃん本舗/アカチャンホンポ/トイザらス/イオン/ニトリ/Amazon/楽天）のベビー用品関連動向
4. 市場規模・消費者行動・EC/D2C変化
5. 海外CPSCリコールは日本に輸入されるベビー用品ブランドの場合のみ価値あり

【スコア配分の重要原則 — 厳守】
- リコール・規制系（safety/regulation）は「本当に重要な1件」だけ高得点(85+)にする
- 同じ商品の継続リコール、海外CPSCの細かい案件、すでに広く知られている案件は 60〜75 に抑える
- カテゴリマネージャーは「安全 + 競合 + 小売 + 市場」のバランスを見たいので、
  上位5件は safety/regulation 合計1件まで、他は product_launch / competitor / retail / market を散らす
- safety/regulation の高得点(80+)は最大で1件のみ（最重要案件のみ）
- 「全部 recall」になりそうなら、2件目以降は 60 以下に下げる

【鮮度ルール】
- published が本日から30日以上前の記事は value_score を 30 以下
- 90日以上前は is_relevant=false で構わない
- ⚠️ Google News RSSは古い記事を再インデックスするとpubDateを更新するため、published 日付だけを信用しない:
  - タイトル/要約に「2024年」「2025年」「昨年」「去年」等の過去年言及があれば is_relevant=false
  - 「○○年版」「20XX年X月X日に発表」など過去年が記事の主題になっている場合も is_relevant=false

【無関係記事の除外】
- 東京ばな奈・セブンイレブン・バーガーキング等のベビー用品と無関係な商品は is_relevant=false
- ベビー用品文脈がない地域ニュース（閉店・開店・地域フェア）は is_relevant=false

【各項目の出力ルール】
- article_id: 入力の id をそのまま文字列で返す
- value_score: 0-100。70以上は意思決定に直結する内容のみ
- why_matters_jp: 事業/商品判断にどう効くかを1文（80文字以内）
- action_hint_jp: 商品担当が今日取るべき動作を動詞始まりで（10〜60文字）
  例: 「対象SKUの在庫を確認」「PSC表示要件を商品ページで確認」「競合品と比較表を作成」
- ノイズ記事も items に含めて is_relevant=false にする。why と action は短くて構わない（5文字以上）

【記事リスト】
{json.dumps(compact, ensure_ascii=False, indent=2)}
"""


def ai_rank_articles(articles: list[dict]) -> tuple[list[dict], bool]:
    """ルールスコア上位の記事をAIで再評価し、value_score 降順で返す。

    Args:
        articles: ルールスコア降順の記事リスト
    Returns:
        (enriched_articles, ai_used)
        - enriched_articles: AI評価で is_relevant=True だった記事を value_score 降順で返す。
          AI失敗時は入力をそのまま返す（フォールバック）。
        - ai_used: AIが実際に有効な評価を返したかどうか
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
            f"[WARN] AI ranker: items 空。tool_use.input keys={list(tool_use.input.keys())} "
            f"raw={str(tool_use.input)[:500]}"
        )
        return articles, False

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
    return enriched, True
