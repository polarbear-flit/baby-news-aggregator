"""Baby News Aggregator 設定 — 業界動向特化版。

設計方針:
- 目的を「ベビー用品EC事業のための業界動向把握」に統一。対象年齢は 0〜未就学児（〜6歳）。
- 全 Google News クエリの OR グループは括弧で囲んで site:/ベビー語のスコープを担保。
- KEYWORDS["general"] はベビー特化語のみ。汎用業界語（市場/EC/売上/メーカー単独等）は除外。
- HARD_NOISE に未就学児外（中学生/高校生/大学生）と無関係食品ブランドを追加。
- リコール/回収情報も HARD_NOISE で除外。
"""

RSS_FEEDS = [
    # === Google News 日本語（カテゴリ横断・必ずベビー文脈と AND）===
    {"name": "GNews: ベビー用品全般",       "url": "https://news.google.com/rss/search?q=ベビー用品+(業界+OR+市場+OR+EC+OR+トレンド)&hl=ja&gl=JP&ceid=JP:ja",          "category": "general",    "language": "ja", "source_type": "google_news", "fetch_type": "rss"},
    {"name": "GNews: 哺乳瓶・授乳",         "url": "https://news.google.com/rss/search?q=(哺乳瓶+OR+授乳+OR+粉ミルク)+(新商品+OR+メーカー+OR+発売)&hl=ja&gl=JP&ceid=JP:ja", "category": "feeding",    "language": "ja", "source_type": "google_news", "fetch_type": "rss"},
    {"name": "GNews: ベビーカー・チャイルドシート", "url": "https://news.google.com/rss/search?q=(ベビーカー+OR+チャイルドシート+OR+抱っこ紐)+(新商品+OR+発売+OR+メーカー)&hl=ja&gl=JP&ceid=JP:ja", "category": "mobility",   "language": "ja", "source_type": "google_news", "fetch_type": "rss"},
    {"name": "GNews: 紙おむつ・おしりふき", "url": "https://news.google.com/rss/search?q=(紙おむつ+OR+乳児用おむつ+OR+おしりふき)+(新商品+OR+メーカー+OR+赤ちゃん)&hl=ja&gl=JP&ceid=JP:ja", "category": "diaper", "language": "ja", "source_type": "google_news", "fetch_type": "rss"},
    {"name": "GNews: ベビースキンケア",     "url": "https://news.google.com/rss/search?q=(赤ちゃん+OR+ベビー)+(スキンケア+OR+ローション+OR+ベビーソープ)+新商品&hl=ja&gl=JP&ceid=JP:ja", "category": "skincare", "language": "ja", "source_type": "google_news", "fetch_type": "rss"},

    # === メーカー公式（site: でドメイン限定 + ベビー文脈で AND）===
    {"name": "Pigeon 公式",         "url": "https://news.google.com/rss/search?q=site:pigeon.co.jp&hl=ja&gl=JP&ceid=JP:ja",   "category": "general", "language": "ja", "source_type": "brand_official", "fetch_type": "rss"},
    {"name": "ユニチャーム ベビー部門", "url": "https://news.google.com/rss/search?q=site:unicharm.co.jp+(ベビー+OR+ムーニー+OR+乳児+OR+赤ちゃん)&hl=ja&gl=JP&ceid=JP:ja", "category": "general", "language": "ja", "source_type": "brand_official", "fetch_type": "rss"},
    {"name": "コンビ 公式",          "url": "https://news.google.com/rss/search?q=site:combi.co.jp&hl=ja&gl=JP&ceid=JP:ja",   "category": "mobility", "language": "ja", "source_type": "brand_official", "fetch_type": "rss"},
    {"name": "リッチェル 公式",      "url": "https://news.google.com/rss/search?q=site:richell.co.jp&hl=ja&gl=JP&ceid=JP:ja", "category": "general", "language": "ja", "source_type": "brand_official", "fetch_type": "rss"},
    {"name": "花王 ベビー部門",      "url": "https://news.google.com/rss/search?q=site:kao.com+(メリーズ+OR+ベビー+OR+赤ちゃん+OR+乳児)&hl=ja&gl=JP&ceid=JP:ja", "category": "general", "language": "ja", "source_type": "brand_official", "fetch_type": "rss"},

    # === メーカー動向（ブランド名 × ベビー文脈、Google News 経由）===
    {"name": "GNews: 哺乳瓶・おむつメーカー", "url": "https://news.google.com/rss/search?q=(ピジョン+OR+ユニチャーム+OR+花王+OR+ムーニー+OR+メリーズ)+(赤ちゃん+OR+乳幼児+OR+ベビー)&hl=ja&gl=JP&ceid=JP:ja", "category": "general", "language": "ja", "source_type": "google_news", "fetch_type": "rss"},
    {"name": "GNews: ベビーカー・カーシートメーカー", "url": "https://news.google.com/rss/search?q=(コンビ+OR+アップリカ+OR+カトージ+OR+リッチェル)+(ベビーカー+OR+チャイルドシート+OR+ベビー用品)&hl=ja&gl=JP&ceid=JP:ja", "category": "mobility", "language": "ja", "source_type": "google_news", "fetch_type": "rss"},

    # === 小売公式（site: でドメイン限定）===
    {"name": "西松屋 公式",          "url": "https://news.google.com/rss/search?q=site:24028.jp&hl=ja&gl=JP&ceid=JP:ja",      "category": "general", "language": "ja", "source_type": "retailer_official", "fetch_type": "rss"},
    {"name": "赤ちゃん本舗 公式",    "url": "https://news.google.com/rss/search?q=site:akachan.jp&hl=ja&gl=JP&ceid=JP:ja",    "category": "general", "language": "ja", "source_type": "retailer_official", "fetch_type": "rss"},

    # === 小売動向（Google News 経由・ベビー文脈と AND）===
    {"name": "GNews: ベビー専門小売動向", "url": "https://news.google.com/rss/search?q=(西松屋+OR+赤ちゃん本舗+OR+アカチャンホンポ+OR+バースデイ)+(ベビー用品+OR+乳幼児+OR+赤ちゃん)&hl=ja&gl=JP&ceid=JP:ja", "category": "general", "language": "ja", "source_type": "google_news", "fetch_type": "rss"},
    {"name": "GNews: 量販 ベビー部門",    "url": "https://news.google.com/rss/search?q=(トイザらス+OR+ベビーザらス+OR+ニトリ+OR+イオン)+(ベビー用品+OR+乳幼児+OR+赤ちゃん)&hl=ja&gl=JP&ceid=JP:ja", "category": "general", "language": "ja", "source_type": "google_news", "fetch_type": "rss"},
    {"name": "GNews: EC ベビー部門",      "url": "https://news.google.com/rss/search?q=(楽天+OR+Amazon)+(ベビー用品+OR+乳幼児+OR+赤ちゃん用)&hl=ja&gl=JP&ceid=JP:ja", "category": "general", "language": "ja", "source_type": "google_news", "fetch_type": "rss"},

    # === 業界専門メディア（site: 検索）===
    {"name": "Diamond Retail Media", "url": "https://news.google.com/rss/search?q=site:diamond-rm.net+(ベビー+OR+育児+OR+乳幼児)&hl=ja&gl=JP&ceid=JP:ja",   "category": "general", "language": "ja", "source_type": "trade_press", "fetch_type": "rss"},
    {"name": "WWD Japan ベビー",      "url": "https://news.google.com/rss/search?q=site:wwdjapan.com+(ベビー+OR+乳幼児+OR+ベビーカー)&hl=ja&gl=JP&ceid=JP:ja", "category": "general", "language": "ja", "source_type": "trade_press", "fetch_type": "rss"},
    {"name": "通販新聞 ベビー",       "url": "https://news.google.com/rss/search?q=site:tsuhanshimbun.com+(ベビー+OR+乳幼児+OR+おむつ)&hl=ja&gl=JP&ceid=JP:ja", "category": "general", "language": "ja", "source_type": "trade_press", "fetch_type": "rss"},

    # === 市場調査（site: 検索）===
    {"name": "矢野経済研究所 ベビー",   "url": "https://news.google.com/rss/search?q=site:yano.co.jp+(ベビー+OR+育児+OR+乳幼児)&hl=ja&gl=JP&ceid=JP:ja", "category": "general", "language": "ja", "source_type": "market_research", "fetch_type": "rss"},
    {"name": "富士経済 ベビー",        "url": "https://news.google.com/rss/search?q=site:fuji-keizai.co.jp+(ベビー+OR+育児)&hl=ja&gl=JP&ceid=JP:ja", "category": "general", "language": "ja", "source_type": "market_research", "fetch_type": "rss"},

    # === 市場・EC動向（必ずベビー語と AND）===
    {"name": "GNews: 育児市場・EC動向",     "url": "https://news.google.com/rss/search?q=ベビー用品+(市場+OR+EC+OR+売上+OR+シェア+OR+販売)&hl=ja&gl=JP&ceid=JP:ja",  "category": "general", "language": "ja", "source_type": "google_news", "fetch_type": "rss"},
    {"name": "GNews: 育児消費・トレンド",   "url": "https://news.google.com/rss/search?q=(育児用品+OR+ベビー用品)+(消費+OR+トレンド+OR+流行+OR+ヒット商品)&hl=ja&gl=JP&ceid=JP:ja", "category": "general", "language": "ja", "source_type": "google_news", "fetch_type": "rss"},

    # === プレスリリース ===
    {"name": "PR TIMES ベビー用品（GNews経由）", "url": "https://news.google.com/rss/search?q=site:prtimes.jp+(ベビー用品+OR+乳幼児+OR+授乳+OR+おむつ)&hl=ja&gl=JP&ceid=JP:ja", "category": "general", "language": "ja", "source_type": "pr_wire", "fetch_type": "rss"},
    {"name": "PR TIMES ベビーカー・カーシート",  "url": "https://news.google.com/rss/search?q=site:prtimes.jp+(ベビーカー+OR+チャイルドシート+OR+抱っこ紐)&hl=ja&gl=JP&ceid=JP:ja", "category": "mobility", "language": "ja", "source_type": "pr_wire", "fetch_type": "rss"},
]

