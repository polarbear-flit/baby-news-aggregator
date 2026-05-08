"""フィード取得・正規化・ノイズ除外・重複除去。

設計方針:
- fetch_type で取得方法をディスパッチ（rss / html_caa_recall 等）。
- HARD_NOISE は完全除外、SOFT_NOISE はスコアリング側で減点（ここでは除外しない）。
- 重複除去は normalize_title + rapidfuzz の類似度ベース（rapidfuzz未インストール時は完全一致フォールバック）。
"""
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

try:
    from bs4 import BeautifulSoup  # type: ignore
    HAS_BS4 = True
except ImportError:  # pragma: no cover
    HAS_BS4 = False

from src.config import (
    RSS_FEEDS, KEYWORDS, HARD_NOISE_TERMS, CRITICAL_OVERRIDE,
    PAST_YEAR_TITLE_PATTERNS,
    MAX_ARTICLES_PER_FEED, FETCH_TIMEOUT_SEC, USER_AGENT,
)

# 古すぎる記事は完全除外（日次Botに数年前のニュースは不要）
MAX_ARTICLE_AGE_DAYS = 90
# 重複判定の類似度しきい値（0-100）。88以上を重複扱いにする。
DEDUP_SIMILARITY_THRESHOLD = 88


def normalize_title(title: str) -> str:
    """重複検出用のタイトル正規化。

    画像N/M, 写真N/M、末尾の媒体名（| ブランド | - メディア）、括弧内、
    句読点、空白を除去して比較しやすくする。
    """
    if not title:
        return ""
    s = title
    # 画像N/M, 写真N/M を除去
    s = re.sub(r"画像\s*\d+\s*[/／]\s*\d+", "", s)
    s = re.sub(r"写真\s*\d+\s*[/／]\s*\d+", "", s)
    # 末尾の媒体名（| メディア / - メディア など）を除去
    s = re.sub(r"\s*[|｜\-－‐]\s*[^|｜\-－‐]+$", "", s)
    # 括弧内文字列を除去
    s = re.sub(r"[【\[\(（][^】\]\)）]*[】\]\)）]", "", s)
    # 句読点・記号を除去
    s = re.sub(r"[、。!！?？\"'‘’“”「」『』]", "", s)
    # 空白を完全除去
    s = re.sub(r"\s+", "", s)
    return s.lower()


def _parse_dt(entry) -> Optional[datetime]:
    """feedparserのtime.struct_timeをdatetimeに変換。取れなければNone。"""
    for field in ("published_parsed", "updated_parsed"):
        t = getattr(entry, field, None)
        if t:
            try:
                return datetime(*t[:6], tzinfo=timezone.utc)
            except Exception:
                pass
    return None


def _fetch_rss(feed_config: dict) -> list[dict]:
    """RSS/Atom フィードを取得して Article リストを返す。"""
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


# 消費者庁こども向けはベビー食品以外（菓子・サラミ・塩昆布等）も多く含むため、
# ベビー用品EC事業に関連するキーワードでフィルタする。
CAA_BABY_RELEVANT_KEYWORDS = [
    # ベビー用品・育児カテゴリ
    "ベビー", "赤ちゃん", "乳幼児", "新生児", "幼児", "乳児",
    "おむつ", "オムツ", "紙おむつ", "おしりふき",
    "ミルク", "哺乳瓶", "哺乳びん", "授乳", "母乳",
    "離乳食", "ベビーフード", "幼児食",
    "ベビーカー", "チャイルドシート", "カーシート",
    "抱っこひも", "抱っこ紐", "スリング", "ベビーキャリア",
    "ベビーベッド", "バウンサー", "ハイチェア",
    "ベビー服", "ベビー肌着", "スタイ", "よだれかけ",
    # 玩具系（こども安全に直結）
    "おもちゃ", "玩具", "知育", "ぬいぐるみ",
    # スキンケア
    "ベビーソープ", "ベビーローション", "ベビーオイル",
]


def _is_baby_relevant(text: str) -> bool:
    """文字列がベビー用品EC事業に関連するキーワードを含むか判定。"""
    text_lower = (text or "").lower()
    return any(kw.lower() in text_lower for kw in CAA_BABY_RELEVANT_KEYWORDS)


