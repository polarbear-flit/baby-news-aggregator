# Baby News Aggregator 仕様書（ChatGPT相談用）

このファイルはChatGPTに改善案を相談するための仕様書です。
リポジトリ全体のコードと現状の課題を1ファイルにまとめています。

---

## 1. アプリの目的

ベビー用品カテゴリ（哺乳瓶・ベビーカー・カーシート・おむつ・おしりふき・スキンケア）のニュースを毎朝自動収集し、Telegramに要約を送るツール。
EC事業の商品担当として、日々の市場トレンド・新製品・リコール情報を5分でキャッチアップするのが目的。

---

## 2. 解決したい課題（=ChatGPTに相談したいこと）

### 課題A：いいニュースが拾えない
- 50件取ってきても「商品担当として読む価値がある記事」が少ない
- ノイズ（古い話題の使い回し、関連性が薄い記事、まとめサイトの転載など）が多い
- 「ハイライト3件」がHotとして選ばれるが、内容がパッとしない日が多い

### 課題B：Telegramから元記事に飛べない
- 現状のTelegram通知はタイトル文字列のみ。URLが含まれていない
- 気になるニュースを見つけてもブラウザを開いて自分で検索する必要がある
- HTMLレポート（GitHub Pages）には飛べるが、Telegramから直接元記事リンクを踏めるようにしたい

ChatGPTに期待する出力：
1. 課題A・Bそれぞれに対する具体的な改善策
2. 優先順位（コスパの高い順）
3. 実装イメージ（コード or 設計の方針）

---

## 3. 全体アーキテクチャ

```
毎日 22:00 UTC（=07:00 JST）
   ↓
GitHub Actions（無料枠）が起動
   ↓
main.py 実行
   ├─ src/fetcher.py    : RSS取得 → キーワードフィルタ → 重複除去 → 上位50件
   ├─ src/analyzer.py   : スコアリング・トレンド検出・カテゴリ分類
   ├─ src/renderer.py   : Jinja2でHTMLレポート生成
   └─ Telegram API      : 要約メッセージ送信
   ↓
docs/index.html と data/history.json を git push
   ↓
GitHub Pages に公開
```

- 言語：Python 3.11
- 依存：`feedparser`, `jinja2`, `requests`
- ホスティング：GitHub Actions（実行）+ GitHub Pages（HTMLレポート公開）
- 通知：Telegram Bot API
- 費用：0円

---

## 4. ファイル構成

```
baby-news-aggregator/
├── .github/workflows/news_update.yml   # cron実行設定
├── src/
│   ├── config.py             # RSSフィード一覧・キーワード辞書
│   ├── fetcher.py            # RSS取得・フィルタ・重複除去
│   ├── analyzer.py           # スコアリング・トレンド・インサイト生成
│   └── renderer.py           # HTML生成
├── templates/index.html.j2   # HTMLテンプレート（Tailwind + Chart.js）
├── docs/index.html           # 自動生成・GitHub Pagesで公開
├── data/history.json         # 過去30日のキーワード頻度履歴
├── main.py                   # エントリーポイント + Telegram送信
└── requirements.txt
```

---

## 5. 全コード（主要ファイル）

### 5-1. main.py（エントリーポイント + Telegram送信）

