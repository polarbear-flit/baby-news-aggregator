# baby-news-aggregator 改善引き継ぎ書 v1

- 作成日: 2026-07-08
- 作成: Claude（レビュー・プラン・検証基準担当）
- 対象リポジトリ: `C:\Users\littl\ClaudeLabs\baby-news-aggregator`（GitHub: polarbear-flit/baby-news-aggregator）
- 症状: 「使えるデータが乗ってこない」（毎朝のTelegram配信の情報価値が低い）

> **【2026-07-09 追記】P0〜P3 実装完了（Opus 4.8 が実施）。** 本文書は元の計画。
> 実装時に計画から変えた点は「§10 実装後メモ」に集約。テスト119件パス・ローカルドライラン
> 完走・cross-day dedup 実機確認済み。**未pushで、次回 GitHub Actions 定期実行（毎朝07:00 JST）
> から新ロジックが走る**。初回はdelivered.jsonが無く全件新着→翌日以降に「毎日同じ」抑制が効く。

---

## 0. TL;DR（結論）

Botは壊れていない。**毎日ほぼ同じ記事を配信し続けている**のが最大の問題。加えて、価値を運ぶはずだった高信頼ソース（メーカー公式・業界紙・市場調査の10フィード）が**採用0件で全滅**しており、配信の85%が汎用Google Newsクエリ由来になっている。

直すべきは4点（優先順）:

| 優先 | 施策 | 期待効果 |
|---|---|---|
| P0 | 配信済み記事の記憶（cross-day dedup）＋同一PRのクラスタ統合 | 「毎日同じ」が消える。体感インパクト最大 |
| P1 | ソース再設計: `site:`クエリ10本を廃止し、実在RSS＋`when:7d`付きクエリへ置換。キーワードフィルタの穴を修正 | 高価値ソースが実際に流れ込む |
| P2 | 鮮度ウィンドウ 90日→14日、ドメインdenylist | 3ヶ月前の「新商品」やスパムが消える |
| P3 | AIプロンプト強化（Why/Actionの定型文禁止・クラスタ判定の追加） | 1件あたりの読む価値が上がる |

---

## 1. 診断: なぜ「使えるデータが乗ってこない」のか

### 原因1【最重要】: 配信済み記事の記憶がなく、同じ記事が何日も再配信される

- `data/history.json` に保存しているのは**キーワード頻度のみ**。どの記事を配信したかは一切記録していない。
- スコアリングは決定的（ソース重み＋企業名＋業界語＋鮮度）なので、強いPR記事は鮮度ペナルティで沈むまで**毎日勝ち続ける**。
- **実測**: 直近レポート間のタイトル重複は 27/40（前日比68%）、3日前とでも 30/40。
- **実測**: Telegram相当の上位7件は、07-04〜07-07の4日間でほぼ同一（「アップリカ クルリラ」が4日連続1位、「トイザらスPOS+」「MiLスマート成長食」「ALOBABY無香」が毎日登場）。

→ ユーザーは毎朝「昨日と同じ話」を受け取っている。これが体感の正体。

### 原因2: 高価値ソース（10フィード）が採用0件で全滅

`config.py` の `site:` 型 Google News クエリは「ニュース」ではなく**そのドメインのインデックス済みページ全部**を返す。実測結果（2026-07-08 ローカル実行）:

| フィード | 取得 | 採用 | 死因 |
|---|---|---|---|
| Pigeon 公式 | 20 | **0** | 2017〜2019年のQ&A・商品ページばかり → 90日超で全滅 |
| ユニチャーム ベビー部門 | 20 | **0** | 2016〜2024年の古いリリース・FAQ → 90日超 |
| 花王 ベビー部門 | 20 | **0** | 製品Q&Aページばかり → 90日超 |
| コンビ / リッチェル 公式 | 20 | **0** | 同上 |
| 西松屋 公式 | 20 | **0** | 2012〜2024年の**店舗案内ページ** → 90日超 |
| Diamond Retail Media | 20 | **0** | 古記事＋キーワード不一致 |
| WWD Japan / 通販新聞 | 20/13 | **0** | 同上 |
| 矢野経済研究所 / 富士経済 | 20 | **0** | **キーワード不一致**（下記原因3） |

結果、配信81件の内訳は google_news 69 / pr_wire 9 / retailer_official 3。「業界動向特化」の設計が実質機能していない。

### 原因3: キーワードフィルタが最重要記事を落とす