# === KEYWORDS — 業界動向特化版 ===
# 汎用業界語（市場/EC/売上/メーカー/小売 単独）は撤去。これらが入っていた時に
# 「Starbucks 売上前年比増」のような無関係記事も general カテゴリで通っていた問題を解消。
KEYWORDS = {
    "feeding":    ["哺乳瓶", "bottle", "feeding", "formula", "breastfeeding", "nipple", "授乳", "母乳", "粉ミルク", "離乳食"],
    "mobility":   ["ベビーカー", "stroller", "pram", "pushchair", "buggy", "抱っこひも", "抱っこ紐", "スリング"],
    "car_safety": ["カーシート", "car seat", "child restraint", "booster seat", "チャイルドシート"],
    "diaper":     ["紙おむつ", "diaper", "nappy", "pampers", "huggies", "オムツ", "乳児用おむつ"],
    "wipes":      ["おしりふき", "baby wipes", "wet wipes", "cleansing wipe", "ウェットシート"],
    "skincare":   ["ベビーソープ", "ベビーローション", "ベビーオイル", "baby lotion", "baby cream",
                   "赤ちゃん肌", "乳児湿疹"],
    # general はベビー特化語のみ。汎用業界語は撤去。
    "general":    ["baby", "infant", "赤ちゃん", "乳幼児", "乳児", "育児",
                   "ベビー用品", "ベビー服", "ベビー雑貨", "新生児", "幼児", "未就学児",
                   "マタニティ", "妊婦", "妊娠中", "産後", "出産"],
}

