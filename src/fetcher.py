import re

import feedparser
from datetime import datetime, timezone

from src.config import (
    RSS_FEEDS, KEYWORDS, MAX_ARTICLES_PER_FEED,
    MAX_ARTICLES_DISPLAY, FETCH_TIMEOUT_SEC, USER_AGENT,
)


def _parse_dt(entry) -> datetime:
    """feedparserのtime.struct_timeをdatetimeに変換"""
    for field in ("published_parsed", "updated_parsed"):
        t = getattr(entry, field, None)
        if t:
            try:
                return datetime(*t[:6], tzinfo=timezone.utc)
            except Exception:
                pass
    return datetime.now(timezone.utc)


def fetch_feed(feed_config: dict) -> list[dict]:
    """1フィードを取得してArticleリストを返す"""
    articles = []
    try:
        fp = feedparser.parse(
            feed_config["url"],
            request_headers={"User-Agent": USER_AGENT},
        )
        for entry in fp.entries[:MAX_ARTICLES_PER_FEED]:
            published_dt = _parse_dt(entry)
            summary = getattr(entry, "summary", "") or ""
            # HTMLタグを簡易除去
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
        # Google News RSSはURLにキーワードが含まれているのでフィルタ不要
        # それ以外はキーワードフィルタを適用
        if "news.google.com" in feed_config["url"]:
            for a in articles:
                a["matched_keywords"] = [feed_config["category"]]
            filtered = articles
        else:
            filtered = filter_by_keywords(articles)
        all_articles.extend(filtered)
        print(f"[OK] {feed_config['name']}: {len(filtered)} 件 (取得: {len(articles)} 件)")

    deduped = deduplicate(all_articles)
    deduped.sort(key=lambda a: a["published_dt"], reverse=True)
    return deduped[:MAX_ARTICLES_DISPLAY]
