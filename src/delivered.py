"""配信済み記事の記憶（cross-day dedup）— 「毎日同じ記事」を防ぐ層。

data/delivered.json に「レポート掲載した記事」を記録し、翌日以降の実行で
同一URL・類似タイトル・同一クラスタの記事を「既報(redelivery)」として降格する。

判定の柱:
1. 正規化URL一致（最も確実）
2. normalize_title の fuzz 類似度（同一記事・別URL を捕捉）
3. cluster_key の fuzz 類似度（同一プレスリリースの別媒体版を翌日以降も捕捉）

30日より古いレコードは prune_delivered で掃除する。
"""

import json
import os
from datetime import datetime, timedelta, timezone

from src.config import DELIVERED_PATH  # noqa: F401  (re-export for callers)
from src.fetcher import normalize_title

try:
    from rapidfuzz import fuzz  # type: ignore

    HAS_RAPIDFUZZ = True
except ImportError:  # pragma: no cover
    HAS_RAPIDFUZZ = False

# cross-day は同一記事の別URL/別媒体版まで拾いたいので、within-day(88)より少し緩める。
REDELIVERY_SIMILARITY_THRESHOLD = 85
# delivered.json の保持日数（trend窓と揃える）。
DELIVERED_KEEP_DAYS = 30


def _norm_url(url: str) -> str:
    return (url or "").rstrip("/").lower()


def _today_jst() -> str:
    jst = timezone(timedelta(hours=9))
    return datetime.now(jst).strftime("%Y-%m-%d")


def load_delivered(path: str) -> dict:
    """delivered.json を読み込む。存在しない/壊れている場合は空ストア。"""
    if not os.path.exists(path):
        return {"articles": []}
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict) and isinstance(data.get("articles"), list):
            return data
    except Exception:
        pass
    return {"articles": []}


def save_delivered(store: dict, path: str) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(store, f, ensure_ascii=False, indent=2)


def prune_delivered(
    store: dict, today: str | None = None, keep_days: int = DELIVERED_KEEP_DAYS
) -> dict:
    """last_delivered が keep_days より古いレコードを除去した新ストアを返す。"""
    today = today or _today_jst()
    try:
        cutoff = datetime.strptime(today, "%Y-%m-%d") - timedelta(days=keep_days)
    except ValueError:
        return store
    kept = []
    for rec in store.get("articles", []):
        ld = rec.get("last_delivered", "")
        try:
            if datetime.strptime(ld, "%Y-%m-%d") >= cutoff:
                kept.append(rec)
        except (ValueError, TypeError):
            # 日付不明のレコードは安全側に倒して保持（次回上書きされる）
            kept.append(rec)
    return {"articles": kept}


def _fuzzy_match(a: str, b: str, threshold: int) -> bool:
    if not a or not b:
        return False
    if HAS_RAPIDFUZZ:
        return fuzz.ratio(a, b) >= threshold
    return a == b


def is_already_delivered(
    article: dict,
    store: dict,
    threshold: int = REDELIVERY_SIMILARITY_THRESHOLD,
) -> bool:
    """記事が過去に配信済みかを判定する。

    - URL 一致
    - タイトル正規化の fuzz 類似度 >= threshold
    - cluster_key の fuzz 類似度 >= threshold
    のいずれかに該当すれば True。
    """
    url_norm = _norm_url(article.get("url", ""))
    title_norm = normalize_title(article.get("title", ""))
    art_cluster = article.get("cluster_key") or title_norm

    for rec in store.get("articles", []):
        if url_norm and url_norm == rec.get("url_norm", ""):
            return True
        rec_title = rec.get("title_norm", "")
        if _fuzzy_match(title_norm, rec_title, threshold):
            return True
        rec_cluster = rec.get("cluster_key", "")
        if _fuzzy_match(art_cluster, rec_cluster, threshold):
            return True
    return False


def split_by_delivery(
    articles: list[dict], store: dict
) -> tuple[list[dict], list[dict]]:
    """記事を (新着, 既報) に分割する。既報には redelivery=True を付与。"""
    fresh: list[dict] = []
    redelivered: list[dict] = []
    for a in articles:
        if is_already_delivered(a, store):
            a["redelivery"] = True
            redelivered.append(a)
        else:
            a["redelivery"] = False
            fresh.append(a)
    return fresh, redelivered


def upsert_delivered(
    store: dict, articles: list[dict], today: str | None = None
) -> dict:
    """今回配信した記事を delivered.json ストアへ登録/更新する。

    既存レコード（URL一致 or タイトル一致）は last_delivered と delivered_count を
    更新。新規は first_seen=today で追加する。
    """
    today = today or _today_jst()
    index_by_url: dict[str, dict] = {}
    for rec in store.get("articles", []):
        if rec.get("url_norm"):
            index_by_url[rec["url_norm"]] = rec

    for a in articles:
        url_norm = _norm_url(a.get("url", ""))
        title_norm = normalize_title(a.get("title", ""))
        cluster_key = a.get("cluster_key") or title_norm

        rec = index_by_url.get(url_norm) if url_norm else None
        if rec is None:
            # タイトル一致の既存レコードを探す
            for r in store.get("articles", []):
                if _fuzzy_match(
                    title_norm, r.get("title_norm", ""), REDELIVERY_SIMILARITY_THRESHOLD
                ):
                    rec = r
                    break

        if rec is not None:
            rec["last_delivered"] = today
            rec["delivered_count"] = rec.get("delivered_count", 1) + 1
            if url_norm and not rec.get("url_norm"):
                rec["url_norm"] = url_norm
                index_by_url[url_norm] = rec
        else:
            new_rec = {
                "url_norm": url_norm,
                "title_norm": title_norm,
                "group_id": a.get("duplicate_group_id", ""),
                "cluster_key": cluster_key,
                "first_seen": today,
                "last_delivered": today,
                "delivered_count": 1,
            }
            store.setdefault("articles", []).append(new_rec)
            if url_norm:
                index_by_url[url_norm] = new_rec

    return store
