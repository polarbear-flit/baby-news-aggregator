import re
from datetime import datetime, timezone

import feedparser
import requests

from src.config import (
    RSS_FEEDS, KEYWORDS, NOISE_TERMS, CRITICAL_OVERRIDE,
    MAX_ARTICLES_PER_FEED, FETCH_TIMEOUT_SEC, USER_AGENT,
)


def _parse_dt(entry) -> datetime | None:
    """feedparserのtime.struct_timeをdatetimeに変換。取れなければNone。"""
    for field in ("published_parsed", "updated_parsed"):
        t = getattr(entry, field, None)
        if t:
            try:
                return datetime(*t[:6], tzinfo=timezone.utc)
            except Exception:
                pass
    return None


def fetch_feed(feed_config: dict) -> list[dict]:
    """1フィードを取得してArticleリストを返す。timeoutを実効化。"""
    articles: list[dict] = []
    try:
        resp = requests.get(
            feed_config["url"],
            headers={"User-Agent": USER_AGENT},
            timeout=FETCH_TIMEOUT_SEC,
        )
        resp.raise_for_status()
        fp = feedparser.parse(resp.content)

        for entry in fp.entries[:MAX_ARTICLES_PER_FEED]:
            published_dt = _parse_dt(entry)
            summary = getattr(entry, "summary", "") or ""
            summary = re.sub(r"<[^>]+>", "", summary).strip()

            articles.append({
                "title": getattr(entry, "title", ""),
                "url": getattr(entry, "link", ""),
                "summary": summary[:400],
                "published": published_dt.isoformat() if published_dt else "",
                "published_dt": published_dt,
                "source_name": feed_config["name"],
                "source_type": feed_config.get("source_type", "google_news"),
                "category": feed_config["category"],
                "language": feed_config["language"],
                "matched_keywords": [],
            })
    except Exception as e:
        print(f"[SKIP] {feed_config['name']}: {e}")
    return articles


def filter_by_keywords(articles: list[dict]) -> list[dict]:
    """キーワードにマッチした記事のみ返す。matched_keywordsも付与"""
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


def is_noise(article: dict) -> bool:
    """SEO/コラム系のノイズ記事を判定。CRITICAL_OVERRIDE該当なら救う。"""
    text = (article.get("title", "") + " " + article.get("summary", "")).lower()
    if any(t.lower() in text for t in CRITICAL_OVERRIDE):
        return False
    return any(t.lower() in text for t in NOISE_TERMS)


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
    """全フィード取得 → キーワードフィルタ → ノイズ除外 → 重複除去（スコア順並べ替えはanalyzerで実施）"""
    all_articles: list[dict] = []
    for feed_config in RSS_FEEDS:
        articles = fetch_feed(feed_config)
        if "news.google.com" in feed_config["url"]:
            # Google Newsは検索クエリ自体がフィルタなのでキーワード照合は省略するが、
            # ノイズ除外とスコアリングは他ソースと同様に通す。
            for a in articles:
                a["matched_keywords"] = [feed_config["category"]]
            kw_filtered = articles
        else:
            kw_filtered = filter_by_keywords(articles)
        filtered = [a for a in kw_filtered if not is_noise(a)]
        all_articles.extend(filtered)
        print(
            f"[OK] {feed_config['name']}: {len(filtered)} 件採用 "
            f"(取得: {len(articles)} / キーワード後: {len(kw_filtered)})"
        )

    return deduplicate(all_articles)
