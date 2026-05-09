# Baby Goods News Quality Rubric — 業界動向特化版

## 目的
日本のベビー用品EC事業（カテゴリ担当・MD・MGR）が「業界動向把握に値するニュース」を定義する。
収集→重複排除→重要度判定→要約→配信のすべてのステップでこの基準を参照する。

**スコープ**: メーカー動向 / 小売・EC動向 / 市場・消費者トレンド / 新商品 / 業界横断
**対象外**: リコール・回収・安全性・規制（HARD_NOISE で入口排除済み。事業判断ではなく安全管轄）

---

## 4軸の評価

各記事を以下4軸で1〜5点評価する。総合 importance を High / Medium / Low に分類する。

### 1. Source Quality（情報源の信頼度）

| Score | 例 |
|------:|---|
| 5 | 企業IR・公式PR：ピジョン/コンビ/アップリカ/ユニチャーム/花王 等の公式発表 |
| 5 | 主要小売公式：西松屋/赤ちゃん本舗/トイザらス 等の公式アナウンス |
| 5 | 業界専門誌・調査会社：矢野経済研究所、富士経済、NielsenIQ、JETRO |
| 4 | 業界専門メディア：通販新聞、流通新聞 |
| 3 | プレスリリース配信：PR TIMES、@Press（中身が公式PRの場合のみ）|
| 3 | 大手新聞・通信社：日経、朝日、ロイター、Bloomberg のベビー関連記事 |
| 2 | Google News配信の一般メディア：地方紙、業界ブログ |
| 1 | SEOまとめサイト、おすすめランキングサイト、転載記事、PR目的の個人ブログ |

### 2. Business Relevance（事業との関連度）

| Score | 例 | value_axis |
|------:|---|---|
| 5 | 主要競合の新商品・価格改定・販路変化 | manufacturer |
| 5 | 主要小売の店舗・EC施策、PB投入、サブスク開始 | retail |
| 4 | 市場規模・カテゴリ別シェア・売上トレンド | market |
| 4 | 新商品・新サービス発売（中堅含む）| product_launch |
| 3 | 消費者行動・ライフスタイル変化 | consumer_trend |
| 3 | 業界横断（提携・買収・展示会）| industry |
| 1 | ベビー用品EC事業に無関係 | noise |

### 3. Actionability（次アクションへの繋がり）

| Score | 例 |
|------:|---|
| 5 | 「対象SKUの取扱有無を在庫確認」「西松屋の新PB商品と当社品の価格比較表を作成」など、当日対応すべき具体動作 |
| 4 | 「競合品との比較表を作成」「カテゴリの仕入れ計画を見直し」など、1週間以内にやるべき動作 |
| 3 | 「市場トレンドとして社内共有」「中期計画の参考にする」など、知識として活用 |
| 2 | 「観察対象として記録」程度 |
| 1 | 「知って終わり」「アクションに繋がらない」 |

### 4. Output Quality（配信品質）

| 項目 | 基準 |
|---|---|
| URL有効性 | 配信前に最低限 HTTP 接続検証（上位7件のみ）。失敗時は importance=Low に格下げ |
| 事実と示唆の分離 | `fact_summary`（事実）と `business_implication / why_it_matters`（事業示唆）が別フィールド |
| 重複統合 | 似たタイトルは `duplicate_group_id`（10桁MD5）で同定。代表1件のみ表示 |
| 重要度ラベル | 各記事に `importance: High / Medium / Low` |
| なぜ重要か | 1〜2文の `why_it_matters` が必ず付く |

---

## 総合 Importance の決定ルール

```
combined = (source_quality + business_relevance + actionability) / 3

importance =
  High   if combined >= 4.0 かつ business_relevance >= 4
  Medium if combined >= 3.0
  Low    それ以外
```

**強制 Low**:
- `is_relevant = false` （AIが「無関係」と判定）
- `link_status = failed`

旧版にあった「safety/regulation×80+ を強制 High」ルールは撤廃（リコールは入口で排除済み）。

---

## 配信フォーマット

### Telegram

全ハイライト（importance=Low 以外）を統一フォーマットで配信。

```
[1] 【High】 🏬 小売・EC
  西松屋、PB「SmartAngel」新ベビーカー発売
  Source: 西松屋公式
  Fact: 西松屋がPBブランドの新ベビーカーを4/15発売、価格14,800円
  Why: 競合PB投入。価格・棚割の見直しが必要
  Action: 自社該当カテゴリの価格比較表を作成
  URL: 記事を開く

[2] 【Medium】 🏭 メーカー
  ピジョン、新型哺乳瓶リリース
  ...
```

末尾に「今日のアクション」3件 + 日次レポートリンクボタン。

### HTML レポート

各記事カードに：
- 重要度バッジ（High=赤 / Medium=黄 / Low=灰）
- 軸バッジ（manufacturer / retail / ...）
- タイトル（クリックで元記事へ）
- Fact / Why it matters / Action の3行構成
- ソース名 / 公開日 / 4軸スコアミニ表示
- link_status=failed 警告（赤字）

---

## 評価ループ

1. **収集時**：fetcher で source_quality_score を `source_type` から仮決定
2. **AI評価時**：ai_ranker で value_axis（7軸）と value_score を導出
3. **配信前**：rubric.compute_importance() で総合 importance を決定 + 上位7件のリンク検証
4. **配信後**：Telegram/HTML に importance + 軸ラベルとともに表示
5. **次回改善**：実際の閲覧データを見て rubric の閾値・キーワード辞書を見直す

---

## High スコアになるべき記事の例

- 「ピジョン、2026年度第2四半期決算 哺乳瓶事業が前年比15%増」（source=5, relevance=5, action=4 → High）
- 「西松屋、PB『SmartAngel』ベビーフード新発売」（source=4, relevance=5, action=4 → High）
- 「楽天、ベビー用品カテゴリの売上が前年比20%成長」（source=3, relevance=4, action=4 → High/Medium）

## Low スコアになるべき記事の例（HARD_NOISE / is_relevant=false）

- 「【2026年版】ベビーカーおすすめランキング50選」（HARD_NOISE）
- 「子育てあるあるエピソード集」（is_relevant=false / SOFT_NOISE）
- 「芸能人〇〇さん、第二子誕生をインスタで報告」（HARD_NOISE）
- 「[消費者庁リコール] 〇〇商品自主回収のお知らせ」（HARD_NOISE: リコール語）

---

## 履歴

- v1.0: 初版（4軸+importance+リコール強制High）
- v2.0: 業界動向特化版。リコール/規制関連を全面撤廃。value_axis を「メーカー/小売/市場/消費者/新商品/業界/ノイズ」7軸に再構成。
