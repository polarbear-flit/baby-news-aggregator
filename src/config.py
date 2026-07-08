"""Baby News Aggregator 設定 — 業界動向特化版。

設計方針:
- 目的を「ベビー用品EC事業のための業界動向把握」に統一。対象年齢は 0〜未就学児（〜6歳）。
- 2026-07-08 ソース再設計: site: 型 Google News クエリ（メーカー/小売/業界紙/市場調査の
  公式ドメイン検索）は「そのドメインの古いインデックス済みページ」を返して採用0件で全滅
  していたため全廃。代わりに ①純正RSS（PR TIMES/流通ニュース/ダイヤモンドRM）を直接取得、
  ②Google News クエリには全て `when:7d` を付けて7日以内に強制する。
- KEYWORDS["general"] に素の「ベビー」等を追加（「ベビー関連」「ベビー・子ども用品」を拾う）。
  入口は広めに倒し、誤爆は HARD_NOISE と AI リランカーの is_relevant=false で吸収する。
- HARD_NOISE に未就学児外（中学生/高校生/大学生）と無関係食品ブランドを追加。
- リコール/回収情報も HARD_NOISE で除外。
- DOMAIN_DENYLIST でスパム/機械翻訳SEO/まとめサイトをドメイン・媒体名で除外。
"""