`KEYWORDS` に素の「ベビー」がない（「ベビー用品」「ベビー服」等の複合語のみ）。このため実測で:

- 矢野経済研究所「**ベビー関連ビジネス市場**に関する調査を実施（2026年）」→ kw不一致で除外（本来この Bot の最高価値記事）
- ダイヤモンド「しまむら、**ベビー・子ども用品**『バースデイ』のオンラインストア開設」→ kw不一致で除外

「ベビー用品」は「ベビー・子ども用品」「ベビー関連」に部分一致しない。**フィルタが一番欲しい記事を弾いている。**

### 原因4: 同一PRのワイヤー重複が配信枠を食い潰す

同じプレスリリースが PR TIMES / 共同通信PRワイヤー / 公式サイト / 転載メディアで別タイトルになり、`fuzz.ratio ≥ 88` では検出できない。実測: 07-07朝の上位7件のうち3件が同一の「ALOBABY無香タイプ」。5枠しかないTelegramハイライトで同じ話が複数枠を占有する。

### 原因5: ノイズとスパムの通過

最新レポート40件に以下が混入:

- `richardajkeys.com` — P&Gのリリースを盗用したスクレイパースパム
- Fortune Business Insights の機械翻訳SEOレポート ×3（「おしゃぶりの市場規模、シェア、2034」等）
- 地域イベント記事 ×3（「赤ちゃんハイハイレース in イオンモール三光」）
- マイベスト「カトージのベビーカーおすすめ人気ランキング」（SOFT_NOISE -20 では沈みきらない）
- 3月27日発売商品が7月に「新商品」として上位表示（90日ウィンドウが日次ブリーフには長すぎる）

### 補足（軽微・ついでに直す）

- Actions のコミットメッセージ `date +'%Y-%m-%d %H:%M JST'` は**UTC時刻にJSTラベル**を付けている（`TZ` がそのstepに未設定）。
- 「急上昇キーワード」は「赤ちゃん」「ベビーカー」等の汎用語の頻度比較で情報価値ゼロ。
- 「カテゴリ別インサイト」はテンプレ文（「今期はN件。比較的静穏。」）で情報価値ゼロ。
- `daily_summary` 自体は良質（実物確認済み）。ただし入力記事が毎日同じなので、サマリも毎日似る。→ P0が直れば自然に直る。

---

## 2. 証拠の再現手順（実装AIが検証に使える）

```bash
# 1) 日次重複率の計測（要 git fetch 済み）
python -X utf8 scripts/check_overlap.py   # ※新規作成。5節のサンプル参照

# 2) フィード別の採用状況
python -X utf8 -c "from src.fetcher import fetch_all_feeds; fetch_all_feeds()"
# → [OK] 各フィード: N件採用 のログで 0件フィードを確認

# 3) when:7d の効果（検証済み: 全56件が7日以内になる）
# https://news.google.com/rss/search?q=ベビー用品+when:7d&hl=ja&gl=JP&ceid=JP:ja
```

検証済みの代替RSS（2026-07-08 に取得成功を確認）:

| ソース | URL | 件数 |
|---|---|---|
| PR TIMES 全件 | `https://prtimes.jp/index.rdf` | 200件 |
| 流通ニュース | `https://www.ryutsuu.biz/feed` | 50件 |
| ダイヤモンド・チェーンストア | `https://diamond-rm.net/feed/` | 10件 |

※ ユニ・チャーム `news.rss` は404（存在しない）。メーカー公式は無理にRSS化せず、Google News `when:` 付きクエリで拾う方針にする（下記）。

---

## 3. 実装仕様

### P0-1: 配信済み記事の記憶（cross-day dedup）

新ファイル `data/delivered.json` を追加し、**配信（レポート掲載）した全記事**を記録する。

```json
{
  "articles": [
    {
      "url_norm": "https://prtimes.jp/main/html/rd/p/....html",
      "title_norm": "アップリカクルリラビッテエックスプラスac...",
      "group_id": "a3f9c02b1e",
      "cluster_key": "アップリカ|クルリラ",
      "first_seen": "2026-07-04",
      "last_delivered": "2026-07-07",
      "delivered_count": 4
    }
  ]
}
```

処理フロー（`main.py` の `fetch_all_feeds()` 直後に挿入）:

1. `delivered.json` を読み込み（`TREND_WINDOW_DAYS`=30日より古いレコードは掃除）。
2. 各記事について既配信判定: ①正規化URL一致 ②`normalize_title` の fuzz ≥ 88 ③`cluster_key` 一致（P0-2参照）のいずれか。
3. 既配信記事は**除外ではなく降格**: `a["redelivery"] = True` を付け、AIリランカー候補・Telegram上位から除外。HTMLレポートには「既報」バッジ付きで末尾掲載（続報を見逃さないため）。
   - 例外: タイトルに続報シグナル（「続報」「追加」「拡大」「発表」＋前回と fuzz < 70）がある場合は新規扱い。判定に迷う実装は不要— まず単純に「URL・タイトル・クラスタ一致＝再配信」でよい。
4. 実行末尾で、今回レポートに掲載した全記事を `delivered.json` へ upsert し、Actions の `git add` 対象に `data/delivered.json` を追加する。

### P0-2: ワイヤー重複のクラスタ統合

AIリランカーに既に30件渡しているので、スキーマに1フィールド足すのが最安:

- `RANK_TOOL` の items に `"cluster_id": {"type": "integer", "description": "同一の出来事/プレスリリースを指す記事は同じ番号。単独記事は自分のidと同じ番号"}` を追加。
- プロンプトに「同じ商品・同じ発表を別媒体が報じたものは同一クラスタ。クラスタ内で最も情報量が多い1件だけを高スコアにし、残りは value_score を 30 未満にする」を追記。
- `main.py` 側: 同一 `cluster_id` からは最高スコア1件のみを Telegram/上位に採用。`cluster_key`（企業名|商品名の粗いキー）を `delivered.json` に保存し、翌日以降の再配信判定にも使う。
- AI失敗時のフォールバック: fuzz 閾値を88→80に下げた第二パスで近似クラスタリング（誤爆してもハイライト5件の多様性が上がる方向なので安全）。

### P1-1: ソース再設計（config.py の RSS_FEEDS 置換）

方針: 「`site:` 型クエリ全10本を廃止」「純正RSSがあるものは直接取得」「Google News クエリには全て `when:7d` を付与」。

```python
RSS_FEEDS = [
    # === 純正RSS（キーワードフィルタで絞る前提。source_typeの重みを活かす）===
    {"name": "PR TIMES 全件", "url": "https://prtimes.jp/index.rdf",
     "category": "general", "language": "ja", "source_type": "pr_wire", "fetch_type": "rss"},
    {"name": "流通ニュース", "url": "https://www.ryutsuu.biz/feed",
     "category": "general", "language": "ja", "source_type": "trade_press", "fetch_type": "rss"},
    {"name": "ダイヤモンド・チェーンストア", "url": "https://diamond-rm.net/feed/",
     "category": "general", "language": "ja", "source_type": "trade_press", "fetch_type": "rss"},

    # === Google News（全クエリに when:7d を付ける。実測で古記事が消えることを確認済み）===
    {"name": "GNews: ベビー用品業界", "url": "https://news.google.com/rss/search?q=ベビー用品+(業界+OR+市場+OR+EC+OR+シェア+OR+売上)+when:7d&hl=ja&gl=JP&ceid=JP:ja", ...},
    {"name": "GNews: 主要メーカー", "url": "https://news.google.com/rss/search?q=(ピジョン+OR+コンビ+OR+アップリカ+OR+ユニ・チャーム+OR+メリーズ+OR+ムーニー)+(ベビー+OR+赤ちゃん+OR+乳幼児)+when:7d&hl=ja&gl=JP&ceid=JP:ja", "source_type": "google_news", ...},
    {"name": "GNews: 主要小売", "url": "https://news.google.com/rss/search?q=(西松屋+OR+アカチャンホンポ+OR+赤ちゃん本舗+OR+バースデイ+OR+ベビーザらス)+when:7d&hl=ja&gl=JP&ceid=JP:ja", ...},
    {"name": "GNews: 市場調査", "url": "https://news.google.com/rss/search?q=(矢野経済研究所+OR+富士経済+OR+市場調査)+(ベビー+OR+育児+OR+乳幼児)+when:7d&hl=ja&gl=JP&ceid=JP:ja", "source_type": "market_research", ...},
    # 既存のカテゴリ別クエリ（哺乳瓶/ベビーカー/おむつ/スキンケア）も when:7d を付けて維持
]
```

注意点:

- PR TIMES 全件RSSは200件/回。`MAX_ARTICLES_PER_FEED = 20` を**フィードごとに上書き可能**にし（`feed_config.get("max_articles", MAX_ARTICLES_PER_FEED)`）、PR TIMESは200件のままキーワードフィルタに通す（ベビー関連は数件/日しかないので処理量は問題ない）。
- `source_type` の格下げロジック（`_article_url_matches_site`）は `site:` クエリ廃止に伴い削除してよい。
- 純正RSS化により、公式ソースの `source_type` 重みが初めて実際に機能し始める点に注意（スコア分布が変わる。P2の閾値と合わせて調整）。

### P1-2: キーワードフィルタの穴修正

```python
"general": [..., "ベビー", "こども用品", "子ども用品", "キッズ", "ベビー・子ども"],
```

- 素の「ベビー」を追加（「ベビー関連」「ベビー・子ども用品」を拾うため）。
- 誤爆増（「ベビーカステラ」等）は HARD_NOISE とAIリランカーの `is_relevant=false` で吸収する設計とし、入口は広めに倒す。**入口で落とすと回収不能、入口を通せばAIで落とせる**（今回の教訓）。

### P2-1: 鮮度ウィンドウ短縮

- `MAX_ARTICLE_AGE_DAYS: 90 → 14`。日次ブリーフに3ヶ月前のニュースは不要。
- `when:7d` 併用でほぼ二重防御になる。`published` 不明の記事は現状どおり通す（analyzer側で-25減点済み）。
- analyzer の鮮度カーブも詰める: 24h以内 +15 / 72h以内 +5 / 7日以内 0 / それ以降 -30（「今日の」ブリーフなので直近を強く優遇）。

### P2-2: ドメインdenylist / allowlist

`config.py` に追加し、`fetcher.py` の `is_hard_noise` 相当の位置でURLベース判定:

```python
DOMAIN_DENYLIST = [
    "richardajkeys.com",             # スクレイパースパム（実配信で確認）
    "fortunebusinessinsights.com",   # 機械翻訳SEO市場レポート（実配信で確認）
    "my-best.com",                   # ランキングまとめ（実配信で確認）
    "jimosh",                        # 地域イベントメディア（ジモッシュ、実配信で確認）
]
DOMAIN_ALLOWLIST_BONUS = {           # スコア加点（任意・P2では denylist だけでも可）
    "prtimes.jp": 5, "ryutsuu.biz": 10, "diamond-rm.net": 10,
}
```

注意: Google News のリダイレクトURL（news.google.com）はドメイン判定できない。`source_name` 末尾の媒体名（タイトル末尾 ` - 媒体名`）でも判定できるよう、denylist は「URL または タイトル末尾媒体名」の両方に当てる。

### P3-1: AIプロンプト強化（ai_ranker.py）

- Why/Action の定型文対策。プロンプトに追記:
  - 「why_matters_jp / action_hint_jp には**記事固有の固有名詞か数字を必ず1つ以上**含める。『主要メーカーの動向を確認』のような、どの記事にも書ける一般文は禁止」
  - 「action_hint_jp の『営業に確認』は禁止。カテゴリマネージャー本人が今日できる行動（比較表作成・売場/ECページ確認・価格調査・仕様書取得）にする」
- cluster_id 追加（P0-2）。
- モデルは当面 Haiku のまま（コスト月200円弱）。プロンプト強化で不足なら `ANTHROPIC_MODEL=claude-sonnet-5` に環境変数1つで切替可能（月500〜700円程度の見込み。30記事×日次規模）。**まずプロンプトで粘る。**

### P3-2: 「新着なしの日」を正直に伝える

再配信除外後にHigh/Mediumが0件の日は、無理に埋めず:

```
📰 ベビー用品 業界動向 2026/07/09
本日、新しい重要ニュースはありません（既報の再掲を除外済み）。
直近の既報: アップリカ新型チャイルドシート（7/4既報）ほか → レポート参照
```

「同じ記事で埋まった配信」より「なしと言い切る配信」の方が信頼される。

### 軽微修正（ついで）

- `.github/workflows/news_update.yml` のコミットstepに `TZ: Asia/Tokyo` を設定（現状UTC時刻にJSTラベル）。
- `git add` に `data/delivered.json` を追加（P0-1）。
- 「急上昇キーワード」「カテゴリ別インサイト」はTelegramから削除してよい（情報価値ゼロ。HTMLには残置可）。Telegramは「サマリ＋ハイライト＋アクション」の3ブロックに絞る。

