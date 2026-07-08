"""フィード取得・正規化・ノイズ除外・重複除去 — 業界動向特化版。

設計方針:
- 目的を「ベビー用品EC事業の業界動向把握」に統一。リコール・規制系のソース/フィルタ救済は完全撤廃。
- HARD_NOISE は CRITICAL_OVERRIDE による救済なしで完全除外。
- 重複除去は normalize_title + rapidfuzz の類似度ベース。
- 配信前のリンク検証は verify_link()（Telegram上位のみ）。
"""

import hashlib
import re
from datetime import datetime, timedelta, timezone
from typing import Optional

import feedparser
import requests

try:
    from rapidfuzz import fuzz  # type: ignore

    HAS_RAPIDFUZZ = True
except ImportError:  # pragma: no cover
    HAS_RAPIDFUZZ = False

from src.config import (
    RSS_FEEDS,
    KEYWORDS,
    HARD_NOISE_TERMS,
    CRITICAL_OVERRIDE,
    PAST_YEAR_TITLE_PATTERNS,
    DOMAIN_DENYLIST,
    MAX_ARTICLES_PER_FEED,
    FETCH_TIMEOUT_SEC,
    USER_AGENT,
)

# 古すぎる記事は完全除外（日次Botに数年前のニュースは不要）。
# 2026-07-08: 90→14日。日次ブリーフに3ヶ月前のニュースは不要。Google News の
# `when:7d` と併用してほぼ二重防御にする。
MAX_ARTICLE_AGE_DAYS = 14
# 重複判定の類似度しきい値（0-100）。88以上を重複扱いにする。
DEDUP_SIMILARITY_THRESHOLD = 88


def normalize_title(title: str) -> str:
    """重複検出用のタイトル正規化。

    画像N/M, 写真N/M、末尾の媒体名、括弧内、句読点、空白を除去。
    """
    if not title:
        return ""
    s = title
    s = re.sub(r"画像\s*\d+\s*[/／]\s*\d+", "", s)
    s = re.sub(r"写真\s*\d+\s*[/／]\s*\d+", "", s)
    s = re.sub(r"\s*[|｜\-－‐]\s*[^|｜\-－‐]+$", "", s)
    s = re.sub(r"[【\[\(（][^】\]\)）]*[】\]\)）]", "", s)
    s = re.sub(r"[、。!！?？\"'‘’“”「」『』]", "", s)
    s = re.sub(r"\s+", "", s)
    return s.lower()


def _parse_dt(entry) -> Optional[datetime]:
    for field in ("published_parsed", "updated_parsed"):
        t = getattr(entry, field, None)
        if t:
            try:
                return datetime(*t[:6], tzinfo=timezone.utc)
            except Exception:
                pass
    return None


def _extract_site_domain(query_url: str) -> Optional[str]:
    """Google News RSS の URL から site:domain を抽出。なければ None。"""
    m = re.search(r"site:([\w.\-]+)", query_url)
    return m.group(1).lower() if m else None


def _article_url_matches_site(article_url: str, site_domain: str) -> bool:
    """記事URLが site:domain と一致するかチェック。

    Google News は redirect URL (news.google.com/articles/...) を返すため、
    URLからの判定は不完全。article内に <source> 要素や原URLが含まれていれば理想。
    実用的には:
    - Google News redirect URL の場合: True 扱い（後段の Codex リスク受容、軽量化）
    - 直接URLの場合: ホスト名を含むか確認
    """
    if not article_url:
        return True  # 判定不能の場合は許容
    url_lower = article_url.lower()
    if "news.google.com" in url_lower:
        # redirect URL — 内容を保証できないが site: クエリを信頼する
        # （括弧で OR を囲んでいる前提）
        return True
    return site_domain in url_lower


def _fetch_rss(feed_config: dict) -> list[dict]:
    """RSS/Atom フィードを取得して Article リストを返す。

    site: スコープのフィードで非該当ドメインの記事が混入した場合、
    source_type を google_news に格下げする（Codex指摘の二重防御）。
    """
    articles: list[dict] = []
    expected_site = _extract_site_domain(feed_config.get("url", ""))
    base_source_type = feed_config.get("source_type", "google_news")
    max_articles = feed_config.get("max_articles", MAX_ARTICLES_PER_FEED)

    try:
        resp = requests.get(
            feed_config["url"],
            headers={"User-Agent": USER_AGENT},
            timeout=FETCH_TIMEOUT_SEC,
        )
        resp.raise_for_status()
        fp = feedparser.parse(resp.content)

        for entry in fp.entries[:max_articles]:
            published_dt = _parse_dt(entry)
            summary = getattr(entry, "summary", "") or ""
            summary = re.sub(r"<[^>]+>", "", summary).strip()
            article_url = getattr(entry, "link", "")

            # site: スコープのフィードで非該当ドメイン記事は source_type を格下げ
            source_type = base_source_type
            if expected_site and base_source_type != "google_news":
                if not _article_url_matches_site(article_url, expected_site):
                    source_type = "google_news"

            articles.append(
                {
                    "title": getattr(entry, "title", ""),
                    "url": article_url,
                    "summary": summary[:400],
                    "published": published_dt.isoformat() if published_dt else "",
                    "published_dt": published_dt,
                    "source_name": feed_config["name"],
                    "source_type": source_type,
                    "category": feed_config["category"],
                    "language": feed_config["language"],
                    "matched_keywords": [],
                }
            )
    except Exception as e:
        print(f"[SKIP] {feed_config['name']}: {e}")
    return articles