RSS_FEEDS = [
    # === プレス/業界紙（site: + when: で「その媒体のベビー関連の最新記事」を取得）===
    # 検証(2026-07-08): 純正 index.rdf/feed は「全ジャンル最新N件のスナップショット」で
    # ベビー記事がほぼ含まれず採用0件。一方 Google News の site:+when: は
    # 「その媒体のベビー関連×直近」を横断検索でき、prtimes は100件/日ヒットした。
    # ※メーカー/店舗の公式ドメイン(pigeon.co.jp等)は静的な商品/店舗ページばかり返すため
    #   site: は使わない（撤去済み）。site: を使うのはプレス/ニュース媒体に限る。
    {
        "name": "PR TIMES ベビー",
        "url": "https://news.google.com/rss/search?q=site:prtimes.jp+(ベビー+OR+乳幼児+OR+赤ちゃん+OR+授乳+OR+おむつ+OR+ベビーカー+OR+チャイルドシート)+when:7d&hl=ja&gl=JP&ceid=JP:ja",
        "category": "general",
        "language": "ja",
        "source_type": "pr_wire",
        "fetch_type": "rss",
        "max_articles": 30,
    },
    {
        "name": "流通ニュース ベビー",
        "url": "https://news.google.com/rss/search?q=site:ryutsuu.biz+(ベビー+OR+乳幼児+OR+赤ちゃん+OR+ベビー用品)+when:14d&hl=ja&gl=JP&ceid=JP:ja",
        "category": "general",
        "language": "ja",
        "source_type": "trade_press",
        "fetch_type": "rss",
    },
    {
        "name": "ダイヤモンド・チェーンストア ベビー",
        "url": "https://news.google.com/rss/search?q=site:diamond-rm.net+(ベビー+OR+育児+OR+乳幼児+OR+赤ちゃん本舗)+when:14d&hl=ja&gl=JP&ceid=JP:ja",
        "category": "general",
        "language": "ja",
        "source_type": "trade_press",
        "fetch_type": "rss",
    },
    # === Google News 日本語（全クエリに when:7d を付与。実測で7日以内に絞れることを確認）===
    {
        "name": "GNews: ベビー用品業界",
        "url": "https://news.google.com/rss/search?q=ベビー用品+(業界+OR+市場+OR+EC+OR+シェア+OR+売上+OR+トレンド)+when:7d&hl=ja&gl=JP&ceid=JP:ja",
        "category": "general",
        "language": "ja",
        "source_type": "google_news",
        "fetch_type": "rss",
    },
    {
        "name": "GNews: 哺乳瓶・授乳",
        "url": "https://news.google.com/rss/search?q=(哺乳瓶+OR+授乳+OR+粉ミルク)+(新商品+OR+メーカー+OR+発売)+when:7d&hl=ja&gl=JP&ceid=JP:ja",
        "category": "feeding",
        "language": "ja",
        "source_type": "google_news",
        "fetch_type": "rss",
    },
    {
        "name": "GNews: ベビーカー・チャイルドシート",
        "url": "https://news.google.com/rss/search?q=(ベビーカー+OR+チャイルドシート+OR+抱っこ紐)+(新商品+OR+発売+OR+メーカー)+when:7d&hl=ja&gl=JP&ceid=JP:ja",
        "category": "mobility",
        "language": "ja",
        "source_type": "google_news",
        "fetch_type": "rss",
    },
    {
        "name": "GNews: 紙おむつ・おしりふき",
        "url": "https://news.google.com/rss/search?q=(紙おむつ+OR+乳児用おむつ+OR+おしりふき)+(新商品+OR+メーカー+OR+赤ちゃん)+when:7d&hl=ja&gl=JP&ceid=JP:ja",
        "category": "diaper",
        "language": "ja",
        "source_type": "google_news",
        "fetch_type": "rss",
    },
    {
        "name": "GNews: ベビースキンケア",
        "url": "https://news.google.com/rss/search?q=(赤ちゃん+OR+ベビー)+(スキンケア+OR+ローション+OR+ベビーソープ)+新商品+when:7d&hl=ja&gl=JP&ceid=JP:ja",
        "category": "skincare",
        "language": "ja",
        "source_type": "google_news",
        "fetch_type": "rss",
    },
    # === メーカー動向（ブランド名 × ベビー文脈、when:7d 付き Google News）===
    {
        "name": "GNews: 主要メーカー",
        "url": "https://news.google.com/rss/search?q=(ピジョン+OR+コンビ+OR+アップリカ+OR+カトージ+OR+リッチェル+OR+ユニ・チャーム+OR+ユニチャーム+OR+花王+OR+ムーニー+OR+メリーズ)+(ベビー+OR+赤ちゃん+OR+乳幼児+OR+ベビーカー+OR+チャイルドシート+OR+おむつ)+when:7d&hl=ja&gl=JP&ceid=JP:ja",
        "category": "general",
        "language": "ja",
        "source_type": "google_news",
        "fetch_type": "rss",
    },
    # === 小売動向（when:7d 付き Google News）===
    {
        "name": "GNews: 主要小売",
        "url": "https://news.google.com/rss/search?q=(西松屋+OR+赤ちゃん本舗+OR+アカチャンホンポ+OR+バースデイ+OR+ベビーザらス+OR+トイザらス)+(ベビー+OR+乳幼児+OR+赤ちゃん+OR+ベビー用品)+when:7d&hl=ja&gl=JP&ceid=JP:ja",
        "category": "general",
        "language": "ja",
        "source_type": "google_news",
        "fetch_type": "rss",
    },
    {
        "name": "GNews: EC ベビー部門",
        "url": "https://news.google.com/rss/search?q=(楽天+OR+Amazon)+(ベビー用品+OR+乳幼児+OR+赤ちゃん用)+when:7d&hl=ja&gl=JP&ceid=JP:ja",
        "category": "general",
        "language": "ja",
        "source_type": "google_news",
        "fetch_type": "rss",
    },
    # === 市場調査（when:7d 付き Google News）===
    {
        "name": "GNews: 市場調査",
        "url": "https://news.google.com/rss/search?q=(矢野経済研究所+OR+富士経済+OR+市場調査+OR+市場規模)+(ベビー+OR+育児+OR+乳幼児+OR+ベビー用品)+when:7d&hl=ja&gl=JP&ceid=JP:ja",
        "category": "general",
        "language": "ja",
        "source_type": "market_research",
        "fetch_type": "rss",
    },
    # === 市場・EC動向・消費トレンド（when:7d 付き）===
    {
        "name": "GNews: 育児消費・トレンド",
        "url": "https://news.google.com/rss/search?q=(育児用品+OR+ベビー用品)+(消費+OR+トレンド+OR+流行+OR+ヒット商品+OR+D2C+OR+サブスク)+when:7d&hl=ja&gl=JP&ceid=JP:ja",
        "category": "general",
        "language": "ja",
        "source_type": "google_news",
        "fetch_type": "rss",
    },
]