---

## 4. 検証基準（Acceptance Criteria）

実装完了の定義。**全て自動テストまたはスクリプトで機械的に判定できる**こと。

| # | 基準 | 判定方法 |
|---|---|---|
| AC-1 | 連続する2日の配信（Telegram相当上位7件）に、同一URL・同一クラスタ・fuzz≥80のタイトルが**0件** | 新規 `scripts/check_overlap.py` を7日分のgit履歴に対して実行 |
| AC-2 | `delivered.json` に配信記事が記録され、30日で自動掃除される | unittest（下記サンプル） |
| AC-3 | 同一クラスタ（同じPRの別媒体版）はTelegramハイライトに1件まで | unittest + 実配信レポート目視1回 |
| AC-4 | 配信記事の `published` は全て14日以内（published不明は除く） | unittest |
| AC-5 | denylistドメイン/媒体名の記事が配信に0件 | unittest |
| AC-6 | フィード採用0件が**3日連続**したフィードがあれば、Telegramメッセージ末尾に `⚠️ 無効フィード: <name>` を出す（ソース全滅の再発検知） | 実装＋unittest |
| AC-7 | Why/Action の80%以上が記事固有の固有名詞または数字を含む | 実配信3日分・上位5件×3日=15件を目視採点（実装AIが実施しレポート） |
| AC-8 | 既存91テストが全てパスし続ける | `python -X utf8 -m unittest discover tests` |
| AC-9 | ローカルドライラン（`BABY_NEWS_BOT_TOKEN` 未設定）で最初から最後まで完走 | 手動1回 |

### AC-1 検証スクリプトのサンプル（scripts/check_overlap.py として新規作成）

```python
"""直近N日のgit履歴からdocs/index.htmlの上位記事重複率を計測する。"""
import subprocess, re, sys

def top_titles(rev: str, n: int = 7) -> list[str]:
    html = subprocess.run(
        ["git", "show", f"{rev}:docs/index.html"],
        capture_output=True,
    ).stdout.decode("utf-8", errors="ignore")
    links = re.findall(
        r'class="font-semibold text-indigo-700[^"]*"[^>]*>\s*(.*?)\s*</a>', html, re.S)
    return [re.sub(r"\s+", " ", t).strip() for t in links[:n]]

revs = subprocess.run(
    ["git", "log", "--format=%h", "-8", "--", "docs/index.html"],
    capture_output=True, text=True).stdout.split()

ng = 0
for newer, older in zip(revs, revs[1:]):
    dup = set(top_titles(newer)) & set(top_titles(older))
    status = "NG" if dup else "OK"
    if dup:
        ng += 1
    print(f"[{status}] {newer} vs {older}: 上位7件の重複 {len(dup)} 件 {sorted(dup)[:2]}")
sys.exit(1 if ng else 0)
```

（fuzz≥80判定を足す場合は rapidfuzz を使い同様に比較。まず完全一致0を達成してから精密化でよい）

### AC-2 テストサンプル（tests/test_delivered_memory.py として新規作成・unittest形式）

```python
import unittest
from src.delivered import (  # 新モジュール想定
    is_already_delivered, upsert_delivered, prune_delivered,
)

class TestDeliveredMemory(unittest.TestCase):
    def test_same_url_is_redelivery(self):
        store = {"articles": [{"url_norm": "https://example.com/a",
                               "title_norm": "x", "cluster_key": "",
                               "last_delivered": "2026-07-07"}]}
        art = {"url": "https://example.com/a/", "title": "全然違うタイトル"}
        self.assertTrue(is_already_delivered(art, store))

    def test_similar_title_is_redelivery(self):
        store = {"articles": [{"url_norm": "u1",
                               "title_norm": "アップリカクルリラビッテエックスプラスac発売",
                               "cluster_key": "", "last_delivered": "2026-07-07"}]}
        art = {"url": "https://other.example/b",
               "title": "アップリカ「クルリラ ビッテ エックス プラス AC」発売！"}
        self.assertTrue(is_already_delivered(art, store))

    def test_fresh_article_passes(self):
        store = {"articles": []}
        art = {"url": "https://example.com/new", "title": "コンビが新工場を建設"}
        self.assertFalse(is_already_delivered(art, store))

    def test_prune_removes_old_records(self):
        store = {"articles": [{"url_norm": "u", "title_norm": "t",
                               "cluster_key": "", "last_delivered": "2026-05-01"}]}
        pruned = prune_delivered(store, today="2026-07-08", keep_days=30)
        self.assertEqual(len(pruned["articles"]), 0)
```

