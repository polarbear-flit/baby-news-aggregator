"""Baby News Aggregator 設定 — 業界動向特化版。

設計方針:
- 目的を「ベビー用品EC事業のための業界動向把握」に統一。
- リコール/回収情報は HARD_NOISE で除外（ユーザー要望: チャットを邪魔しない）。
- CRITICAL_OVERRIDE は空にし、ノイズ判定の例外を作らない（過去の漏れの主因）。
- ソースは「メーカー / 小売 / 市場・EC / 消費者トレンド」の4軸を捕捉する形に再構成。
"""

RSS_FEEDS = [
    # === Google News 日本語（カテゴリ横断） ===
    {"name": "GNews: ベビー用品全般",       "url": "https://news.google.com/rss/search?q=ベビー用品+業界+OR+市場+OR+EC&hl=ja&gl=JP&ceid=JP:ja",                "category": "general",    "language": "ja", "source_type": "google_news", "fetch_type": "rss"},
    {"name": "GNews: 哺乳瓶・授乳",         "url": "https://news.google.com/rss/search?q=哺乳瓶+OR+授乳+OR+ミルク+新商品+OR+メーカー&hl=ja&gl=JP&ceid=JP:ja",   "category": "feeding",    "language": "ja", "source_type": "google_news", "fetch_type": "rss"},
    {"name": "GNews: ベビーカー・チャイルドシート", "url": "https://news.google.com/rss/search?q=ベビーカー+OR+チャイルドシート+新商品+OR+発売&hl=ja&gl=JP&ceid=JP:ja", "category": "mobility",   "language": "ja", "source_type": "google_news", "fetch_type": "rss"},
    {"name": "GNews: おむつ・おしりふき",   "url": "https://news.google.com/rss/search?q=おむつ+OR+おしりふき+新商品+OR+メーカー&hl=ja&gl=JP&ceid=JP:ja",        "category": "diaper",     "language": "ja", "source_type": "google_news", "fetch_type": "rss"},
    {"name": "GNews: ベビースキンケア",     "url": "https://news.google.com/rss/search?q=赤ちゃん+スキンケア+OR+ローション+OR+ベビーソープ+新商品&hl=ja&gl=JP&ceid=JP:ja", "category": "skincare", "language": "ja", "source_type": "google_news", "fetch_type": "rss"},

    # === メーカー公式（site: で公式IRページに絞る — source_type=brand_official）===
    {"name": "Pigeon 公式",         "url": "https://news.google.com/rss/search?q=site:pigeon.co.jp&hl=ja&gl=JP&ceid=JP:ja",   "category": "general", "language": "ja", "source_type": "brand_official", "fetch_type": "rss"},
    {"name": "ユニチャーム 公式",    "url": "https://news.google.com/rss/search?q=site:unicharm.co.jp+ベビー+OR+おむつ+OR+ムーニー&hl=ja&gl=JP&ceid=JP:ja", "category": "general", "language": "ja", "source_type": "brand_official", "fetch_type": "rss"},
    {"name": "コンビ 公式",          "url": "https://news.google.com/rss/search?q=site:combi.co.jp&hl=ja&gl=JP&ceid=JP:ja",   "category": "mobility", "language": "ja", "source_type": "brand_official", "fetch_type": "rss"},
    {"name": "リッチェル 公式",      "url": "https://news.google.com/rss/search?q=site:richell.co.jp&hl=ja&gl=JP&ceid=JP:ja", "category": "general", "language": "ja", "source_type": "brand_official", "fetch_type": "rss"},
    {"name": "花王 ベビー関連",      "url": "https://news.google.com/rss/search?q=site:kao.com+ベビー+OR+メリーズ+OR+赤ちゃん&hl=ja&gl=JP&ceid=JP:ja", "category": "general", "language": "ja", "source_type": "brand_official", "fetch_type": "rss"},

    # === メーカー動向（ブランド名 × ベビー用品文脈で AND、Google News）===
    {"name": "GNews: 哺乳瓶・おむつメーカー", "url": "https://news.google.com/rss/search?q=ピジョン+OR+ユニチャーム+OR+花王+OR+ムーニー+赤ちゃん+OR+乳幼児+OR+おむつ+OR+授乳&hl=ja&gl=JP&ceid=JP:ja", "category": "general", "language": "ja", "source_type": "google_news", "fetch_type": "rss"},
    {"name": "GNews: ベビーカー・カーシートメーカー", "url": "https://news.google.com/rss/search?q=コンビ+OR+アップリカ+OR+カトージ+OR+リッチェル+ベビーカー+OR+チャイルドシート+OR+ベビー用品&hl=ja&gl=JP&ceid=JP:ja", "category": "mobility", "language": "ja", "source_type": "google_news", "fetch_type": "rss"},

    # === 小売公式（site: 検索 — source_type=retailer_official）===
    {"name": "西松屋 公式",          "url": "https://news.google.com/rss/search?q=site:24028.jp&hl=ja&gl=JP&ceid=JP:ja",      "category": "general", "language": "ja", "source_type": "retailer_official", "fetch_type": "rss"},
    {"name": "赤ちゃん本舗 公式",    "url": "https://news.google.com/rss/search?q=site:akachan.jp&hl=ja&gl=JP&ceid=JP:ja",    "category": "general", "language": "ja", "source_type": "retailer_official", "fetch_type": "rss"},

    # === 小売動向（Google News 経由）===
    {"name": "GNews: ベビー専門小売動向",   "url": "https://news.google.com/rss/search?q=西松屋+OR+赤ちゃん本舗+OR+アカチャンホンポ+OR+バースデイ+ベビー用品+OR+乳幼児+OR+新商品+OR+店舗&hl=ja&gl=JP&ceid=JP:ja", "category": "general", "language": "ja", "source_type": "google_news", "fetch_type": "rss"},
    {"name": "GNews: 量販・EC ベビー部門",  "url": "https://news.google.com/rss/search?q=トイザらス+OR+ベビーザらス+OR+ニトリ+OR+イオン+OR+楽天+OR+Amazon+ベビー用品+OR+乳幼児+OR+おむつ&hl=ja&gl=JP&ceid=JP:ja", "category": "general", "language": "ja", "source_type": "google_news", "fetch_type": "rss"},

    # === 業界専門メディア（site: 検索 — source_type=trade_press）===
    {"name": "Diamond Retail Media", "url": "https://news.google.com/rss/search?q=site:diamond-rm.net+ベビー+OR+育児+OR+乳幼児&hl=ja&gl=JP&ceid=JP:ja",   "category": "general", "language": "ja", "source_type": "trade_press", "fetch_type": "rss"},
    {"name": "WWD Japan ベビー",      "url": "https://news.google.com/rss/search?q=site:wwdjapan.com+ベビー+OR+乳幼児+OR+ベビーカー&hl=ja&gl=JP&ceid=JP:ja", "category": "general", "language": "ja", "source_type": "trade_press", "fetch_type": "rss"},
    {"name": "通販新聞 ベビー",       "url": "https://news.google.com/rss/search?q=site:tsuhanshimbun.com+ベビー+OR+乳幼児+OR+おむつ&hl=ja&gl=JP&ceid=JP:ja", "category": "general", "language": "ja", "source_type": "trade_press", "fetch_type": "rss"},

    # === 市場調査（site: 検索 — source_type=market_research）===
    {"name": "矢野経済研究所 ベビー",   "url": "https://news.google.com/rss/search?q=site:yano.co.jp+ベビー+OR+育児+OR+乳幼児&hl=ja&gl=JP&ceid=JP:ja", "category": "general", "language": "ja", "source_type": "market_research", "fetch_type": "rss"},
    {"name": "富士経済 ベビー",        "url": "https://news.google.com/rss/search?q=site:fuji-keizai.co.jp+ベビー+OR+育児&hl=ja&gl=JP&ceid=JP:ja",     "category": "general", "language": "ja", "source_type": "market_research", "fetch_type": "rss"},

    # === 市場・EC動向（Google News）===
    {"name": "GNews: 育児市場・EC動向",     "url": "https://news.google.com/rss/search?q=ベビー用品+市場+OR+EC+OR+売上+OR+シェア+OR+販売&hl=ja&gl=JP&ceid=JP:ja",  "category": "general", "language": "ja", "source_type": "google_news", "fetch_type": "rss"},
    {"name": "GNews: 育児消費・トレンド",   "url": "https://news.google.com/rss/search?q=育児用品+OR+ベビー用品+消費+OR+トレンド+OR+流行+OR+ヒット商品&hl=ja&gl=JP&ceid=JP:ja", "category": "general", "language": "ja", "source_type": "google_news", "fetch_type": "rss"},

    # === プレスリリース ===
    {"name": "PR TIMES ベビー用品（GNews経由）", "url": "https://news.google.com/rss/search?q=site:prtimes.jp+ベビー用品+OR+乳幼児+OR+授乳+OR+おむつ&hl=ja&gl=JP&ceid=JP:ja", "category": "general", "language": "ja", "source_type": "pr_wire", "fetch_type": "rss"},
    {"name": "PR TIMES ベビーカー・カーシート",  "url": "https://news.google.com/rss/search?q=site:prtimes.jp+ベビーカー+OR+チャイルドシート+OR+抱っこ紐&hl=ja&gl=JP&ceid=JP:ja", "category": "mobility", "language": "ja", "source_type": "pr_wire", "fetch_type": "rss"},
]