# === KEYWORDS — 業界動向特化版 ===
# 汎用業界語（市場/EC/売上/メーカー/小売 単独）は撤去。これらが入っていた時に
# 「Starbucks 売上前年比増」のような無関係記事も general カテゴリで通っていた問題を解消。
KEYWORDS = {
    "feeding": [
        "哺乳瓶",
        "bottle",
        "feeding",
        "formula",
        "breastfeeding",
        "nipple",
        "授乳",
        "母乳",
        "粉ミルク",
        "離乳食",
    ],
    "mobility": [
        "ベビーカー",
        "stroller",
        "pram",
        "pushchair",
        "buggy",
        "抱っこひも",
        "抱っこ紐",
        "スリング",
    ],
    "car_safety": [
        "カーシート",
        "car seat",
        "child restraint",
        "booster seat",
        "チャイルドシート",
    ],
    "diaper": [
        "紙おむつ",
        "diaper",
        "nappy",
        "pampers",
        "huggies",
        "オムツ",
        "乳児用おむつ",
    ],
    "wipes": [
        "おしりふき",
        "baby wipes",
        "wet wipes",
        "cleansing wipe",
        "ウェットシート",
    ],
    "skincare": [
        "ベビーソープ",
        "ベビーローション",
        "ベビーオイル",
        "baby lotion",
        "baby cream",
        "赤ちゃん肌",
        "乳児湿疹",
    ],
    # general はベビー特化語のみ。汎用業界語は撤去。
    # 2026-07-08: 素の「ベビー」「こども/子ども用品」を追加。旧版は複合語（ベビー用品等）
    # しかなく「ベビー関連ビジネス市場調査」「ベビー・子ども用品」等の最高価値記事を
    # キーワード不一致で落としていたため。誤爆は HARD_NOISE と AI で吸収する。
    "general": [
        "baby",
        "infant",
        "赤ちゃん",
        "乳幼児",
        "乳児",
        "育児",
        "ベビー",
        "ベビー用品",
        "ベビー服",
        "ベビー雑貨",
        "ベビー・子ども",
        "こども用品",
        "子ども用品",
        "子供用品",
        "新生児",
        "幼児",
        "未就学児",
        "マタニティ",
        "妊婦",
        "妊娠中",
        "産後",
        "出産",
    ],
}

# === HARD_NOISE_TERMS: 完全除外（CRITICAL_OVERRIDE が空なので例外なし）===
HARD_NOISE_TERMS = [
    # === リコール系（ユーザー要望で完全除外）===
    "リコール",
    "回収",
    "recall",
    "自主回収",
    "重大製品事故",
    "誤飲",
    "窒息",
    "事故防止",
    "事故情報",
    "回収のお知らせ",
    "返金",
    "交換対応",
    # === 未就学児外の年齢層（ユーザー要望: 〜6歳まで）===
    "中学生",
    "中学校",
    "高校生",
    "高校",
    "大学生",
    "大学",
    "成人",
    "小中学生",
    "中高生",
    "小学校高学年",
    "塾",
    # === 完全に無関係な食品・飲料・店舗 ===
    "東京ばな奈",
    "セブンイレブン",
    "セブン-イレブン",
    "セブン‐イレブン",
    "バーガーキング",
    "マクドナルド",
    "ケンタッキー",
    "スターバックス",
    "スタバ",
    "ドトール",
    "コメダ",
    "ライフガード",
    "モンテール",
    "ミスタードーナツ",
    "ミスド",
    "焼肉",
    "ラーメン",
    # === 画像・写真ギャラリー ===
    "フォトギャラリー",
    "画像",
    "写真",
    # === 過剰SEO/ガイド ===
    "完全ガイド",
    "選び方ガイド",
    "選び方も紹介",
    "100均",
    "百均",
    "ダイソー",
    "セリア",
    "best of",
    "top 10",
    "top10",
    # === 感情・コラム系 ===
    "かわいすぎ",
    "あるある",
    "育児あるある",
    "わが子",
    # === 検証/プロモ系 ===
    "検証レビュー",
    "PR記事",
    "タイアップ",
    # === 地域販促 ===
    "閉店",
    "開店",
    "地域ニュース",
    # === 著名人ゴシップ ===
    "芸能人",
    "タレント",
    "インスタで報告",
    "出産報告",
]

