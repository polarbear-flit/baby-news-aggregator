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
    # PR TIMES（日本語プレスリリース）
    {"name": "PR TIMES: ベビー", "url": "https://prtimes.jp/rss20.xml", "category": "general", "language": "ja"},
    # Baby Gaga（動作確認済み）
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