---

## 5. サンプル出力（Before / After）

### Before（実際の配信・07-04〜07-07で毎朝ほぼこれ）

```
📰 ベビー用品 業界動向 2026/07/07
【1】アップリカ『クルリラ ビッテ エックス プラス AC』…（※4日連続1位）
【2】コンビ、新チャイルドシートをアカチャンホンポで6月26日発売…（※3日連続）
【3】トイザらス全158店舗にPOS+導入…（※4日連続）
【4】ALOBABY ベビーソープ無香タイプ…（※同じPRが媒体違いで最大3枠）
【5】MiL・トイザらス・赤ちゃん本舗「スマート成長食」…（※3日連続）
```

### After(目標)

```
📰 ベビー用品 業界動向 2026/07/09
━━━━━━━━━━━━━
📌 今日の業界動向
【主軸: 小売・EC】しまむら「バースデイ」がECを本格強化。ベビー専門小売の
オンラインシフトが加速しており、価格帯の近い西松屋PBとの競合構図に変化。

今日のハイライト（新着のみ・既報は除外済み）
[1]【High】🏬 小売・EC
  しまむら、ベビー・子ども用品「バースデイ」のオンラインストア開設
  Fact (AI要約): しまむらが「バースデイ」EC事業を開始、300店舗網と連動…
  Why: 価格志向ベビー用品ECの直接競合が増える。送料・価格政策の比較が必要
  Action: バースデイECの送料無料ライン・主要SKU価格を自社と比較表に
[2]【High】📊 市場
  矢野経済研究所、ベビー関連ビジネス市場に関する調査を実施（2026年）
  Fact (AI要約): 2026年のベビー関連市場は前年比…
  Why: カテゴリ予算策定の根拠データ。縮小市場での単価上昇トレンドを確認
  Action: 調査サマリを入手し、担当カテゴリの市場規模前提を更新
[3]【Medium】🆕 新商品 …（新着のみ最大5件）

本日新着が少ない日の例:
「本日、新しい重要ニュースはありません（既報の再掲を除外済み）」
━━━━━━━━━━━━━
📄 日次レポートを開く
```

ポイント: ①全件が**新着**（既報は載らない）②同一PRは1枠まで ③純正RSS由来の業界紙・市場調査記事が実際に載る ④Why/Actionに固有名詞・数字が入る。

---

## 6. 実装の進め方（推奨順序）

1. **P0-1 + P0-2**（delivered.json＋クラスタ）→ AC-1/2/3。ここまでで体感は大きく変わる
2. **P1-1 + P1-2**(ソース置換＋キーワード穴)→ AC-6、フィード採用ログで全フィード>0件を確認
3. **P2**（鮮度14日＋denylist）→ AC-4/5
4. **P3**（プロンプト強化＋新着なし配信）→ AC-7
5. 3日間実運用を観察し、AC-1スクリプトとAC-7目視採点の結果を残す

## 7. 環境・規約（このリポジトリの約束事）

- Windows / Python 3.13ローカル、Actions は ubuntu + Python 3.11。ローカル実行は必ず `python -X utf8`
- テストは unittest（pytest未導入）。`python -X utf8 -m unittest discover tests`
- フォーマットは black。型ヒント必須。conventional commits（`feat:` `fix:`）
- **トークン・APIキーはいかなる出力にも直書きしない**（GitHub Secrets: `BABY_NEWS_BOT_TOKEN` / `BABY_NEWS_CHAT_ID` / `ANTHROPIC_API_KEY` 登録済み）
- Telegram送信を伴うテストはしない（ドライラン=環境変数未設定で確認）。本番送信の確認は翌朝の実配信で行う

## 8. スコープ外(やらないこと)

- 週次サマリー機能・英語フィード再追加（別イシュー）
- リコール情報の再導入（2026年に意図的に撤廃済み。HARD_NOISEで除外が正）
- HTMLレポートのデザイン変更（Tailwind CDN依存の解消等は今回対象外）
- Telegram Bot の双方向化

## 9. 未解決の論点（実装AIが判断してよいこと）