KEYWORDS = {
    "feeding":    ["哺乳瓶", "bottle", "feeding", "formula", "breastfeeding", "nipple", "授乳", "母乳", "ミルク", "離乳食"],
    "mobility":   ["ベビーカー", "stroller", "pram", "pushchair", "buggy", "抱っこひも", "スリング"],
    "car_safety": ["カーシート", "car seat", "child restraint", "booster seat", "チャイルドシート"],
    "diaper":     ["おむつ", "diaper", "nappy", "pampers", "huggies", "オムツ", "紙おむつ"],
    "wipes":      ["おしりふき", "baby wipes", "wet wipes", "cleansing wipe", "ウェットシート"],
    "skincare":   ["スキンケア", "baby lotion", "baby cream", "eczema", "baby wash", "sensitive skin", "baby oil",
                   "赤ちゃん肌", "乳児湿疹", "保湿", "無添加", "オーガニック", "低刺激"],
    "general":    ["新製品", "new product", "baby", "infant", "赤ちゃん", "乳幼児",
                   "育児", "子育て", "ベビー", "新生児", "幼児", "子ども用品", "ベビー用品", "マタニティ",
                   "市場", "EC", "売上", "販売", "シェア", "出店", "新店", "メーカー", "小売"],
}

# === HARD_NOISE_TERMS: 完全除外（CRITICAL_OVERRIDE が空なので例外なし）===
# リコール/回収もここに含める（ユーザー要望: 業界動向Botでは邪魔）
HARD_NOISE_TERMS = [
    # === リコール系（ユーザー要望で完全除外）===
    "リコール", "回収", "recall", "自主回収", "重大製品事故", "誤飲", "窒息", "事故防止", "事故情報",
    "回収のお知らせ", "返金", "交換対応",
    # === 完全に無関係なブランド・店舗 ===
    "東京ばな奈", "セブンイレブン", "セブン-イレブン", "セブン‐イレブン",
    "バーガーキング", "マクドナルド", "ケンタッキー",
    # === 画像・写真ギャラリー（記事本文ではない）===
    "フォトギャラリー", "画像", "写真",
    # === 過剰SEO/ガイド ===
    "完全ガイド", "選び方ガイド", "選び方も紹介",
    "100均", "百均", "ダイソー", "セリア",
    "best of", "top 10", "top10",
    # === 感情・コラム系 ===
    "かわいすぎ", "あるある", "育児あるある", "わが子",
    # === 検証/プロモ系 ===
    "検証レビュー", "PR記事", "タイアップ",
    # === 地域販促 ===
    "閉店", "開店", "地域ニュース",
    # === 著名人ゴシップ ===
    "芸能人", "タレント", "インスタで報告", "出産報告",
]

