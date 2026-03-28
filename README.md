# ベビー用品ニュース収集・Telegram通知ツール

ベビー用品カテゴリ（哺乳瓶・ベビーカー・カーシート・おむつ・おしりふき・スキンケア）に関するニュースを毎日自動収集し、Telegramに要約を送信するツールです。

## 何ができるか

- Google News RSS から日本語・英語のニュースを毎日最大50件収集
- カテゴリ別に分類・トレンド検出・ビジネス示唆を自動生成
- 毎朝07:00 JST に Telegram へ要約を自動送信
- 収集結果をHTMLレポートとして `docs/index.html` に保存

## 仕組み

```
毎日 07:00 JST
↓
GitHub Actions がサーバーを起動（無料・自分のPCは不要）
↓
Google News RSS からニュース収集（日本語7本・英語4本）
↓
キーワード分類 / トレンド検出 / スコアリング
↓
docs/index.html を生成・リポジトリに保存
↓
Telegram Bot に要約を送信
↓
サーバー終了
```

## ファイル構成

```
baby-news-aggregator/
├── .github/
│   └── workflows/
│       └── news_update.yml   # 定期実行の設定（cron）
├── src/
│   ├── config.py             # RSSフィード・キーワードの設定
│   ├── fetcher.py            # RSSニュース取得
│   ├── analyzer.py           # 分析・インサイト生成
│   └── renderer.py           # HTMLレポート生成
├── templates/
│   └── index.html.j2         # HTMLテンプレート
├── docs/
│   └── index.html            # 生成されたレポート（自動更新）
├── data/
│   └── history.json          # 過去30日のキーワード頻度履歴
├── main.py                   # エントリーポイント
└── requirements.txt          # 依存パッケージ
```

## セットアップ済みの内容

### GitHub Secrets（登録済み）
| Secret名 | 内容 |
|---------|------|
| `BABY_NEWS_BOT_TOKEN` | Telegram Bot のToken |
| `BABY_NEWS_CHAT_ID` | 送信先のChat ID |

### 対応しているニュースソース
| フィード | 言語 | カテゴリ |
|---------|------|---------|
| GNews: ベビー用品全般 | 日本語 | 全般 |
| GNews: 哺乳瓶・授乳 | 日本語 | feeding |
| GNews: ベビーカー・チャイルドシート | 日本語 | mobility |
| GNews: おむつ・おしりふき | 日本語 | diaper |
| GNews: ベビースキンケア | 日本語 | skincare |
| GNews: ベビー用品リコール | 日本語 | general |
| GNews: 育児市場トレンド | 日本語 | general |
| GNews: baby products market | 英語 | general |
| GNews: stroller car seat | 英語 | car_safety |
| GNews: diaper wipes recall | 英語 | diaper |
| GNews: baby skincare formula | 英語 | skincare |
| Baby Gaga | 英語 | general |

## よくある操作

### 手動で今すぐ実行したい
1. [Actions](https://github.com/polarbear-flit/baby-news-aggregator/actions) を開く
2. 「Baby News Update」→「Run workflow」→「Run workflow」

### 実行時間を変えたい
`.github/workflows/news_update.yml` の `cron` を変更する。

| 送りたい時間（JST） | cronの設定 |
|------------------|-----------|
| 07:00 | `0 22 * * *`（現在） |
| 08:00 | `0 23 * * *` |
| 09:00 | `0 0 * * *` |
| 12:00 | `0 3 * * *` |

変更後は `git add . → git commit → git push` で反映される。

### ニュースのキーワードを追加・変更したい
`src/config.py` の `KEYWORDS` を編集する。

```python
KEYWORDS = {
    "feeding":    ["哺乳瓶", "bottle", ...],   # 授乳関連
    "mobility":   ["ベビーカー", "stroller", ...], # 移動関連
    "car_safety": ["カーシート", "car seat", ...],
    "diaper":     ["おむつ", "diaper", ...],
    "wipes":      ["おしりふき", "baby wipes", ...],
    "skincare":   ["スキンケア", "baby lotion", ...],
    "general":    ["育児", "ベビー", ...],      # 全般
}
```

### RSSフィードを追加したい
`src/config.py` の `RSS_FEEDS` にエントリを追加する。

```python
{"name": "フィード名", "url": "RSSのURL", "category": "general", "language": "ja"},
```

### ローカルで動かしたい（テスト用）
```powershell
cd C:\Users\littl\ClaudeLabs\baby-news-aggregator
pip install -r requirements.txt

# Telegram通知も送る場合（GitHub SecretsのTokenとChatIDを入力）
$env:BABY_NEWS_BOT_TOKEN = "（BotFatherのTokenを入力）"
$env:BABY_NEWS_CHAT_ID = "（userinofobot で取得したIDを入力）"

python main.py
```

## Telegramメッセージのサンプル

```
📰 ベビー用品ニュース 2026/03/29
━━━━━━━━━━━━━━━━━━━━━
【今日のハイライト】
・おむつサブスクが保育園で相次ぎ導入
・ジョンソンベビーがブランド刷新
・チャイルドシート遮熱カバー新発売

📊 カテゴリ別
👶 ベビーカー: 13件 / 🌿 スキンケア: 9件 / ...

📈 急上昇: mobility、skincare、car_safety
合計 50 件収集
━━━━━━━━━━━━━━━━━━━━━
```

## 今後の発展案

### すぐできる
- 送信時間の変更
- キーワード・フィードの追加
- Telegramメッセージのフォーマット変更

### 中期
- **GitHub Actions → Claudeのスケジュール連携**
  - Actionsが収集したJSONをpush → ClaudeがAIで読んでビジネス示唆を生成 → Telegram送信
  - 条件: リポジトリをPublicにする必要あり
- 週次サマリー（月曜朝に1週間分のトレンドまとめ）

## 費用

| 項目 | 費用 |
|------|------|
| GitHub Actions | 無料（月2,000分まで・月60〜90分しか使わない） |
| Google News RSS | 無料 |
| Telegram Bot | 無料 |
| 合計 | **0円** |