# fetch_type ディスパッチ。CAA リコール HTML スクレイピングは撤廃。
FETCH_DISPATCH = {
    "rss": _fetch_rss,
}


def fetch_feed(feed_config: dict) -> list[dict]:
    """fetch_type に応じて取得関数をディスパッチ。"""
    fetch_type = feed_config.get("fetch_type", "rss")
    fetcher = FETCH_DISPATCH.get(fetch_type, _fetch_rss)
    return fetcher(feed_config)


def filter_by_keywords(articles: list[dict]) -> list[dict]:
    """キーワードにマッチした記事のみ返す。matched_keywordsも付与。"""
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


def is_hard_noise(article: dict) -> bool:
    """HARD_NOISE_TERMS該当の記事を完全除外判定。

    CRITICAL_OVERRIDE は空（業界動向特化のため救済例外を作らない）。
    リコール語が入る記事もここで弾く設計。
    """
    text = (article.get("title", "") + " " + article.get("summary", "")).lower()
    if CRITICAL_OVERRIDE and any(t.lower() in text for t in CRITICAL_OVERRIDE):
        return False
    return any(t.lower() in text for t in HARD_NOISE_TERMS)


def is_denylisted(article: dict) -> bool:
    """DOMAIN_DENYLIST に該当する記事を除外判定。

    Google News のリダイレクトURLはドメインが news.google.com になるため、
    「記事URL」に加えて「タイトル末尾の媒体名（ ` - 媒体名` ）」にも当てる。
    """
    url = (article.get("url", "") or "").lower()
    title = (article.get("title", "") or "").lower()
    source = (article.get("source_name", "") or "").lower()
    # タイトル末尾の「 - 媒体名」を抽出（Google News の慣習）
    trailing_media = ""
    m = re.search(r"[-–—|｜]\s*([^-–—|｜]+)$", article.get("title", ""))
    if m:
        trailing_media = m.group(1).strip().lower()

    blob = " ".join([url, title, source, trailing_media])
    # スペースを除いた版も用意（媒体名「Fortune Business Insights」とドメイン
    # 「fortunebusinessinsights.com」のような表記ゆれを吸収）
    despaced = blob.replace(" ", "")
    for term in DOMAIN_DENYLIST:
        t = term.lower()
        core = t.split(".")[0]  # ドメインのTLD前 or プレーン語
        if t in blob or (core and core in despaced):
            return True
    return False


# 2031年以降の未来年（機械翻訳SEO市場予測レポートの「〜2032年予測」等の signature）
_FORECAST_YEAR = re.compile(r"20(?:3[1-9]|[4-9]\d)")
# SEO市場予測レポート特有の語（百万米ドル・CAGR・調査会社名等）
_SEO_MARKET_TERMS = [
    "百万米ドル",
    "million usd",
    "usd million",
    "qyresearch",
    "cagr",
    "世界市場予測",
    "予測レポート",
    "market research future",
    "grand view",
    "report ocean",
    "imarc",
    "market size",
    "市場規模、シェア",
]


def is_seo_market_report(article: dict) -> bool:
    """機械翻訳SEO市場予測レポートを除外判定。

    「○○市場：2026年〜2032年 世界市場予測、CAGR、XX百万米ドル」型の記事。
    日本のECカテゴリ担当には非実用（グローバル予測の羅列で actionability ゼロ）。
    正規の国内調査（矢野経済「ベビー関連ビジネス市場に関する調査(2026年)」等）は
    未来年レンジや百万米ドル表記を持たないため誤爆しない。
    """
    text = (article.get("title", "") + " " + article.get("summary", "")).lower()
    has_market = "市場" in text or "market" in text
    if has_market and _FORECAST_YEAR.search(text):
        return True
    if any(t in text for t in _SEO_MARKET_TERMS):
        return True
    return False