# === SOFT_NOISE_TERMS: スコア減点（-20）するが AI判定候補には残す ===
SOFT_NOISE_TERMS = [
    "おすすめ", "ランキング", "選び方",
    "口コミレビュー", "まとめ",
    "プレゼント特集",
    "best baby", "guide to",
    "フェア", "キャンペーン",
]

# === CRITICAL_OVERRIDE: 空（過去のリコール救済が漏れの原因だったため撤廃）===
# どんな記事もノイズ語があれば例外なくHARD/SOFT判定される。
CRITICAL_OVERRIDE: list[str] = []

# === 過去年シグナル（タイトル/要約に含まれていれば古い記事と判定）===
PAST_YEAR_TITLE_PATTERNS = [
    "2018年", "2019年", "2020年", "2021年", "2022年", "2023年",
    "2024年", "2025年",
    "2018 年", "2019 年", "2020 年", "2021 年", "2022 年", "2023 年",
    "2024 年", "2025 年",
    "昨年", "去年", "前年", "一昨年",
]

# === 主要企業/小売エンティティ（スコア加点専用）===
KEY_ENTITIES = [
    "ピジョン", "Pigeon", "コンビ", "Combi", "アップリカ", "Aprica",
    "カトージ", "KATOJI", "リッチェル", "Richell",
    "ユニ・チャーム", "ユニチャーム", "ムーニー", "Moony",
    "花王", "メリーズ", "Pampers", "パンパース",
    "西松屋", "赤ちゃん本舗", "アカチャンホンポ", "バースデイ",
    "ニトリ", "イオン", "トイザらス", "ベビーザらス", "楽天", "Amazon",
    "Ergobaby", "エルゴ", "ベビービョルン", "BabyBjorn",
]