```python
from src.fetcher import fetch_all_feeds
from src.analyzer import analyze
from src.renderer import render
import json
import os
import requests
from datetime import datetime, timezone, timedelta

from src.config import HISTORY_PATH, OUTPUT_PATH, TREND_WINDOW_DAYS


def load_history() -> list[dict]:
    if not os.path.exists(HISTORY_PATH):
        return []
    try:
        with open(HISTORY_PATH, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []


def save_history(history, keyword_freq, article_count):
    jst = timezone(timedelta(hours=9))
    today = datetime.now(jst).isoformat()
    new_record = {
        "date": today,
        "article_count": article_count,
        "keyword_freq": keyword_freq,
    }
    cutoff = datetime.now(timezone.utc) - timedelta(days=TREND_WINDOW_DAYS)
    kept = []
    for r in history:
        try:
            ts = datetime.fromisoformat(r["date"])
            if ts.tzinfo is None:
                ts = ts.replace(tzinfo=timezone.utc)
            if ts >= cutoff:
                kept.append(r)
        except Exception:
            pass
    updated = [new_record] + kept
    os.makedirs(os.path.dirname(HISTORY_PATH), exist_ok=True)
    with open(HISTORY_PATH, "w", encoding="utf-8") as f:
        json.dump(updated, f, ensure_ascii=False, indent=2)


def send_telegram(analysis, articles):
    """Telegramにサマリを送信。★ここで元記事URLを送っていない★"""
    token = os.environ.get("BABY_NEWS_BOT_TOKEN")
    chat_id = os.environ.get("BABY_NEWS_CHAT_ID")
    if not token or not chat_id:
        return

    jst = timezone(timedelta(hours=9))
    today = datetime.now(jst).strftime("%Y/%m/%d")

    cat_labels = {
        "feeding": "🍼 授乳", "mobility": "👶 ベビーカー",
        "car_safety": "🚗 チャイルドシート", "diaper": "🧸 おむつ",
        "wipes": "💧 おしりふき", "skincare": "🌿 スキンケア",
        "general": "📰 一般",
    }
    cat_lines = " / ".join(
        f"{cat_labels.get(k, k)}: {v}件"
        for k, v in sorted(analysis["category_freq"].items(), key=lambda x: -x[1])
        if v > 0
    )

    hot = analysis.get("hot_articles", articles[:3])
    # ★ここがタイトル文字列のみ。URLを付けていない★
    highlights = "\n".join(f"・{a['title'][:50]}" for a in hot[:3])

    trending = analysis.get("trending_keywords", [])
    trend_text = "、".join(t["keyword"] for t in trending[:3]) if trending else "なし"

    recall_count = sum(
        1 for a in articles
        if any(k in ["recall", "リコール"] for k in a.get("matched_keywords", []))
    )
    recall_line = f"⚠️ リコール関連: {recall_count}件\n" if recall_count > 0 else ""

    message = f"""📰 ベビー用品ニュース {today}
━━━━━━━━━━━━━
【今日のハイライト】
{highlights}

📊 カテゴリ別
{cat_lines}

📈 急上昇: {trend_text}
{recall_line}合計 {len(articles)} 件収集
━━━━━━━━━━━━━"""

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    requests.post(url, json={"chat_id": chat_id, "text": message}, timeout=10)


def main():
    articles = fetch_all_feeds()
    history = load_history()
    analysis = analyze(articles, history)
    html = render(articles, analysis)
    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        f.write(html)
    send_telegram(analysis, articles)
    save_history(history, analysis["keyword_freq"], len(articles))


if __name__ == "__main__":
    main()
```

### 5-2. src/config.py（RSSフィード・キーワード）

