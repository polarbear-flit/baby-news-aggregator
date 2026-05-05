RSS_FEEDS = [
    # Google News 日本語（キーワード検索RSS）
    {"name": "GNews: ベビー用品全般", "url": "https://news.google.com/rss/search?q=ベビー用品&hl=ja&gl=JP&ceid=JP:ja", "category": "general", "language": "ja", "source_type": "google_news"},
    {"name": "GNews: 哺乳瓶・授乳", "url": "https://news.google.com/rss/search?q=哺乳瓶+授乳+ミルク&hl=ja&gl=JP&ceid=JP:ja", "category": "feeding", "language": "ja", "source_type": "google_news"},
    {"name": "GNews: ベビーカー・チャイルドシート", "url": "https://news.google.com/rss/search?q=ベビーカー+チャイルドシート&hl=ja&gl=JP&ceid=JP:ja", "category": "mobility", "language": "ja", "source_type": "google_news"},
    {"name": "GNews: おむつ・おしりふき", "url": "https://news.google.com/rss/search?q=おむつ+おしりふき&hl=ja&gl=JP&ceid=JP:ja", "category": "diaper", "language": "ja", "source_type": "google_news"},
    {"name": "GNews: ベビースキンケア", "url": "https://news.google.com/rss/search?q=赤ちゃん+スキンケア+保湿&hl=ja&gl=JP&ceid=JP:ja", "category": "skincare", "language": "ja", "source_type": "google_news"},
    {"name": "GNews: ベビー用品リコール", "url": "https://news.google.com/rss/search?q=ベビー+リコール+安全+乳幼児&hl=ja&gl=JP&ceid=JP:ja", "category": "general", "language": "ja", "source_type": "google_news"},
    {"name": "GNews: 育児市場トレンド", "url": "https://news.google.com/rss/search?q=育児+市場+新製品+子育て&hl=ja&gl=JP&ceid=JP:ja", "category": "general", "language": "ja", "source_type": "google_news"},
    # Google News 英語
    {"name": "GNews: baby products market", "url": "https://news.google.com/rss/search?q=baby+products+market+trend&hl=en&gl=US&ceid=US:en", "category": "general", "language": "en", "source_type": "google_news"},
    {"name": "GNews: stroller car seat", "url": "https://news.google.com/rss/search?q=stroller+car+seat+infant&hl=en&gl=US&ceid=US:en", "category": "car_safety", "language": "en", "source_type": "google_news"},
    {"name": "GNews: diaper wipes recall", "url": "https://news.google.com/rss/search?q=diaper+baby+wipes+recall+safety&hl=en&gl=US&ceid=US:en", "category": "diaper", "language": "en", "source_type": "google_news"},
    {"name": "GNews: baby skincare formula", "url": "https://news.google.com/rss/search?q=baby+skincare+formula+infant+lotion&hl=en&gl=US&ceid=US:en", "category": "skincare", "language": "en", "source_type": "google_news"},
    # Baby Gaga（動作確認済み）
    {"name": "Baby Gaga", "url": "https://www.babygaga.com/feed/", "category": "general", "language": "en", "source_type": "seo_media"},
    # PR TIMES rss20.xml は全分野の混入が多いため除外。必要になったらキーワードページを別ロジックで追加する。
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

# SEO/コラム系のノイズ語。タイトル/要約に含まれていれば原則除外する。
NOISE_TERMS = [
    "おすすめ", "ランキング", "選び方", "完全ガイド", "口コミレビュー",
    "まとめ", "育児あるある", "芸能人", "プレゼント特集",
    "100均", "百均", "ダイソー", "セリア",
    "best of", "top 10", "top10", "best baby", "guide to",
]

# ノイズ語が入っていても「絶対に落としてはいけない」記事を救うキーワード。
CRITICAL_OVERRIDE = [
    # 安全・規制
    "リコール", "回収", "重大製品事故", "誤飲", "窒息", "PSC",
    "ST規格", "SGマーク", "規制", "法改正", "施行", "技術基準",
    "recall", "safety alert", "hazard",
    # 主要メーカー・小売
    "ピジョン", "Pigeon", "コンビ", "Combi", "アップリカ", "Aprica",
    "カトージ", "KATOJI", "リッチェル", "Richell",
    "ユニ・チャーム", "ユニチャーム", "ムーニー", "Moony",
    "花王", "メリーズ", "Pampers", "パンパース", "Huggies", "ハギーズ",
    "西松屋", "赤ちゃん本舗", "アカチャンホンポ", "バースデイ",
    "トイザらス", "ベビーザらス", "ニトリ", "イオン",
    "Ergobaby", "エルゴ", "ベビービョルン", "BabyBjorn",
]

# スコア加点に使う主要企業/小売エンティティ（CRITICAL_OVERRIDEと一部重複してOK）
KEY_ENTITIES = [
    "ピジョン", "Pigeon", "コンビ", "Combi", "アップリカ", "Aprica",
    "カトージ", "KATOJI", "リッチェル", "Richell",
    "ユニ・チャーム", "ユニチャーム", "ムーニー", "Moony",
    "花王", "メリーズ", "Pampers", "パンパース",
    "西松屋", "赤ちゃん本舗", "アカチャンホンポ",
    "ニトリ", "イオン", "トイザらス", "ベビーザらス",
    "Ergobaby", "エルゴ", "ベビービョルン", "BabyBjorn",
]

# 安全・規制シグナル語
SAFETY_TERMS = ["リコール", "回収", "事故", "誤飲", "窒息", "重大製品事故", "recall", "hazard"]
REGULATION_TERMS = ["PSC", "ST規格", "SGマーク", "規制", "法改正", "施行", "技術基準", "表示義務"]

# ソース種別ごとのスコア重み（高いほど信頼度・価値が高い）
SOURCE_WEIGHTS = {
    "official_recall":     50,  # 消費者庁リコール、CPSC等（Step 3で追加予定）
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