# === HARD_NOISE_TERMS: 完全除外（CRITICAL_OVERRIDE が空なので例外なし）===
HARD_NOISE_TERMS = [
    # === リコール系（ユーザー要望で完全除外）===
    "リコール", "回収", "recall", "自主回収", "重大製品事故", "誤飲", "窒息", "事故防止", "事故情報",
    "回収のお知らせ", "返金", "交換対応",
    # === 未就学児外の年齢層（ユーザー要望: 〜6歳まで）===
    "中学生", "中学校", "高校生", "高校", "大学生", "大学", "成人",
    "小中学生", "中高生", "小学校高学年", "塾",
    # === 完全に無関係な食品・飲料・店舗 ===
    "東京ばな奈", "セブンイレブン", "セブン-イレブン", "セブン‐イレブン",
    "バーガーキング", "マクドナルド", "ケンタッキー",
    "スターバックス", "スタバ", "ドトール", "コメダ",
    "ライフガード", "モンテール", "ミスタードーナツ", "ミスド",
    "焼肉", "ラーメン",
    # === 画像・写真ギャラリー ===
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

# === SOFT_NOISE_TERMS: スコア減点（-20）===
SOFT_NOISE_TERMS = [
    "おすすめ", "ランキング", "選び方",
    "口コミレビュー", "まとめ",
    "プレゼント特集",
    "best baby", "guide to",
    "フェア", "キャンペーン",
]

# === CRITICAL_OVERRIDE: 空（過去の救済が漏れの原因だったため撤廃）===
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

# === 業界動向シグナル（スコア加点用）===
INDUSTRY_TERMS = [
    "新商品", "新製品", "発売", "リニューアル", "新ブランド",
    "市場", "シェア", "売上", "販売", "EC", "D2C", "サブスク",
    "出店", "新店", "店舗", "改装", "PB", "プライベートブランド",
    "値上げ", "価格改定", "決算", "業績",
    "提携", "資本", "買収", "合弁",
]

# === ソース種別ごとのスコア重み ===
SOURCE_WEIGHTS = {
    "brand_official":    35,
    "retailer_official": 32,
    "market_research":   30,
    "trade_press":       25,
    "pr_wire":           18,
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