```python
RSS_FEEDS = [
    # Google News 日本語（キーワード検索RSS）
    {"name": "GNews: ベビー用品全般", "url": "https://news.google.com/rss/search?q=ベビー用品&hl=ja&gl=JP&ceid=JP:ja", "category": "general", "language": "ja"},
    {"name": "GNews: 哺乳瓶・授乳", "url": "https://news.google.com/rss/search?q=哺乳瓶+授乳+ミルク&hl=ja&gl=JP&ceid=JP:ja", "category": "feeding", "language": "ja"},
    {"name": "GNews: ベビーカー・チャイルドシート", "url": "https://news.google.com/rss/search?q=ベビーカー+チャイルドシート&hl=ja&gl=JP&ceid=JP:ja", "category": "mobility", "language": "ja"},
    {"name": "GNews: おむつ・おしりふき", "url": "https://news.google.com/rss/search?q=おむつ+おしりふき&hl=ja&gl=JP&ceid=JP:ja", "category": "diaper", "language": "ja"},
    {"name": "GNews: ベビースキンケア", "url": "https://news.google.com/rss/search?q=赤ちゃん+スキンケア+保湿&hl=ja&gl=JP&ceid=JP:ja", "category": "skincare", "language": "ja"},
    {"name": "GNews: ベビー用品リコール", "url": "https://news.google.com/rss/search?q=ベビー+リコール+安全+乳幼児&hl=ja&gl=JP&ceid=JP:ja", "category": "general", "language": "ja"},
    {"name": "GNews: 育児市場トレンド", "url": "https://news.google.com/rss/search?q=育児+市場+新製品+子育て&hl=ja&gl=JP&ceid=JP:ja", "category": "general", "language": "ja"},
    # Google News 英語
    {"name": "GNews: baby products market", "url": "https://news.google.com/rss/search?q=baby+products+market+trend&hl=en&gl=US&ceid=US:en", "category": "general", "language": "en"},
    {"name": "GNews: stroller car seat", "url": "https://news.google.com/rss/search?q=stroller+car+seat+infant&hl=en&gl=US&ceid=US:en", "category": "car_safety", "language": "en"},
    {"name": "GNews: diaper wipes recall", "url": "https://news.google.com/rss/search?q=diaper+baby+wipes+recall+safety&hl=en&gl=US&ceid=US:en", "category": "diaper", "language": "en"},
    {"name": "GNews: baby skincare formula", "url": "https://news.google.com/rss/search?q=baby+skincare+formula+infant+lotion&hl=en&gl=US&ceid=US:en", "category": "skincare", "language": "en"},
    # その他
    {"name": "PR TIMES: ベビー", "url": "https://prtimes.jp/rss20.xml", "category": "general", "language": "ja"},
    {"name": "Baby Gaga", "url": "https://www.babygaga.com/feed/", "category": "general", "language": "en"},
]

KEYWORDS = {
    "feeding":    ["哺乳瓶", "bottle", "feeding", "formula", "breastfeeding", "nipple", "授乳", "母乳", "ミルク", "離乳食"],
    "mobility":   ["ベビーカー", "stroller", "pram", "pushchair", "buggy", "抱っこひも", "スリング"],
    "car_safety": ["カーシート", "car seat", "child restraint", "booster seat", "チャイルドシート"],
    "diaper":     ["おむつ", "diaper", "nappy", "pampers", "huggies", "オムツ", "紙おむつ"],
    "wipes":      ["おしりふき", "baby wipes", "wet wipes", "cleansing wipe", "ウェットシート"],
    "skincare":   ["スキンケア", "baby lotion", "baby cream", "eczema", "baby wash", "sensitive skin", "baby oil",
                   "赤ちゃん肌", "乳児湿疹", "保湿", "無添加", "オーガニック", "低刺激"],
    "general":    ["recall", "リコール", "safety", "安全", "market share", "growth", "trend", "regulation",
                   "新製品", "new product", "baby", "infant", "赤ちゃん", "乳幼児",
                   "育児", "子育て", "ベビー", "新生児", "幼児", "子ども用品", "ベビー用品", "マタニティ"],
}

TREND_WINDOW_DAYS = 30
MAX_ARTICLES_PER_FEED = 20
MAX_ARTICLES_DISPLAY = 50
OUTPUT_PATH = "docs/index.html"
HISTORY_PATH = "data/history.json"
FETCH_TIMEOUT_SEC = 15
USER_AGENT = "Mozilla/5.0 (compatible; BabyNewsAggregator/1.0)"
```

### 5-3. src/fetcher.py（取得・フィルタ・重複除去）