def is_too_old(article: dict) -> bool:
    """MAX_ARTICLE_AGE_DAYS より古い記事を除外。日付不明は許容（analyzerで減点）。"""
    published_dt = article.get("published_dt")
    if published_dt is None:
        return False
    cutoff = datetime.now(timezone.utc) - timedelta(days=MAX_ARTICLE_AGE_DAYS)
    return published_dt < cutoff


def is_old_topic_title(article: dict) -> bool:
    """タイトル/要約冒頭に過去年シグナルが含まれていれば古い記事と判定。"""
    title = article.get("title", "")
    summary = article.get("summary", "")[:150]
    text_check = title + " " + summary
    text_lower = text_check.lower()
    if CRITICAL_OVERRIDE and any(t.lower() in text_lower for t in CRITICAL_OVERRIDE):
        return False
    return any(p in text_check for p in PAST_YEAR_TITLE_PATTERNS)


def _make_group_id(normalized_title: str) -> str:
    """正規化タイトルから決定的な duplicate_group_id (10桁MD5) を生成。"""
    if not normalized_title:
        return ""
    return hashlib.md5(normalized_title.encode("utf-8")).hexdigest()[:10]


def deduplicate(articles: list[dict]) -> list[dict]:
    """URL一致 + タイトル正規化+類似度で重複除去。各記事に duplicate_group_id を付与。"""
    seen_urls: set[str] = set()
    kept: list[tuple[str, dict]] = []

    for a in articles:
        norm_url = (a.get("url") or "").rstrip("/").lower()
        if norm_url and norm_url in seen_urls:
            continue
        if norm_url:
            seen_urls.add(norm_url)

        norm_title = normalize_title(a.get("title", ""))
        if not norm_title:
            a["duplicate_group_id"] = ""
            kept.append((norm_title, a))
            continue

        is_dup = False
        if HAS_RAPIDFUZZ:
            for prev_norm, _ in kept:
                if not prev_norm:
                    continue
                if fuzz.ratio(norm_title, prev_norm) >= DEDUP_SIMILARITY_THRESHOLD:
                    is_dup = True
                    break
        else:
            if any(prev_norm == norm_title for prev_norm, _ in kept):
                is_dup = True

        if not is_dup:
            a["duplicate_group_id"] = _make_group_id(norm_title)
            kept.append((norm_title, a))

    return [a for _, a in kept]


def verify_link(url: str, timeout: int = 5) -> str:
    """URLが最低限アクセス可能か検証。

    Returns: "ok" / "failed" / "skipped"
    HEAD失敗時は GET (stream=True) でフォールバック。
    """
    if not url:
        return "skipped"
    headers = {"User-Agent": USER_AGENT}
    try:
        resp = requests.head(
            url, allow_redirects=True, timeout=timeout, headers=headers
        )
        if resp.status_code < 400:
            return "ok"
    except Exception:
        pass
    try:
        with requests.get(
            url, allow_redirects=True, timeout=timeout, headers=headers, stream=True
        ) as resp:
            if resp.status_code < 400:
                return "ok"
            return "failed"
    except Exception:
        return "failed"


def verify_links_batch(articles: list[dict], max_count: int = 7) -> list[dict]:
    """先頭 max_count 件のURLを検証し、各記事に link_status を付与。"""
    for i, a in enumerate(articles):
        if i >= max_count:
            a.setdefault("link_status", "skipped")
            continue
        a["link_status"] = verify_link(a.get("url", ""))
    return articles


def fetch_all_feeds() -> list[dict]:
    """全フィード取得 → キーワードフィルタ → ノイズ・古さ除外 → 重複除去。"""
    all_articles: list[dict] = []
    for feed_config in RSS_FEEDS:
        articles = fetch_feed(feed_config)

        url = feed_config.get("url", "")
        fetch_type = feed_config.get("fetch_type", "rss")
        if fetch_type != "rss":
            # 公的ソース等は既に matched_keywords 付きの想定でスキップ
            kw_filtered = articles
        else:
            # ⚠️ Google News含めすべての RSS に filter_by_keywords を適用。
            # 過去版は Google News をスキップしていたが、検索クエリの曖昧さで
            # 「Starbucks 売上」「ライフガード新商品」等が混入していたため。
            # 結果記事の本文に baby-specific 語が含まれることを確認する。
            kw_filtered = filter_by_keywords(articles)

        filtered = [
            a
            for a in kw_filtered
            if not is_hard_noise(a)
            and not is_denylisted(a)
            and not is_seo_market_report(a)
            and not is_too_old(a)
            and not is_old_topic_title(a)
        ]
        all_articles.extend(filtered)
        print(
            f"[OK] {feed_config['name']}: {len(filtered)} 件採用 "
            f"(取得: {len(articles)} / フィルタ後: {len(kw_filtered)})"
        )

    deduped = deduplicate(all_articles)
    print(f"[OK] 重複除去後: {len(deduped)} 件")
    return deduped