def _fetch_html_caa_recall(feed_config: dict) -> list[dict]:
    """消費者庁リコール「こども向け」をHTMLスクレイピング。

    URL形式: https://www.recall.caa.go.jp/result/index.php?screenkbn=05
    各リコール行に詳細リンク `/result/detail.php?rcl=ID&...` がある前提。
    日付（YYYY/MM/DD）はrow全体から正規表現で抽出する。

    注意: こども向けリコールは食品（菓子・ハム等）も多く含むため、
    ベビー用品関連キーワード（ミルク・哺乳瓶・玩具・ベビー等）にマッチするものだけ採用する。
    """
    MAX_CAA_ITEMS = 5  # 念のため上限を設定（実際のフィルタは関連性で絞る）
    if not HAS_BS4:
        print(f"[SKIP] {feed_config['name']}: beautifulsoup4 未インストール")
        return []

    BASE = "https://www.recall.caa.go.jp"
    articles: list[dict] = []
    skipped_irrelevant = 0
    try:
        resp = requests.get(
            feed_config["url"],
            headers={"User-Agent": USER_AGENT},
            timeout=FETCH_TIMEOUT_SEC,
        )
        resp.raise_for_status()
        resp.encoding = resp.apparent_encoding or "utf-8"
        soup = BeautifulSoup(resp.text, "html.parser")

        seen_ids: set[str] = set()
        # 詳細リンクを起点に各リコール項目を抽出
        for link in soup.select('a[href*="/result/detail.php"]'):
            href = link.get("href", "")
            rcl_match = re.search(r"rcl=(\d+)", href)
            if not rcl_match:
                continue
            rcl_id = rcl_match.group(1)
            if rcl_id in seen_ids:
                continue
            seen_ids.add(rcl_id)

            # URL正規化
            if href.startswith("/"):
                full_url = BASE + href
            elif href.startswith("http"):
                full_url = href
            else:
                full_url = BASE + "/result/" + href

            link_text = link.get_text(" ", strip=True)
            if not link_text:
                continue

            # ベビー用品EC事業に関連するもののみ採用（食品・菓子・サラミ等は除外）
            row_for_check = link.find_parent("tr") or link.find_parent("li") or link.parent
            row_text_full = (
                row_for_check.get_text(" ", strip=True) if row_for_check else link_text
            )
            if not _is_baby_relevant(row_text_full):
                skipped_irrelevant += 1
                continue

            # 周辺セルから日付（YYYY/MM/DD）を抽出
            row = link.find_parent("tr") or link.find_parent("li") or link.parent
            published_dt: Optional[datetime] = None
            published_str = ""
            if row is not None:
                row_text = row.get_text(" ", strip=True)
                date_match = re.search(r"(\d{4})[/\-](\d{1,2})[/\-](\d{1,2})", row_text)
                if date_match:
                    try:
                        published_dt = datetime(
                            int(date_match.group(1)),
                            int(date_match.group(2)),
                            int(date_match.group(3)),
                            tzinfo=timezone.utc,
                        )
                        published_str = published_dt.strftime("%Y-%m-%d")
                    except Exception:
                        pass

            articles.append({
                "title": "[消費者庁リコール] " + link_text[:180],
                "url": full_url,
                "summary": "消費者庁リコール（こども向け）公式情報",
                "published": published_str,
                "published_dt": published_dt,
                "source_name": feed_config["name"],
                "source_type": feed_config.get("source_type", "official_recall"),
                "category": feed_config["category"],
                "language": feed_config["language"],
                "matched_keywords": ["リコール"],
            })

            if len(articles) >= MAX_CAA_ITEMS:
                break

        if skipped_irrelevant:
            print(
                f"[INFO] {feed_config['name']}: ベビー用品関連 {len(articles)} 件採用 / "
                f"{skipped_irrelevant} 件は食品等のため除外"
            )
        return articles
    except Exception as e:
        print(f"[SKIP] {feed_config['name']}: {e}")
        return []