```python
import re
import feedparser
from datetime import datetime, timezone

from src.config import (
    RSS_FEEDS, KEYWORDS, MAX_ARTICLES_PER_FEED,
    MAX_ARTICLES_DISPLAY, FETCH_TIMEOUT_SEC, USER_AGENT,
)


def _parse_dt(entry) -> datetime:
    for field in ("published_parsed", "updated_parsed"):
        t = getattr(entry, field, None)
        if t:
            try:
                return datetime(*t[:6], tzinfo=timezone.utc)
            except Exception:
                pass
    return datetime.now(timezone.utc)


def fetch_feed(feed_config: dict) -> list[dict]:
    articles = []
    try:
        fp = feedparser.parse(
            feed_config["url"],
            request_headers={"User-Agent": USER_AGENT},
        )
        for entry in fp.entries[:MAX_ARTICLES_PER_FEED]:
            published_dt = _parse_dt(entry)
            summary = getattr(entry, "summary", "") or ""
            summary = re.sub(r"<[^>]+>", "", summary).strip()
            articles.append({
                "title": getattr(entry, "title", ""),
                "url": getattr(entry, "link", ""),
                "summary": summary[:400],
                "published": published_dt.isoformat(),
                "published_dt": published_dt,
                "source_name": feed_config["name"],
                "category": feed_config["category"],
                "language": feed_config["language"],
                "matched_keywords": [],
            })
    except Exception as e:
        print(f"[SKIP] {feed_config['name']}: {e}")
    return articles


def filter_by_keywords(articles: list[dict]) -> list[dict]:
    """キーワードにマッチした記事のみ返す（Google News以外に適用）"""
    result = []
    for article in articles:
        text = (article["title"] + " " + article["summary"]).lower()
        matched = []
        for category, kw_list in KEYWORDS.items():
            for kw in kw_list:
                if kw.lower() in text:
                    matched.append(kw)
        if matched:
            article["matched_keywords"] = list(set(matched))
            result.append(article)
    return result


def deduplicate(articles: list[dict]) -> list[dict]:
    """URLとタイトル前方一致で重複除去"""
    seen_urls: set[str] = set()
    seen_titles: set[str] = set()
    result = []
    for a in articles:
        norm_url = a["url"].rstrip("/").lower()
        norm_title = a["title"][:40].lower()
        if norm_url in seen_urls or norm_title in seen_titles:
            continue
        seen_urls.add(norm_url)
        seen_titles.add(norm_title)
        result.append(a)
    return result


def fetch_all_feeds() -> list[dict]:
    """全フィード取得 → フィルタ → 重複除去 → 日時降順 → 最大50件"""
    all_articles: list[dict] = []
    for feed_config in RSS_FEEDS:
        articles = fetch_feed(feed_config)
        # ★Google News RSSは検索キーワード自体がフィルタになっているのでフィルタ無効化★
        if "news.google.com" in feed_config["url"]:
            for a in articles:
                a["matched_keywords"] = [feed_config["category"]]
            filtered = articles
        else:
            filtered = filter_by_keywords(articles)
        all_articles.extend(filtered)

    deduped = deduplicate(all_articles)
    deduped.sort(key=lambda a: a["published_dt"], reverse=True)
    return deduped[:MAX_ARTICLES_DISPLAY]
```

### 5-4. src/analyzer.py（スコアリング・トレンド検出）

```python
from collections import Counter
from datetime import datetime, timezone, timedelta

from src.config import KEYWORDS, TREND_WINDOW_DAYS


def score_articles(articles: list[dict]) -> list[dict]:
    """★スコアリングロジック★ 上位がTelegramの「ハイライト」になる"""
    now = datetime.now(timezone.utc)
    scored = []
    for a in articles:
        score = len(a["matched_keywords"])  # マッチしたキーワード数
        text = (a["title"] + " " + a["summary"]).lower()
        if "recall" in text or "リコール" in text:
            score += 5
        if "safety" in text or "安全" in text:
            score += 2
        try:
            age_hours = (now - a["published_dt"]).total_seconds() / 3600
            if age_hours < 24:
                score += 3
            elif age_hours < 72:
                score += 1
        except Exception:
            pass
        scored.append({**a, "score": score})
    scored.sort(key=lambda x: x["score"], reverse=True)
    return scored


# ※ count_keyword_freq, count_category_freq, calc_trending_keywords,
#   generate_category_insight, generate_overall_insights は省略（HTMLレポート用）
```

### 5-5. .github/workflows/news_update.yml

```yaml
name: Baby News Update
on:
  schedule:
    - cron: '0 22 * * *'  # 毎日07:00 JST
  workflow_dispatch:
permissions:
  contents: write
jobs:
  update-news:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
          cache: 'pip'
      - run: pip install -r requirements.txt
      - run: python main.py
        env:
          TZ: Asia/Tokyo
          BABY_NEWS_BOT_TOKEN: ${{ secrets.BABY_NEWS_BOT_TOKEN }}
          BABY_NEWS_CHAT_ID: ${{ secrets.BABY_NEWS_CHAT_ID }}
      - name: Commit and push
        run: |
          git config user.name "github-actions[bot]"
          git config user.email "github-actions[bot]@users.noreply.github.com"
          git add docs/index.html data/history.json
          git diff --staged --quiet || (git commit -m "chore: auto-update news report $(date +'%Y-%m-%d %H:%M JST')" && git push)
```

