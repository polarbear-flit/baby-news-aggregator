# Baby Goods News Quality Rubric

## 目的
日本のベビー用品EC事業（カテゴリ担当・MD・MGR）が「読む価値のあるニュース」を定義し、
収集→重複排除→重要度判定→要約→配信のすべてのステップでこの基準を参照する。

## 4軸の評価

各記事を以下4軸で1〜5点評価する。総合 importance を High / Medium / Low に分類する。

---

### 1. Source Quality（情報源の信頼度）

| Score | 例 |
|------:|---|
| 5 | 公的機関：消費者庁、NITE、経産省、こども家庭庁、国民生活センター、CPSC、CAA |
| 5 | リコール公式：消費者庁リコール情報、メーカー自主回収プレスリリース |
| 4 | 企業IR・公式PR：ピジョン/コンビ/アップリカ/ユニチャーム/花王 等の公式発表 |
| 4 | 主要小売公式：西松屋/赤ちゃん本舗/トイザらス 等の公式アナウンス |
| 4 | 業界専門誌・調査会社：矢野経済研究所、富士経済、NielsenIQ、JETRO |
| 3 | プレスリリース配信：PR TIMES、@Press（中身が公式PRの場合のみ）|
| 3 | 大手新聞・通信社：日経、朝日、ロイター、Bloomberg のベビー関連記事 |
| 2 | Google News配信の一般メディア：地方紙、業界ブログ |
| 1 | SEOまとめサイト、おすすめランキングサイト、転載記事、PR目的の個人ブログ |

**運用ルール**：
- `source_type` フィールド（official_recall / brand_official / google_news 等）を1次判定
- AIがタイトル/要約から「これは公式PRの転載か、SEO記事か」を判定して微調整

---

### 2. Business Relevance（事業との関連度）

| Score | 例 |
|------:|---|
| 5 | リコール・回収・PSC規制・法改正・安全基準改定（直接的な販売リスク） |
| 5 | 主要競合の新商品・価格改定・販路変化（自社の打ち手に直結） |
| 4 | 主要小売の店舗・EC施策、PB投入、サブスク開始（販売チャネル動向） |
| 4 | 市場規模・カテゴリ別シェア・消費者行動変化（戦略立案に効く） |
| 3 | ベビー用品全般のトレンド、新素材・新技術の話題 |
| 2 | 一般的な育児コラム、専門家インタビュー（具体的事業示唆なし） |
| 1 | 子育てあるある、芸能人の子育て、選び方ガイド、おすすめランキング |

**運用ルール**：
- AI の `value_axis`（safety/regulation/product_launch/competitor/retail/market/consumer_trend/noise）から導出
- `noise` 軸は score=1（is_relevant=false）

---

### 3. Actionability（次アクションへの繋がり）

| Score | 例 |
|------:|---|
| 5 | 「対象SKUの取扱有無を在庫確認」「PSC表示要件を商品ページで確認」など、当日対応すべき具体動作 |
| 4 | 「競合品との比較表を作成」「カテゴリの仕入れ計画を見直し」など、1週間以内にやるべき動作 |
| 3 | 「市場トレンドとして社内共有」「中期計画の参考にする」など、知識として活用 |
| 2 | 「観察対象として記録」「クォータリーレビューで触れる」程度 |
| 1 | 「知って終わり」「アクションに繋がらない」「具体的でない」 |

**運用ルール**：
- AI の `action_hint_jp` の有無・具体性から導出
- 動詞始まり（確認・作成・見直し・調査）かつ10文字以上で score≥3
- Importance = High の記事は score≥4 が望ましい

---

### 4. Output Quality（配信品質）

各配信メッセージ・HTMLレポートが以下を満たすこと。これは **記事ごと** ではなく **配信全体** の評価軸。

| 項目 | 基準 |
|---|---|
| URL有効性 | 配信前に最低限 HTTP 接続検証。失敗時は除外or `link_status=failed` |
| 事実と示唆の分離 | `fact_summary`（RSS要約）と `business_implication`（why_matters_jp）が別フィールド |
| 重複統合 | 似たタイトルの記事は `duplicate_group_id` でまとめ、代表1件のみ表示 |
| 重要度ラベル | 各記事に `importance: High / Medium / Low` |
| なぜ重要か | 1〜2文の `why_it_matters` が必ず付く（High/Medium のみ） |

---

## 総合 Importance の決定ルール

```
combined = (source_quality + business_relevance + actionability) / 3

importance =
  High   if combined >= 4.0 かつ business_relevance >= 4
  Medium if combined >= 3.0
  Low    それ以外
```

ただし以下は強制的に High：
- `value_axis = safety` かつ `value_score >= 80`（重大リコール）
- `value_axis = regulation` かつ `value_score >= 80`（PSC等の法改正）

以下は強制的に Low：
- `is_relevant = false`
- `link_status = failed`

---

## 配信フォーマット

### Telegram（importance: High のみフルブロック）

```
【High】タイトル
Source: 媒体名
URL: ...
Fact: 事実要約を1〜2文
Why it matters: ベビー用品EC事業への意味
Action hint: 見るべき観点 or 次アクション
```

Medium は1行（タイトル＋ソース）、Low は配信しない。

### HTMLレポート

各記事カードに以下を表示：
- 重要度バッジ（High=赤 / Medium=黄 / Low=灰）
- タイトル（クリックで元記事へ）
- Source / 公開日
- Fact summary
- Why it matters
- Action hint（あれば）
- 4軸スコア（小さく表示）

---

## 評価ループ

1. **収集時**：fetcher で source_quality_score を `source_type` から仮決定
2. **AI評価時**：ai_ranker で business_relevance_score・actionability_score を AI から導出
3. **配信前**：rubric.compute_importance() で総合 importance を決定 + リンク検証
4. **配信後**：Telegram/HTML に importance とともに表示
5. **次回改善**：実際の閲覧データ（クリック率・「読んだ」フィードバック）を見て rubric を見直す

---

## 出典の例：High スコアになるべき記事

- 「消費者庁、ベビーカーのPSCマーク表示義務化を施行」（source=5, relevance=5, action=5 → High）
- 「ピジョン、新型哺乳瓶のリコール開始」（source=5, relevance=5, action=5 → High）
- 「西松屋、PB『SmartAngel』ベビーフード新発売」（source=4, relevance=4, action=4 → High）

## 出典の例：Low スコアになるべき記事

- 「【2026年版】ベビーカーおすすめランキング50選」（source=1, relevance=1, action=1 → Low）
- 「子育てあるあるエピソード集」（source=2, relevance=1, action=1 → Low）
- 「芸能人〇〇さん、第二子誕生をインスタで報告」（source=2, relevance=1, action=1 → Low）