def _fetch_html_meti(feed_config: dict) -> list[dict]:
    """経産省 製品安全 - 未実装スタブ。今後 PSC マーク・法令改正等を取得予定。"""
    print(f"[SKIP] {feed_config['name']}: html_meti は未実装スタブ")
    return []


def _fetch_html_nite(feed_config: dict) -> list[dict]:
    """NITE 製品事故・リコール - 未実装スタブ。SAFE-Lite等のスクレイピング検討。"""
    print(f"[SKIP] {feed_config['name']}: html_nite は未実装スタブ")
    return []


FETCH_DISPATCH = {
    "rss": _fetch_rss,
    "html_caa_recall": _fetch_html_caa_recall,
    "html_meti": _fetch_html_meti,
    "html_nite": _fetch_html_nite,
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
    """HARD_NOISE_TERMS該当の記事を完全除外判定。CRITICAL_OVERRIDE該当なら救う。

    企業名は CRITICAL_OVERRIDE に含めていないため、「西松屋 + 選び方ガイド」のような
    企業名+SEOコラム記事は除外される。
    """
    text = (article.get("title", "") + " " + article.get("summary", "")).lower()
    if any(t.lower() in text for t in CRITICAL_OVERRIDE):
        return False
    return any(t.lower() in text for t in HARD_NOISE_TERMS)


def is_too_old(article: dict) -> bool:
    """MAX_ARTICLE_AGE_DAYS より古い記事を除外。日付不明は許容（analyzerで減点）。"""
    published_dt = article.get("published_dt")
    if published_dt is None:
        return False
    cutoff = datetime.now(timezone.utc) - timedelta(days=MAX_ARTICLE_AGE_DAYS)
    return published_dt < cutoff


def is_old_topic_title(article: dict) -> bool:
    """タイトル/要約冒頭に過去年シグナル（2018年〜2025年/昨年/去年等）が含まれていれば
    古い記事と判定。

    Google News RSSは古い記事を再インデックスするとpubDateを更新するため、
    本文（タイトル+要約の冒頭150文字）から過去年を検出する必要がある。
    例: ユニ・チャームの2018年おむつ戦略記事が2026年扱いで配信されるケース。

    CRITICAL_OVERRIDE該当（リコール等）は古い年でも残す（重大継続案件のため）。
    """
    title = article.get("title", "")
    summary = article.get("summary", "")[:150]  # 本文冒頭のみ（年月撮影等の末尾誤検出を避ける）
    text_check = title + " " + summary
    text_lower = text_check.lower()
    if any(t.lower() in text_lower for t in CRITICAL_OVERRIDE):
        return False
    return any(p in text_check for p in PAST_YEAR_TITLE_PATTERNS)


def deduplicate(articles: list[dict]) -> list[dict]:
    """URL一致 + タイトル正規化+類似度（rapidfuzzあれば）で重複除去。

    画像1/34 と 画像3/34 のようなギャラリー記事は、normalize_title で
    「画像N/M」が除去されるため、同一タイトル扱いで重複排除される。
    """
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
            # フォールバック: 完全一致のみ
            if any(prev_norm == norm_title for prev_norm, _ in kept):
                is_dup = True

        if not is_dup:
            kept.append((norm_title, a))

    return [a for _, a in kept]


def fetch_all_feeds() -> list[dict]:
    """全フィード取得 → キーワードフィルタ → ノイズ・古さ除外 → 重複除去。"""
    all_articles: list[dict] = []
    for feed_config in RSS_FEEDS:
        articles = fetch_feed(feed_config)

        # キーワードフィルタ:
        # - Google Newsは検索クエリ自体がフィルタなのでカテゴリ語を擬似マッチさせる
        # - 公的ソース（fetch_type != "rss"）は既にmatched_keywords付き、または対象が明確なのでスキップ
        url = feed_config.get("url", "")
        fetch_type = feed_config.get("fetch_type", "rss")
        if fetch_type != "rss":
            kw_filtered = articles
        elif "news.google.com" in url:
            for a in articles:
                a["matched_keywords"] = [feed_config["category"]]
            kw_filtered = articles
        else:
            kw_filtered = filter_by_keywords(articles)

        filtered = [
            a for a in kw_filtered
            if not is_hard_noise(a)
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