# === DOMAIN_DENYLIST: ドメイン or 媒体名で完全除外（実配信で確認したスパム/低品質）===
# Google News のリダイレクトURL(news.google.com)はドメイン判定できないため、
# 「記事URL」または「タイトル末尾の媒体名（ ` - 媒体名` ）」のいずれかに当てる。
DOMAIN_DENYLIST = [
    "richardajkeys.com",  # P&Gリリースを盗用したスクレイパースパム
    "fortunebusinessinsights.com",  # 機械翻訳SEO市場レポート（「〜市場規模、シェア、2034」等）
    "my-best.com",  # マイベスト（ランキングまとめ）
    "mybest",  # マイベスト（媒体名表記ゆれ・英字）
    "マイベスト",  # マイベスト（日本語媒体名）
    "jimosh",  # ジモッシュ（地域イベントメディア・英字）
    "ジモッシュ",  # ジモッシュ（日本語媒体名）
]

# === DOMAIN_ALLOWLIST_BONUS: 信頼ソースへのスコア加点 ===
# 記事URLはGoogle Newsのリダイレクトになるため、URL・媒体名・タイトル末尾で照合する。
# キーは実際に現れる表記（タイトル末尾「 - PR TIMES」やドメイン）に小文字で合わせる。
DOMAIN_ALLOWLIST_BONUS = {
    "prtimes.jp": 5,
    "pr times": 5,
    "ryutsuu.biz": 10,
    "流通ニュース": 10,
    "diamond-rm.net": 10,
    "ダイヤモンド・チェーンストア": 10,
}

# === SOFT_NOISE_TERMS: スコア減点（-20）===
SOFT_NOISE_TERMS = [
    "おすすめ",
    "ランキング",
    "選び方",
    "口コミレビュー",
    "まとめ",
    "プレゼント特集",
    "best baby",
    "guide to",
    "フェア",
    "キャンペーン",
]

# === CRITICAL_OVERRIDE: 空（過去の救済が漏れの原因だったため撤廃）===
CRITICAL_OVERRIDE: list[str] = []

# === 過去年シグナル（タイトル/要約に含まれていれば古い記事と判定）===
PAST_YEAR_TITLE_PATTERNS = [
    "2018年",
    "2019年",
    "2020年",
    "2021年",
    "2022年",
    "2023年",
    "2024年",
    "2025年",
    "2018 年",
    "2019 年",
    "2020 年",
    "2021 年",
    "2022 年",
    "2023 年",
    "2024 年",
    "2025 年",
    "昨年",
    "去年",
    "前年",
    "一昨年",
]

# === 主要企業/小売エンティティ（スコア加点専用）===
KEY_ENTITIES = [
    "ピジョン",
    "Pigeon",
    "コンビ",
    "Combi",
    "アップリカ",
    "Aprica",
    "カトージ",
    "KATOJI",
    "リッチェル",
    "Richell",
    "ユニ・チャーム",
    "ユニチャーム",
    "ムーニー",
    "Moony",
    "花王",
    "メリーズ",
    "Pampers",
    "パンパース",
    "西松屋",
    "赤ちゃん本舗",
    "アカチャンホンポ",
    "バースデイ",
    "ニトリ",
    "イオン",
    "トイザらス",
    "ベビーザらス",
    "楽天",
    "Amazon",
    "Ergobaby",
    "エルゴ",
    "ベビービョルン",
    "BabyBjorn",
]

# === 業界動向シグナル（スコア加点用）===
INDUSTRY_TERMS = [
    "新商品",
    "新製品",
    "発売",
    "リニューアル",
    "新ブランド",
    "市場",
    "シェア",
    "売上",
    "販売",
    "EC",
    "D2C",
    "サブスク",
    "出店",
    "新店",
    "店舗",
    "改装",
    "PB",
    "プライベートブランド",
    "値上げ",
    "価格改定",
    "決算",
    "業績",
    "提携",
    "資本",
    "買収",
    "合弁",
]

# === ソース種別ごとのスコア重み ===
SOURCE_WEIGHTS = {
    "brand_official": 35,
    "retailer_official": 32,
    "market_research": 30,
    "trade_press": 25,
    "pr_wire": 18,
    "google_news": 10,
    "seo_media": 0,
}

TREND_WINDOW_DAYS = 30
MAX_ARTICLES_PER_FEED = 20
MAX_ARTICLES_DISPLAY = 50
OUTPUT_PATH = "docs/index.html"
HISTORY_PATH = "data/history.json"
DELIVERED_PATH = "data/delivered.json"
FETCH_TIMEOUT_SEC = 15
USER_AGENT = "Mozilla/5.0 (compatible; BabyNewsAggregator/1.0)"
DEFAULT_REPORT_URL = "https://polarbear-flit.github.io/baby-news-aggregator/"
