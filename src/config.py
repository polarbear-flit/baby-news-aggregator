"""Baby News Aggregator 設定。

設計方針:
- CRITICAL_OVERRIDE は安全・規制ワードだけに限定する。
  企業名でノイズ記事が救済される問題を防ぐため、ブランド名はKEY_ENTITIESにのみ置く。
- HARD_NOISE_TERMS は完全除外。SOFT_NOISE_TERMS はスコア減点のみで AI 判定候補に残す。
- フィードは fetch_type で取得方法を切り替える（rss / html_caa_recall / html_meti / html_nite 等）。
"""

RSS_FEEDS = [
    # === Google News 日本語（カテゴリ横断） ===
    {"name": "GNews: ベビー用品全般",       "url": "https://news.google.com/rss/search?q=ベビー用品&hl=ja&gl=JP&ceid=JP:ja",                              "category": "general",    "language": "ja", "source_type": "google_news", "fetch_type": "rss"},
    {"name": "GNews: 哺乳瓶・授乳",         "url": "https://news.google.com/rss/search?q=哺乳瓶+授乳+ミルク&hl=ja&gl=JP&ceid=JP:ja",                     "category": "feeding",    "language": "ja", "source_type": "google_news", "fetch_type": "rss"},
    {"name": "GNews: ベビーカー・チャイルドシート", "url": "https://news.google.com/rss/search?q=ベビーカー+チャイルドシート&hl=ja&gl=JP&ceid=JP:ja",  "category": "mobility",   "language": "ja", "source_type": "google_news", "fetch_type": "rss"},
    {"name": "GNews: おむつ・おしりふき",   "url": "https://news.google.com/rss/search?q=おむつ+おしりふき&hl=ja&gl=JP&ceid=JP:ja",                       "category": "diaper",     "language": "ja", "source_type": "google_news", "fetch_type": "rss"},
    {"name": "GNews: ベビースキンケア",     "url": "https://news.google.com/rss/search?q=赤ちゃん+スキンケア+保湿&hl=ja&gl=JP&ceid=JP:ja",                "category": "skincare",   "language": "ja", "source_type": "google_news", "fetch_type": "rss"},
    {"name": "GNews: ベビー用品リコール",   "url": "https://news.google.com/rss/search?q=ベビー+リコール+安全+乳幼児&hl=ja&gl=JP&ceid=JP:ja",              "category": "general",    "language": "ja", "source_type": "google_news", "fetch_type": "rss"},
    {"name": "GNews: 育児市場トレンド",     "url": "https://news.google.com/rss/search?q=育児+市場+新製品+子育て&hl=ja&gl=JP&ceid=JP:ja",                  "category": "general",    "language": "ja", "source_type": "google_news", "fetch_type": "rss"},

    # === Google News 日本語（ブランド別。必ずベビー用品文脈とAND） ===
    # 哺乳瓶/おむつ系メーカー × カテゴリ語
    {"name": "GNews: 哺乳瓶・おむつメーカー", "url": "https://news.google.com/rss/search?q=ピジョン+OR+ユニチャーム+OR+花王+OR+ムーニー+赤ちゃん+OR+乳幼児+OR+おむつ+OR+授乳&hl=ja&gl=JP&ceid=JP:ja", "category": "general",  "language": "ja", "source_type": "google_news", "fetch_type": "rss"},
    # ベビーカー/チャイルドシート系メーカー × カテゴリ語
    {"name": "GNews: ベビーカー・カーシートメーカー", "url": "https://news.google.com/rss/search?q=コンビ+OR+アップリカ+OR+カトージ+OR+リッチェル+ベビーカー+OR+チャイルドシート+OR+ベビー用品&hl=ja&gl=JP&ceid=JP:ja", "category": "mobility", "language": "ja", "source_type": "google_news", "fetch_type": "rss"},
    # 主要小売 × ベビー用品文脈（東京ばな奈やセブンの食品PRが混入しないようにベビー用品とAND）
    {"name": "GNews: ベビー小売動向",       "url": "https://news.google.com/rss/search?q=西松屋+OR+赤ちゃん本舗+OR+アカチャンホンポ+ベビー用品+OR+乳幼児+OR+新商品&hl=ja&gl=JP&ceid=JP:ja", "category": "general", "language": "ja", "source_type": "google_news", "fetch_type": "rss"},
    {"name": "GNews: 育児市場・EC動向",     "url": "https://news.google.com/rss/search?q=ベビー用品+市場+OR+EC+OR+売上+OR+シェア&hl=ja&gl=JP&ceid=JP:ja",  "category": "general", "language": "ja", "source_type": "google_news", "fetch_type": "rss"},
    {"name": "GNews: 規制・PSC・安全",      "url": "https://news.google.com/rss/search?q=乳幼児+OR+ベビー+PSC+OR+規制+OR+消費者庁+OR+NITE&hl=ja&gl=JP&ceid=JP:ja", "category": "general", "language": "ja", "source_type": "google_news", "fetch_type": "rss"},

    # === Google News 英語（輸入品リコール監視のみに絞る） ===
    {"name": "GNews: stroller car seat (海外リコール)", "url": "https://news.google.com/rss/search?q=stroller+car+seat+recall&hl=en&gl=US&ceid=US:en",       "category": "car_safety", "language": "en", "source_type": "google_news", "fetch_type": "rss"},
    {"name": "GNews: diaper wipes recall (海外リコール)", "url": "https://news.google.com/rss/search?q=diaper+baby+wipes+recall+safety&hl=en&gl=US&ceid=US:en", "category": "diaper",  "language": "en", "source_type": "google_news", "fetch_type": "rss"},

    # === 公的ソース ===
    {"name": "消費者庁リコール（こども向け）", "url": "https://www.recall.caa.go.jp/result/index.php?screenkbn=05", "category": "general", "language": "ja", "source_type": "official_recall", "fetch_type": "html_caa_recall"},
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

# === ノイズ判定 ===
# HARD_NOISE_TERMS: 完全除外（CRITICAL_OVERRIDE該当のみ救済）。
# 「画像」「写真」「フォトギャラリー」など、明らかに記事ではないギャラリー系を含む。
HARD_NOISE_TERMS = [
    # 完全に無関係なブランド・店舗
    "東京ばな奈", "セブンイレブン", "セブン-イレブン", "セブン‐イレブン",
    "バーガーキング", "マクドナルド",
    # 画像・写真ギャラリー（記事本文ではないため除外）
    "フォトギャラリー", "画像", "写真",
    # 過剰SEO/ガイド
    "完全ガイド", "選び方ガイド", "選び方も紹介",
    "100均", "百均", "ダイソー", "セリア",
    "best of", "top 10", "top10",
    # 感情記事
    "かわいすぎ",
    # 検証/レビュー（プロモ系）
    "検証レビュー",
    # 地域販促・閉店開店（商品担当の意思決定に直結しない）
    "閉店", "開店", "地域ニュース",
]

# SOFT_NOISE_TERMS: スコア減点（-20）するが、AI判定候補には残す。
SOFT_NOISE_TERMS = [
    "おすすめ", "ランキング", "選び方",
    "口コミレビュー", "まとめ",
    "育児あるある", "芸能人", "プレゼント特集",
    "best baby", "guide to",
    "フェア", "キャンペーン",
]

# CRITICAL_OVERRIDE: 安全・規制ワードに限定。これが含まれる記事はノイズ判定で救済される。
# ブランド名は KEY_ENTITIES に置き、加点だけに使う（ノイズ救済はしない）。
CRITICAL_OVERRIDE = [
    "リコール", "回収", "重大製品事故", "誤飲", "窒息",
    "PSC", "ST規格", "STマーク", "SGマーク",
    "規制", "法改正", "施行", "技術基準", "表示義務",
    "recall", "safety alert", "hazard",
]

# 過去年シグナル（タイトル含有時に古い記事と判定）
PAST_YEAR_TITLE_PATTERNS = [
    "2024年", "2024 年",
    "2025年", "2025 年",
    "昨年", "去年", "前年", "一昨年",
]

# スコア加点に使う主要企業/小売エンティティ（CRITICAL_OVERRIDEには入れない）
KEY_ENTITIES = [
    "ピジョン", "Pigeon", "コンビ", "Combi", "アップリカ", "Aprica",
    "カトージ", "KATOJI", "リッチェル", "Richell",
    "ユニ・チャーム", "ユニチャーム", "ムーニー", "Moony",
    "花王", "メリーズ", "Pampers", "パンパース",
    "西松屋", "赤ちゃん本舗", "アカチャンホンポ",
    "ニトリ", "イオン", "トイザらス", "ベビーザらス",
    "Ergobaby", "エルゴ", "ベビービョルン", "BabyBjorn",
]

# 安全・規制シグナル語（スコア加点）
SAFETY_TERMS = ["リコール", "回収", "事故", "誤飲", "窒息", "重大製品事故", "recall", "hazard"]
REGULATION_TERMS = ["PSC", "ST規格", "SGマーク", "規制", "法改正", "施行", "技術基準", "表示義務"]

# ソース種別ごとのスコア重み（高いほど信頼度・価値が高い）
SOURCE_WEIGHTS = {
    "official_recall":     50,  # 消費者庁リコール、CPSC等
    "official_regulation": 45,  # 経産省、消費者庁、こども家庭庁
    "official_safety":     42,  # NITE、国民生活センター
    "brand_official":      30,  # メーカー公式
    "retailer_official":   28,  # 小売公式
    "market_research":     26,  # 矢野経済研究所等
    "pr_wire":             15,  # PR TIMES等
    "google_news":         10,
    "seo_media":            0,
}

TREND_WINDOW_DAYS = 30
MAX_ARTICLES_PER_FEED = 20
MAX_ARTICLES_DISPLAY = 50
OUTPUT_PATH = "docs/index.html"
HISTORY_PATH = "data/history.json"
FETCH_TIMEOUT_SEC = 15
USER_AGENT = "Mozilla/5.0 (compatible; BabyNewsAggregator/1.0)"

# Telegram通知から日次レポートに飛ぶためのデフォルトURL（環境変数で上書き可）
DEFAULT_REPORT_URL = "https://polarbear-flit.github.io/baby-news-aggregator/"