---

## 6. 現状のTelegramメッセージ実例

```
📰 ベビー用品ニュース 2026/05/04
━━━━━━━━━━━━━
【今日のハイライト】
・ベビーカーで電車に乗るとき気をつけたい3つのこと
・チャイルドシートの選び方完全ガイド2026年版
・新生児に最適な紙おむつランキング

📊 カテゴリ別
🧸 おむつ: 12件 / 👶 ベビーカー: 9件 / 🌿 スキンケア: 7件 / ...

📈 急上昇: 育児、新製品、ベビー
合計 50 件収集
━━━━━━━━━━━━━
```

→ **タイトルだけで、リンクが無い**。HTMLレポート（GitHub Pages）のURLすら載っていない。

---

## 7. データモデル

### Article（記事1件）
```python
{
    "title": str,
    "url": str,                  # 元記事URL（ただしGoogle Newsの場合はリダイレクトURL）
    "summary": str,              # 最大400文字
    "published": str,            # ISO8601
    "published_dt": datetime,
    "source_name": str,          # フィード名
    "category": str,             # フィード設定の初期カテゴリ
    "language": "ja" | "en",
    "matched_keywords": list[str],
    "score": int,                # analyzer後に付与
}
```

### history.json（過去30日分）
```json
[
  {
    "date": "2026-05-04T07:00:00+09:00",
    "article_count": 50,
    "keyword_freq": {"育児": 12, "ベビー": 9, ...}
  },
  ...
]
```

---

## 8. 課題A「いいニュースが拾えない」の原因仮説（私が思う範囲）

1. **Google News RSSがキーワードフィルタを素通りしている**
   `fetcher.py` の `if "news.google.com" in feed_config["url"]:` で全件採用してしまうため、ノイズが入る
2. **スコアリングが浅い**
   キーワード数 + リコール/安全 + 新鮮さだけ。「商品担当として価値があるか」を測れていない
3. **ソースが弱い**
   Google News RSS頼みで、業界特化メディア（こども家庭庁・PIO-NET・GfK・Statistaなど）が無い
4. **PR TIMESがベビーフィルタ無しで全カテゴリ取れてしまう**
   `prtimes.jp/rss20.xml` は全分野のプレスリリースが流れてくる
5. **AI要約・選別が無い**
   Claude/GPTを呼んで「これは商品担当に有益か」を判定するステップが無い

---

## 9. 課題B「Telegramから元記事に飛べない」の原因

`main.py` の `send_telegram()` 内の以下の行：

```python
highlights = "\n".join(f"・{a['title'][:50]}" for a in hot[:3])
```

→ `a['url']` を含めていない。
Telegramは `parse_mode="HTML"` または `"MarkdownV2"` を指定すればリンク化できる。
また、HTMLレポート（GitHub Pages）のURL自体もメッセージ末尾に貼っていない。

---

## 10. ChatGPTへの質問（コピペ用）

> 上記アプリについて、以下を相談したい。
>
> **質問1（課題A）**：商品担当として読む価値のあるニュースを優先して上位に出すには、どこをどう改善すればよいか？
> - 新しいRSSソースの提案（業界特化メディア・公的機関）
> - スコアリングロジックの改善案
> - AI（Claude API or OpenAI API）を使った選別の組み込み方
> - 「価値あるニュース」を定義するための評価軸の提案
>
> **質問2（課題B）**：Telegramメッセージから元記事や日次レポートに直接飛べるようにしたい。
> - `send_telegram()` のコード修正案（parse_mode, HTML/MarkdownV2のどちら推奨か）
> - Google News RSSのリダイレクトURLが長くて醜い問題の対処法
> - HTMLレポート（GitHub Pages）URLをメッセージに添える形式の提案
>
> **質問3**：上記2つを実装する優先順位と、最小工数で効果が大きい順に並べ替えてほしい。