# === 業界動向シグナル（スコア加点用、リコール語は意図的に外す）===
INDUSTRY_TERMS = [
    "新商品", "新製品", "発売", "リニューアル", "新ブランド",
    "市場", "シェア", "売上", "販売", "EC", "D2C", "サブスク",
    "出店", "新店", "店舗", "改装", "PB", "プライベートブランド",
    "値上げ", "価格改定", "決算", "業績",
    "提携", "資本", "買収", "合弁",
]

# === ソース種別ごとのスコア重み（リコール・規制系は撤廃、業界系のみ）===
SOURCE_WEIGHTS = {
    "brand_official":    35,  # メーカー公式（将来追加用）
    "retailer_official": 32,  # 小売公式（将来追加用）
    "market_research":   30,  # 矢野経済研究所等
    "trade_press":       25,  # 通販新聞・流通新聞等
    "pr_wire":           18,  # PR TIMES等
    "google_news":       10,
    "seo_media":          0,
}

TREND_WINDOW_DAYS = 30
MAX_ARTICLES_PER_FEED = 20
MAX_ARTICLES_DISPLAY = 50
OUTPUT_PATH = "docs/index.html"
HISTORY_PATH = "data/history.json"
FETCH_TIMEOUT_SEC = 15
USER_AGENT = "Mozilla/5.0 (compatible; BabyNewsAggregator/1.0)"
DEFAULT_REPORT_URL = "https://polarbear-flit.github.io/baby-news-aggregator/"