- 再配信の「降格」実装: HTMLに「既報」バッジ付き掲載 vs 完全除外。本書は前者を推奨（続報の見逃し防止）が、実装が重ければ完全除外でも可
- PR TIMES 全件RSS(200件/回)の処理コスト: キーワードフィルタ通過後は数件/日の見込みだが、実測して多すぎればカテゴリRSSへの絞り込みを検討
- cluster_key の粒度（企業名|商品名）: 誤統合（別商品を同一視）が観測されたらキーを細かくする

---

## 10. 実装後メモ（2026-07-09・計画からの変更点）

実装は計画どおり P0〜P3 を全て入れたが、ドライラン検証で以下を計画から修正した。

### 修正1: `site:` クエリは「全廃」ではなく「プレス/ニュース媒体は when: 付きで存続」
- 計画では「site:型クエリ全10本を廃止し純正RSSへ」としたが、純正RSS（`prtimes.jp/index.rdf`,
  `ryutsuu.biz/feed`, `diamond-rm.net/feed`）は**全ジャンル最新N件のスナップショット**で、
  ベビー記事がほぼ含まれず採用0件だった（実測: PR TIMES 全件200件中ベビー1件）。
- 正しい切り分け: `site:` が悪いのは**メーカー/店舗の公式ドメイン**（pigeon.co.jp 等＝静的な
  商品/店舗ページしか返さない）だけ。**プレス/ニュース媒体**（prtimes/ryutsuu/diamond-rm）は
  `site:媒体 (ベビー語) when:7d` にすれば「その媒体のベビー関連×直近」を横断検索でき、
  **PR TIMES で100件/日ヒット**した（実測）。→ config.py はこの形に修正済み。
- 教訓: ドメイン全体RSSより「Google News の site:+when: 横断検索」の方が、ニッチ×鮮度の両立に強い。

### 修正2: SEO市場予測レポートの専用フィルタを追加（計画になかった）
- denylist 通過後も「○○市場：2026年〜2032年 世界市場予測、CAGR、XX百万米ドル」型の
  機械翻訳SEOレポート（アットプレス/QYResearch/note 経由）が市場語+鮮度で上位化した。
- `fetcher.is_seo_market_report()` を新設: 「市場/market」を含み かつ ①2031年以降の未来年 or
  ②百万米ドル/CAGR/世界市場予測/QYResearch 等の signature、で除外。
- 正規の国内調査（矢野経済「ベビー関連ビジネス市場に関する調査(2026年)」）は未来年レンジも
  百万米ドルも持たないので誤爆しない（テスト済み）。

### 実装したファイル
- 新規: `src/delivered.py`（cross-day記憶）, `scripts/check_overlap.py`（AC-1判定）,
  `tests/test_delivered_memory.py` / `test_cluster_dedup.py` / `test_denylist.py`
- 改修: `src/config.py`（ソース再設計・KEYWORDS穴・DENYLIST・ALLOWLIST・SEO語）,
  `src/fetcher.py`（14日・per-feed max・denylist・SEOフィルタ）, `src/analyzer.py`（鮮度カーブ・信頼加点）,
  `src/ai_ranker.py`（cluster_id・プロンプト強化・cluster_key導出・dedupe_by_cluster）,
  `main.py`（新着/既報分割・クラスタ統合・新着なし配信・delivered upsert）,
  `templates/index.html.j2`（既報バッジ）, `.github/workflows/news_update.yml`（TZ・delivered.json add）

### ドライラン実測（2026-07-09, AI評価あり）
- フィード採用: PR TIMES 23件（旧0）・GNews各種。合計53件（旧37件）。全高価値ソースが復活。
- 上位はチャイルドシート調査(56%/52.3%)・新商品・小売セール・PR TIMES新商品で埋まり、
  Why/Action は固有名詞+数字入り（「アップリカ新型CSの機能・価格を自社カタログと比較表に」）。
- SEO市場レポート・スパム: レポート内 残留0件。
- cross-day: 同じ記憶で2回目実行 → 11件が既報として自動抑制。「毎日同じ」の解消を実機確認。

### 残課題・次に見るべき点
- 流通ニュース/ダイヤモンドRM は当日ベビー関連0件（低頻度ソース）。AC-6（3日連続0件で
  Telegram末尾に⚠️警告）が監視するので、警告が続けばクエリ見直し。
- 本番3日運用後に `python -X utf8 scripts/check_overlap.py` で上位重複0を確認（AC-1）。
- AI月額コスト: Haiku継続。プロンプト強化で品質不足なら `ANTHROPIC_MODEL=claude-sonnet-5` へ。
