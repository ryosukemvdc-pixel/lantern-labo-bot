"""
らんたんLABO 士業向けSNS自動配信ボット (イベント集客特化版)
================================
毎日3回、LINEに以下を配信:
  - 朝8時 (JST): 一般ニュースサイト中心(1業種フォーカス)
  - 昼12時(JST): 士業業界全体向け軽い読み物
  - 夕方17時(JST): 公的機関中心(1業種フォーカス)

各回、X(Twitter)・Instagram・Facebook用に最適化された3つの投稿文 + 画像 + チラシを一括配信。
ニュースを「問題提起のフック」として、らんたんLABO Opening Session への参加申込に
誘導する構成。

8つの士業を1日ずつローテーション:
  税理士 → 弁護士 → 社労士 → 司法書士 → 行政書士 → 会計士 → 弁理士 → 中小企業診断士
"""

import os
import sys
import json
import urllib.parse
from datetime import datetime, timezone, timedelta

import requests

# ============================================================
# Configuration
# ============================================================

ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY")
LINE_CHANNEL_ACCESS_TOKEN = os.environ.get("LINE_CHANNEL_ACCESS_TOKEN")
LINE_TARGET_ID = os.environ.get("LINE_TARGET_ID")
# 士業向け申込URLと一般向け申込URL
APPLY_URL_SHIGYO = os.environ.get("APPLY_URL_SHIGYO", "").strip()
APPLY_URL_GENERAL = os.environ.get("APPLY_URL_GENERAL", "").strip()
# 後方互換: APPLY_URL のみ設定された場合は両方に使う
_legacy_apply_url = os.environ.get("APPLY_URL", "https://lantern-labo.com/apply").strip()
if not APPLY_URL_SHIGYO:
    APPLY_URL_SHIGYO = _legacy_apply_url
if not APPLY_URL_GENERAL:
    APPLY_URL_GENERAL = _legacy_apply_url

# プロンプトや本文に埋め込むために整形した「2つのURL」ブロック
APPLY_URLS_BLOCK = f"""🏢 士業の方:
{APPLY_URL_SHIGYO}

👤 一般の方:
{APPLY_URL_GENERAL}"""

# イベントチラシのHTTPS画像URL(任意)
FLYER_IMAGE_URL = os.environ.get("FLYER_IMAGE_URL", "").strip()

SLOT = os.environ.get("SLOT", "auto")
DRY_RUN = os.environ.get("DRY_RUN", "false").lower() == "true"

# ============================================================
# Event Countdown
# ============================================================

EVENT_DATE = datetime(2026, 6, 19, 18, 0, tzinfo=timezone(timedelta(hours=9)))


def get_countdown_message(now=None):
    """イベントまでのカウントダウンメッセージを生成"""
    if now is None:
        now = datetime.now(timezone(timedelta(hours=9)))

    delta = EVENT_DATE - now
    days = delta.days

    # イベント当日(その日のうち)
    if 0 <= days < 1 and now.date() == EVENT_DATE.date():
        if delta.total_seconds() > 0:
            hours = int(delta.total_seconds() // 3600)
            if hours <= 0:
                return "🎉 本日まもなく開催!会場でお待ちしています!"
            return f"🎉 本日開催!START まで あと {hours} 時間!"
        return "🎉 開催中!"

    # 翌日に開催
    if days == 0 or (days == 1 and now.hour >= 18):
        return "⏰ いよいよ明日開催!お申込みは本日中に!"

    # 数日前まで
    if 1 <= days <= 3:
        return f"🔥 あと {days} 日!残席わずか、お早めに!"

    if 4 <= days <= 7:
        return f"⏰ 開催まで あと {days} 日!"

    if 8 <= days <= 30:
        return f"🏮 開催まで あと {days} 日!"

    if 31 <= days <= 90:
        return f"🏮 開催まで あと {days} 日"

    # 90日より先
    if days > 90:
        return f"📅 {EVENT_DATE.month}/{EVENT_DATE.day} 開催 (あと {days} 日)"

    # イベント終了後
    return None  # Noneの場合はカウントダウン非表示

# ============================================================
# Event Information (used in every post)
# ============================================================

EVENT_INFO = {
    "name": "らんたんLABO Opening Session",
    "tagline": "本気で遊び、本気で学ぶ",
    "date": "2026年6月19日(金) 18:00 START (受付17:30)",
    "venue": "ロイヤルパークホテル日本橋 2階 春海/有明",
    "venue_address": "東京都中央区日本橋蛎殻町2-1-1",
    "fee_shigyo": "15,000円(税込)",
    "fee_general": "20,000円(税込)",
    "schedule": "17:30 受付 / 18:00 オープニング / 18:10 講演 / 19:10 交流会",
    "themes": "挑戦・組織づくり・教育",
    "organizer": "らんたん株式会社",
    "leaders": "代表 庄司絢子 / 副代表 今井亮輔(税理士)",
    "community_pillars": [
        "暗くなりがちな士業業界を温かく照らす居場所",
        "専門を超えた士業同士の連携・協業",
        "AI時代だからこそ対面のコミュニケーションを大切に",
        "会員専用LP無料提供などの福利厚生",
        "毎月の交流会＋勉強会で最新トレンドを",
    ],
    "guest_1": {
        "name": "水谷暢宏(みずたに のぶひろ)氏",
        "title": "おもしろビジネスアカデミー校長",
        "bio": "元吉本クリエイティブエージェンシー(元吉本興業)社長。NSC(吉本総合芸能学院)校長として2,000名以上の卒業生を業界に輩出。元吉本興業・教育部門担当取締役。広報PRコンサルタントとして中小企業支援も実施。「おもしろいで社会を元気に」をモットーに、おもしろビジネスアカデミーを設立。",
        "value": "話すプロを育ててきた視点と、組織改革の実践から、これからの士業に必要なヒントを語る",
    },
    "guest_2": {
        "name": "今井ようじ氏",
        "title": "おもしろビジネスアカデミー副校長 / 落語作家・構成作家 / 株式会社日本通信広告社代表取締役社長",
        "bio": "ラジオCM制作、構成作家を経て、2004年より新作落語の制作を開始。100冊以上の落語を制作し、落語台本コンクールで12回受賞。人気漫画「カイジ」の落語化台本も担当。落語を活用した地域振興にも取り組み、農林水産省「地域資源活用・地域連携中央プランナー」としても活動。",
        "value": "ストーリーテリングと『伝える技術』で、士業のコミュニケーションを変える",
    },
}

# ============================================================
# 8つの士業ローテーション
# ============================================================

SHIGYO_LIST = [
    {
        "name": "税理士",
        "search_focus": "税理士 税務 最新",
        "pain_points": [
            "毎月の税制改正・通達フォローが追いつかない",
            "顧問先からの想定外の相談(M&A・事業承継・国際税務)に独力で対応する不安",
            "AI・クラウド会計の波で記帳業務の付加価値が下がる懸念",
            "他士業との連携不足で顧問先の総合相談に乗りきれない",
            "事務所経営・採用・人材育成の悩み",
        ],
        "hot_topics": [
            "インボイス2割特例終了", "電子帳簿保存法", "税制改正", "賃上げ促進税制",
            "事業承継税制", "年収の壁178万円", "食事補助非課税枠", "相続税",
        ],
        "search_hashtags": [
            "#税理士", "#税理士事務所", "#税務", "#インボイス",
            "#電子帳簿保存法", "#税制改正", "#節税", "#顧問税理士",
        ],
    },
    {
        "name": "弁護士",
        "search_focus": "弁護士 法律 最新",
        "pain_points": [
            "労働事件・ハラスメント案件の急増に対応しきれない",
            "顧問先の労務・税務・知財など領域横断の相談を一人で受ける負担",
            "判例・法改正のキャッチアップに費やす時間",
            "中小企業向けマーケティング・集客の難しさ",
            "事務所経営とアソシエイトの育成",
        ],
        "hot_topics": [
            "労働事件", "企業法務", "相続", "ハラスメント",
            "判例", "法改正", "AI法規制", "個人情報保護",
        ],
        "search_hashtags": [
            "#弁護士", "#法律相談", "#企業法務", "#労働問題",
            "#相続", "#法改正", "#判例", "#弁護士事務所",
        ],
    },
    {
        "name": "社労士",
        "search_focus": "社会保険労務士 労務 最新",
        "pain_points": [
            "毎年の労働法改正と助成金制度のキャッチアップ負担",
            "ハラスメント・メンタルヘルス相談の急増",
            "クラウド人事システム導入支援に必要な提案力",
            "顧問先の経営課題に踏み込んだ提案ができていない焦り",
            "他士業との連携で総合的な労務支援を実現したい",
        ],
        "hot_topics": [
            "労働法改正", "助成金", "就業規則", "働き方改革",
            "ハラスメント対策", "賃金", "労働時間", "社会保険",
        ],
        "search_hashtags": [
            "#社労士", "#社会保険労務士", "#労務", "#助成金",
            "#就業規則", "#働き方改革", "#人事労務", "#労務管理",
        ],
    },
    {
        "name": "司法書士",
        "search_focus": "司法書士 登記 最新",
        "pain_points": [
            "相続登記義務化対応の問い合わせ激増",
            "登記オンライン化の中での業務効率化",
            "他士業(税理士・行政書士)との連携不足",
            "若年層への認知拡大・集客",
            "事務所経営と後継者問題",
        ],
        "hot_topics": [
            "相続登記義務化", "商業登記", "成年後見", "債務整理",
            "不動産登記", "会社設立", "家族信託", "登記オンライン",
        ],
        "search_hashtags": [
            "#司法書士", "#相続登記", "#相続登記義務化", "#不動産登記",
            "#商業登記", "#成年後見", "#家族信託", "#司法書士事務所",
        ],
    },
    {
        "name": "行政書士",
        "search_focus": "行政書士 許認可 最新",
        "pain_points": [
            "扱う業務の幅が広すぎて専門特化が難しい",
            "建設業許可・ビザ申請の制度変更追従",
            "他士業との連携で付加価値を上げたい",
            "ブランディング・差別化の難しさ",
            "事務所経営と継続的な集客",
        ],
        "hot_topics": [
            "建設業許可", "ビザ申請", "古物商許可", "外国人雇用",
            "補助金", "会社設立", "産業廃棄物許可",
        ],
        "search_hashtags": [
            "#行政書士", "#建設業許可", "#ビザ申請", "#許認可",
            "#古物商", "#行政書士事務所", "#外国人雇用", "#補助金申請",
        ],
    },
    {
        "name": "公認会計士",
        "search_focus": "公認会計士 監査 最新",
        "pain_points": [
            "監査法人を離れた後のキャリア構築",
            "上場準備・M&A支援案件の獲得",
            "サステナビリティ開示対応",
            "コンサル領域への展開と他士業との連携",
            "独立後の集客・ブランディング",
        ],
        "hot_topics": [
            "監査制度", "IFRS", "上場準備", "M&A",
            "内部統制", "サステナビリティ開示", "会計基準改正",
        ],
        "search_hashtags": [
            "#公認会計士", "#監査", "#会計士", "#IFRS",
            "#上場準備", "#M&A", "#内部統制", "#会計基準",
        ],
    },
    {
        "name": "弁理士",
        "search_focus": "弁理士 知財 特許 最新",
        "pain_points": [
            "AI関連特許の出願ノウハウ蓄積",
            "国際出願業務の競争激化",
            "中小企業の知財戦略支援への食い込み難しさ",
            "他士業との連携で経営戦略レベルの支援を",
            "事務所経営と人材確保",
        ],
        "hot_topics": [
            "特許出願", "商標登録", "意匠", "知財戦略",
            "AI関連特許", "知財訴訟", "国際出願",
        ],
        "search_hashtags": [
            "#弁理士", "#特許", "#商標", "#知財",
            "#知的財産", "#特許出願", "#商標登録", "#弁理士事務所",
        ],
    },
    {
        "name": "中小企業診断士",
        "search_focus": "中小企業診断士 経営 最新",
        "pain_points": [
            "補助金支援に偏った業務からの脱却",
            "顧問契約の獲得・継続",
            "他士業との連携で総合的な経営支援を",
            "DX・事業承継・事業再構築への対応力",
            "ブランディングと差別化",
        ],
        "hot_topics": [
            "事業計画", "補助金活用", "DX推進", "事業承継",
            "資金繰り", "マーケティング", "事業再構築", "経営改善",
        ],
        "search_hashtags": [
            "#中小企業診断士", "#経営コンサル", "#事業計画", "#補助金",
            "#事業承継", "#DX", "#経営改善", "#中小企業",
        ],
    },
]


# ============================================================
# 昼配信用: 士業業界全体向け(横断テーマ)
# ============================================================

INDUSTRY_WIDE_NOON = {
    "name": "士業業界全体",
    "search_focus": "士業 最新 トレンド",
    "theme_options": [
        # Claude が下記から1つピック(または独自に発想)
        "AI・LLM時代の士業の生存戦略",
        "士業のSNS活用・Web集客・ブランディングの最新事例",
        "士業×他士業のコラボ・連携で生まれている新しいビジネス",
        "若手士業の独立・開業ストーリー",
        "ベテラン士業が語る30年で変わったこと・変わらないこと",
        "士業の働き方改革・ワークライフバランス事例",
        "業界数値で見る士業の今(登録者数推移、報酬相場、平均年齢)",
        "異業種(エンタメ・落語・お笑い)から学ぶ士業の伝え方",
        "士業の事務所経営・人材育成・採用の最新トレンド",
        "ダブルライセンス・トリプルライセンスの戦略的価値",
        "海外士業との比較から見えるニッポンの士業の特異性",
        "士業の名言・偉人エピソードから学ぶ仕事観",
        "顧問先とのリレーションを深める意外なテクニック",
        "AI時代に高まる『対面・雑談・人柄』の価値",
    ],
    "search_hashtags": [
        "#士業", "#士業交流", "#士業連携", "#税理士", "#弁護士",
        "#社労士", "#司法書士", "#行政書士", "#公認会計士", "#弁理士",
        "#中小企業診断士", "#士業集客", "#士業マーケティング",
        "#事務所経営", "#らんたんLABO",
    ],
}


# ============================================================
# Slot determination
# ============================================================

def get_today_shigyo_and_slot():
    JST = timezone(timedelta(hours=9))
    now = datetime.now(JST)
    day_of_year = now.timetuple().tm_yday

    if SLOT in ("morning", "noon", "evening"):
        slot = SLOT
    else:
        # 時刻ベース判定: 5-10時=朝, 11-14時=昼, それ以外=夕
        h = now.hour
        if 5 <= h <= 10:
            slot = "morning"
        elif 11 <= h <= 14:
            slot = "noon"
        else:
            slot = "evening"

    # 朝・夕は士業を1業種ずつローテーション、昼は業界横断
    if slot == "noon":
        shigyo = INDUSTRY_WIDE_NOON
    else:
        shigyo = SHIGYO_LIST[(day_of_year - 1) % len(SHIGYO_LIST)]

    return shigyo, slot, now


# ============================================================
# Article generation via Claude
# ============================================================

def build_prompt(shigyo, slot, now):
    date_str = f"{now.year}年{now.month}月{now.day}日"

    # ----- 昼スロット: 業界横断・読み物トーン -----
    if slot == "noon":
        return _build_noon_prompt(shigyo, now, date_str)

    # ----- 朝/夕スロット: 1業種にフォーカス -----
    slot_label = "朝" if slot == "morning" else "夕方"

    if slot == "morning":
        source_guidance = """
【検索ソースの優先度】
1. 主要ニュースサイトを優先(日経新聞、東洋経済、Reuters、Yahoo!ニュース、NewsPicks、ITmedia、ZDNet、ダイヤモンドオンライン、PRESIDENT Online、業界専門メディア)
2. 見出しの引きが強い、話題性のあるニュースを優先
3. 補足として公的機関の情報も使ってOK"""
        tone_base = "朝の通勤時に読みたくなる、エネルギッシュで引きの強いトーン。"
    else:
        source_guidance = """
【検索ソースの優先度】
1. 公的機関を最優先(国税庁、財務省、厚生労働省、法務省、経済産業省、中小企業庁、日本銀行、金融庁、特許庁、最高裁判所、内閣府、総務省、Jグランツ)
2. 法改正・制度変更・新通達など、実務に直結する情報を優先
3. 公式発表のソースURLを必ず明記"""
        tone_base = "夕方の落ち着いた時間に読む、専門家としての知見を感じさせる解説トーン。"

    pain_str = "\n".join(f"  - {p}" for p in shigyo["pain_points"])
    topics_str = "、".join(shigyo["hot_topics"])
    hashtags_str = " ".join(shigyo["search_hashtags"])

    g1 = EVENT_INFO["guest_1"]
    g2 = EVENT_INFO["guest_2"]
    countdown_for_prompt = get_countdown_message(now) or "(イベント終了済み)"

    prompt = f"""本日({date_str} {slot_label})の{shigyo["name"]}向けSNS投稿セットを生成してください。

【投稿の最終目的】
すべての投稿は、らんたんLABO Opening Session(2026年6月19日)への参加申込みに繋げる集客投稿です。
news/最新ニュースは「問題提起のフック」として使い、本題はイベント集客に振ってください。

【ターゲット読者】
{shigyo["name"]}本人。検索ヒットさせて流入させ、参加申込みに繋げる。

【{shigyo["name"]}が抱えている悩み・問題】
{pain_str}

【関心トピック例】
{topics_str}

{source_guidance}

【全体トーン】
{tone_base}

【共通ストーリー構成(全プラットフォーム共通)】
1. 【フック】最新ニュースで{shigyo["name"]}の関心を引く
2. 【共感】「これ、ひとりで追うの限界では?」という孤独・限界感に寄り添う
3. 【提案】らんたんLABO Opening Session への招待
   - 異業種ゲスト2名から学べる(下記参照)
   - 他士業(8士業)との交流の場
   - "本気で遊び、本気で学ぶ"がコンセプト
4. 【CTA】具体的な日時・会場・参加費・申込URL

【申込URLの扱い】
申込URLは士業用と一般用の2種類があります。
- X(Twitter)用: 文字数制限のため、士業用URLのみを書くか、「リンクは画像に記載」などと書いて省略してOK
- Instagram用: 「プロフィールのリンクから」と書くか、または投稿内に両方のURLを明記してOK
- Facebook用: 投稿の最後に両方のURLを明記すること(士業の方/一般の方を分けて)
※ コードで自動的に投稿末尾に両方のURLを追加するため、本文中にURLを必須で書く必要はないが、文脈上自然な誘導文(「お申込みはこちら↓」など)を入れること

【らんたんLABO Opening Session 詳細】
- 日時: {EVENT_INFO["date"]}
- 会場: {EVENT_INFO["venue"]} ({EVENT_INFO["venue_address"]})
- スケジュール: {EVENT_INFO["schedule"]}
- テーマ: {EVENT_INFO["themes"]}
- 参加費: 士業 {EVENT_INFO["fee_shigyo"]} / 一般 {EVENT_INFO["fee_general"]}
- 主催: {EVENT_INFO["organizer"]} ({EVENT_INFO["leaders"]})
- 申込URL(士業): {APPLY_URL_SHIGYO}
- 申込URL(一般): {APPLY_URL_GENERAL}
- **本日時点でのイベントまでのカウントダウン**: {countdown_for_prompt}

【カウントダウンの活用】
本文の中にもカウントダウン情報を自然に織り込んでください。
- 31日以上前: "6/19のイベントまで「あと◯日」" のように軽く触れる
- 1ヶ月前くらい: "いよいよ来月!" "あと◯日でついに" など期待感を煽る
- 1週間前: "残り◯日!" "席埋まってきています!" など緊迫感を出す
- 数日前: "あと◯日!" "もう間に合わなくなる前に!" など強い緊迫感
- 当日・前日: "本日開催!" "いよいよ明日!" など最終呼びかけ

【ゲスト1: {g1["name"]}】
- 肩書: {g1["title"]}
- 経歴: {g1["bio"]}
- 講演の価値: {g1["value"]}

【ゲスト2: {g2["name"]}】
- 肩書: {g2["title"]}
- 経歴: {g2["bio"]}
- 講演の価値: {g2["value"]}

【コミュニティの提供価値】
{chr(10).join(f"  - {p}" for p in EVENT_INFO["community_pillars"])}

【作業手順】
1. まずWeb検索で最新ニュース(できれば過去1週間以内)を1つピックアップ
2. そのニュースを「{shigyo["name"]}の悩み・限界」と結びつける問題提起のフックとして使う
3. 「ひとりで全部追うのは無理。だから繋がる場が必要」という流れで Opening Session に誘導
4. 異業種(吉本興業出身の水谷氏・落語作家の今井氏)から学ぶ刺激と、他士業との交流の魅力を具体的に
5. 必ず実在する最新ニュースのみ使用(架空・古いニュースは厳禁)

【1. X(Twitter)用投稿】
- **全角140字以内** (ハッシュタグ・URL含めた全体)
- 1行目: 強い問題提起(数字・最新性・限界感)
- 2-3行目: 共感+解決策の暗示
- 4行目: 6/19のイベント名+申込誘導
- ハッシュタグ2-3個
- 末尾に申込URL

【2. Instagram用投稿(キャプション)】
- **800〜1,200字程度**
- 1行目に強烈なフック(絵文字使用OK・🚨📊⚠️📰など)
- 段落構成: 問題提起 → 共感(孤独感・限界感) → イベント紹介 → ゲスト紹介(2名) → 他士業交流の魅力 → CTA
- ゲスト2名の経歴・魅力を具体的に書く(吉本興業・落語作家など、目を引くキーワードを活かす)
- 「保存推奨」「シェアしてね」など Instagram文化に合う表現も
- 末尾に検索ヒット重視のハッシュタグ **15個程度**
- 「プロフィールのリンクから申込み✨」で誘導

【3. Facebook用投稿】
- **600〜900字程度**
- 専門家としての知見を感じさせる落ち着いた文体
- 絵文字は控えめ
- 段落構成: 問題提起→現状分析→なぜ繋がりが必要か→イベント詳細(ゲスト含む)→申込み
- 末尾にイベント詳細(日時・会場・参加費・申込URL)を明記
- ハッシュタグ5-8個

【4. 画像プロンプト(英語)】
記事内容に合った、本物の写真に見えるリアルな画像をPollinations.aiで生成するプロンプトを英語で作成。
**AIっぽさを徹底的に排除すること。** 以下のテクニックを必ず使用:
- **被写体は若手士業を中心に**: "young Japanese professional in late 20s to mid 30s",
   "young tax accountant / lawyer / consultant", "fresh-faced ambitious professional"
   (年齢を感じさせる表現は避け、「若手・新世代」感を強く打ち出す)
- カメラ・フィルム指定: "Shot on Fujifilm X100V, 35mm, Provia film stock, slight film grain"
   または "Canon AE-1, Kodak Portra 400, 50mm" など
- ドキュメンタリー調: "candid documentary photography", "photojournalism style"
- 日常感・生活感: "ordinary office details, modern minimal desk, laptop and notepad, coffee mug"
- 自然光: "natural diffused daylight" / "overcast window light" / "fluorescent office lighting"
   (× cinematic, × dramatic, × epic, × glowing は禁止ワード)
- 構図: "off-center composition", "asymmetric framing", "imperfect angle"
- 不完全さ: "natural skin texture", "slight motion blur", "subject unaware of camera"
- 服装: "modern business casual", "smart casual attire" (堅すぎないスーツ)
- 60〜90語以内、英語のみ
- シーン例: 若手税理士がノートPCで通達原文を読み込む / 若手弁護士が同僚と立ち話 /
   若手社労士がスマホで助成金情報をチェック など、「明るく前向きで挑戦している若手」を感じさせる構図

【出力形式】
以下のJSON形式のみで返答(前置き・後置き・コードブロック不要):

{{
  "news_title": "ピックアップしたニュースの見出し",
  "news_summary": "ニュース要点(150字程度)",
  "source_name": "出典サイト名",
  "source_url": "https://...",
  "news_date": "YYYY-MM-DD または 不明",
  "twitter": "X投稿本文(140字以内)",
  "instagram": "Instagram投稿本文",
  "facebook": "Facebook投稿本文",
  "image_prompt": "英語の画像生成プロンプト"
}}

参考ハッシュタグ: {hashtags_str} #らんたんLABO #士業
"""
    return prompt


def _build_noon_prompt(shigyo, now, date_str):
    """昼配信用: 業界横断・読み物トーン"""
    themes_str = "\n".join(f"  - {t}" for t in shigyo["theme_options"])
    hashtags_str = " ".join(shigyo["search_hashtags"])

    g1 = EVENT_INFO["guest_1"]
    g2 = EVENT_INFO["guest_2"]
    countdown_for_prompt = get_countdown_message(now) or "(イベント終了済み)"

    prompt = f"""本日({date_str} お昼)のランチタイム配信用 SNS投稿セットを生成してください。

【投稿の性質】
ランチタイム(12:00)に配信する、士業業界全体向けの「軽めの読み物」コンテンツです。
朝の速報・夕方の専門解説とは違い、お昼休みに気軽に読めて、ちょっと話題にしたく
なる読み物トーン。

【投稿の最終目的】
最終的には らんたんLABO Opening Session(2026年6月19日)への参加申込みに
繋げる集客投稿。ただし朝・夕より「ふわっと、読み物として面白く」を優先し、
イベント誘導はソフトに(押し売り感ゼロで)。

【ターゲット読者】
8士業すべての士業(税理士・弁護士・社労士・司法書士・行政書士・公認会計士・弁理士・
中小企業診断士)に共通する話題。「自分の士業と関係ない」と思われない普遍性を持たせる。

【テーマ選定】
以下から1つ選ぶか、Web検索結果を踏まえて独自のテーマを設定してOK。
今日の検索結果やトレンドに最も合うものを選んでください。
{themes_str}

【検索の方針】
1. 士業業界全体に関わる最新の話題・データ・トレンド・事例・名言・エピソードを探す
2. 業界紙・ビジネスメディア・専門家ブログ・SNSバズ記事・統計データ・本の引用
   など、ジャンル不問で「面白い読み物」になる素材を選ぶ
3. 必ず実在する情報のみ(架空の統計・架空の人物発言は厳禁)
4. 一次情報がベスト。引用元のURLを必ず明記

【トーン】
- ランチ片手にスマホで読む、軽い読み物
- 「へぇ〜」「ちょっと話したくなる」「保存したくなる」感じ
- 重い実務情報は避ける(朝・夕に任せる)
- 絵文字は中程度(🍱☕📊💡🤝など)
- 押し売り感ゼロで、最後にさりげなくイベント誘導

【共通ストーリー構成】
1. 【ランチタイムの掴み】「お疲れさまです」感のある軽いオープニング
2. 【今日の話題】選んだテーマを軽妙に紹介
3. 【士業全体への問いかけ】「あなたの事務所/業界ではどう?」と当事者意識を喚起
4. 【ソフト誘導】「こういう話、6/19のらんたんLABOで他の士業と話してみません?」
5. 【CTA】定型のイベント情報

【らんたんLABO Opening Session 詳細】
- 日時: {EVENT_INFO["date"]}
- 会場: {EVENT_INFO["venue"]} ({EVENT_INFO["venue_address"]})
- スケジュール: {EVENT_INFO["schedule"]}
- テーマ: {EVENT_INFO["themes"]}
- 参加費: 士業 {EVENT_INFO["fee_shigyo"]} / 一般 {EVENT_INFO["fee_general"]}
- 主催: {EVENT_INFO["organizer"]} ({EVENT_INFO["leaders"]})
- 申込URL(士業): {APPLY_URL_SHIGYO}
- 申込URL(一般): {APPLY_URL_GENERAL}
- **本日時点でのイベントまでのカウントダウン**: {countdown_for_prompt}

【カウントダウンの活用】
本文の中にもカウントダウン情報を自然に織り込んでください。
- 31日以上前: "6/19のイベントまで「あと◯日」" のように軽く触れる
- 1ヶ月前くらい: "いよいよ来月!" "あと◯日でついに" など期待感を煽る
- 1週間前: "残り◯日!" "席埋まってきています!" など緊迫感を出す
- 数日前: "あと◯日!" "もう間に合わなくなる前に!" など強い緊迫感
- 当日・前日: "本日開催!" "いよいよ明日!" など最終呼びかけ

【ゲスト1: {g1["name"]}】
- 肩書: {g1["title"]}
- 経歴: {g1["bio"]}
- 講演の価値: {g1["value"]}

【ゲスト2: {g2["name"]}】
- 肩書: {g2["title"]}
- 経歴: {g2["bio"]}
- 講演の価値: {g2["value"]}

【1. X(Twitter)用投稿】
- **全角140字以内**
- 1行目で目を引く軽い問いかけ・面白いデータ・名言など
- 軽妙でシェアしたくなるトーン
- ハッシュタグ2-3個
- 末尾に申込URL(またはイベント名のみで誘導)

【2. Instagram用投稿(キャプション)】
- **700〜1,000字程度** (朝・夕より少し短めでOK)
- 読み物として完結する満足感を重視
- ストーリー仕立て・データの可視化・引用などで飽きさせない構成
- 「保存推奨」「シェアしたい」と思わせる工夫
- 末尾にハッシュタグ12個程度
- イベント誘導は最後の2-3行でさりげなく

【3. Facebook用投稿】
- **500〜700字程度**
- ランチタイムに知的好奇心を刺激する読み物
- 個人的な体験談・観察・問いかけを織り交ぜた語り口
- 絵文字は1〜2個に抑制
- ハッシュタグ5-7個
- イベント誘導は文末で軽く

【4. 画像プロンプト(英語)】
ランチタイムらしい温かい画像。**AIっぽさを徹底排除**。以下のテクニックを必ず使用:
- **被写体は若手士業を中心に**: "young Japanese professional in late 20s to mid 30s",
   "young office worker on lunch break", "fresh-faced ambitious professional"
- カメラ・フィルム指定: "Shot on Fujifilm X100V, 35mm, Provia film stock, slight grain"
- ドキュメンタリー調: "candid lifestyle photography, snapshot moment"
- 生活感: "everyday Tokyo cafe, ordinary bento box, used coffee cup, slight imperfections"
- 自然光: "natural midday light" / "soft window light" (× cinematic, × dramatic は禁止)
- 構図: "off-center composition", "subject unaware", "casual angle"
- 服装: "modern business casual", "smart casual attire"
- 不完全さ: "natural texture, ordinary moment, no perfect lighting"
- 60〜90語以内、英語のみ
- シーン例: 若手士業がランチ中にスマホをチラ見 / カフェで弁当を開ける若手 /
   ランチ中に同僚と笑顔で話す若手など

【出力形式】
以下のJSON形式のみで返答(前置き・後置き・コードブロック不要):

{{
  "news_title": "選んだテーマ・話題の見出し",
  "news_summary": "話題の要点(150字程度)",
  "source_name": "出典サイト名",
  "source_url": "https://...",
  "news_date": "YYYY-MM-DD または 不明",
  "twitter": "X投稿本文(140字以内)",
  "instagram": "Instagram投稿本文",
  "facebook": "Facebook投稿本文",
  "image_prompt": "英語の画像生成プロンプト"
}}

参考ハッシュタグ: {hashtags_str}
"""
    return prompt



def call_claude(shigyo, slot, now):
    if not ANTHROPIC_API_KEY:
        raise RuntimeError("ANTHROPIC_API_KEY is not set")

    system_prompt = f"""あなたは士業限定コミュニティ「らんたんLABO」の広報ライターです。
"本気で遊び、本気で学ぶ"をモットーに、暗くなりがちな士業業界を温かく照らし、
士業同士の連携を強め、AI時代の対面コミュニケーションを大切にするコミュニティです。
代表: 庄司絢子 / 副代表: 今井亮輔(税理士)

毎日3回(朝8時/昼12時/夕方17時)、SNSにOpening Session(2026/6/19)への参加申込みに
繋げる投稿を発信します。
- 朝/夕は{shigyo["name"]}向けに最新ニュースを問題提起のフックとした集客投稿
- 昼は士業業界全体向けの軽い読み物コンテンツ

最終的には「他士業と交流したい」「異業種ゲストの講演を聞きたい」と思わせる
投稿を作成してください。"""

    user_prompt = build_prompt(shigyo, slot, now)

    payload = {
        "model": "claude-sonnet-4-5",
        "max_tokens": 6000,
        "system": system_prompt,
        "messages": [{"role": "user", "content": user_prompt}],
        "tools": [
            {"type": "web_search_20250305", "name": "web_search", "max_uses": 5}
        ],
    }
    headers = {
        "x-api-key": ANTHROPIC_API_KEY,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
    }

    print(f"[INFO] Calling Claude API for {shigyo['name']} ({slot})...")
    r = requests.post(
        "https://api.anthropic.com/v1/messages",
        headers=headers, json=payload, timeout=180,
    )
    if r.status_code != 200:
        raise RuntimeError(f"Anthropic API error {r.status_code}: {r.text[:500]}")

    data = r.json()
    text_blocks = [b["text"] for b in data["content"] if b.get("type") == "text"]
    full_text = "\n".join(text_blocks)

    cleaned = full_text.replace("```json", "").replace("```", "").strip()
    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start == -1 or end == -1:
        raise RuntimeError(f"No JSON found in response: {full_text[:500]}")

    return json.loads(cleaned[start : end + 1])


# ============================================================
# Image generation via Pollinations.ai
# ============================================================

def build_image_url(prompt, seed=None):
    encoded = urllib.parse.quote(prompt)
    seed = seed or int(datetime.now().timestamp())
    return (
        f"https://image.pollinations.ai/prompt/{encoded}"
        f"?width=1024&height=1024&seed={seed}&nologo=true&model=flux&enhance=true"
    )


# ============================================================
# Compose LINE messages — separate text per platform
# ============================================================

def compose_messages(article, shigyo, slot, image_url, now=None):
    """Returns a list of LINE message objects (image + 4 text blocks)."""
    if now is None:
        now = datetime.now(timezone(timedelta(hours=9)))
    if slot == "morning":
        slot_emoji = "☀️"
        slot_label = f"今朝の{shigyo['name']}向け"
    elif slot == "noon":
        slot_emoji = "🍱"
        slot_label = "ランチタイムの士業読み物"
    else:
        slot_emoji = "🌙"
        slot_label = f"今夕の{shigyo['name']}向け"

    twitter_text = article.get("twitter", "").strip()
    instagram_text = article.get("instagram", "").strip()
    facebook_text = article.get("facebook", "").strip()
    source_name = article.get("source_name", "").strip()
    source_url = article.get("source_url", "").strip()
    news_title = article.get("news_title", "").strip()

    countdown = get_countdown_message(now)
    countdown_line = f"\n{countdown}\n" if countdown else ""

    event_block = f"""【らんたんLABO Opening Session】
🏮 {EVENT_INFO["tagline"]}{countdown_line}
📅 {EVENT_INFO["date"]}
📍 {EVENT_INFO["venue"]}
🎤 ゲスト:
   ・{EVENT_INFO["guest_1"]["name"]} ({EVENT_INFO["guest_1"]["title"]})
   ・{EVENT_INFO["guest_2"]["name"]} (落語作家)
🎯 テーマ: {EVENT_INFO["themes"]}
💴 士業 {EVENT_INFO["fee_shigyo"]} / 一般 {EVENT_INFO["fee_general"]}

👇 お申込みはこちら
{APPLY_URLS_BLOCK}"""

    # ----- Twitter (header情報を冒頭に統合してメッセージ数を節約) -----
    if FLYER_IMAGE_URL:
        # チラシも添付するため、headerメッセージを省略しX冒頭に統合
        twitter_msg = f"""{slot_emoji} {slot_label} SNS投稿セット
━━━━━━━━━━━━━━━
📰 {news_title}
📎 出典: {source_name}
{source_url}
━━━━━━━━━━━━━━━

𝕏  X(Twitter)用 ({len(twitter_text)}字)
※ AI画像 + チラシの2枚を添付推奨

{twitter_text}"""
    else:
        twitter_msg = f"""━━━━━━━━━━━━━━━
𝕏  X(Twitter)用 ({len(twitter_text)}字)
━━━━━━━━━━━━━━━

{twitter_text}"""

    # ----- Instagram -----
    instagram_msg = f"""━━━━━━━━━━━━━━━
📷 Instagram用 ({len(instagram_text)}字)
━━━━━━━━━━━━━━━

{instagram_text}

━━━━━━━━
{event_block}"""

    # ----- Facebook -----
    facebook_msg = f"""━━━━━━━━━━━━━━━
📘 Facebook用 ({len(facebook_text)}字)
━━━━━━━━━━━━━━━

{facebook_text}

━━━━━━━━
{event_block}"""

    def trim(text):
        return text if len(text) <= 4900 else text[:4850] + "...(以下省略)"

    # ----- メッセージ構成 -----
    if FLYER_IMAGE_URL:
        # 2画像 + 3テキスト = 5メッセージ
        messages = [
            {
                "type": "image",
                "originalContentUrl": image_url,
                "previewImageUrl": image_url,
            },
            {
                "type": "image",
                "originalContentUrl": FLYER_IMAGE_URL,
                "previewImageUrl": FLYER_IMAGE_URL,
            },
            {"type": "text", "text": trim(twitter_msg)},
            {"type": "text", "text": trim(instagram_msg)},
            {"type": "text", "text": trim(facebook_msg)},
        ]
    else:
        # 1画像 + 4テキスト = 5メッセージ
        header = f"""{slot_emoji} {slot_label} SNS投稿セット
━━━━━━━━━━━━━━━

📰 フックに使うニュース・話題
{news_title}

📎 出典: {source_name}
{source_url}

━━━━━━━━━━━━━━━
このあと X / Instagram / Facebook 用の
投稿が順に届きます👇"""
        messages = [
            {
                "type": "image",
                "originalContentUrl": image_url,
                "previewImageUrl": image_url,
            },
            {"type": "text", "text": trim(header)},
            {"type": "text", "text": trim(twitter_msg)},
            {"type": "text", "text": trim(instagram_msg)},
            {"type": "text", "text": trim(facebook_msg)},
        ]
    return messages


# ============================================================
# LINE Messaging API
# ============================================================

def send_to_line(messages):
    if not LINE_CHANNEL_ACCESS_TOKEN or not LINE_TARGET_ID:
        raise RuntimeError("LINE credentials not configured")

    headers = {
        "Authorization": f"Bearer {LINE_CHANNEL_ACCESS_TOKEN}",
        "Content-Type": "application/json",
    }
    payload = {"to": LINE_TARGET_ID, "messages": messages[:5]}

    print(f"[INFO] Pushing {len(payload['messages'])} messages to LINE...")
    r = requests.post(
        "https://api.line.me/v2/bot/message/push",
        headers=headers, json=payload, timeout=30,
    )
    if r.status_code != 200:
        raise RuntimeError(f"LINE API error {r.status_code}: {r.text[:500]}")
    print("[OK] Sent to LINE")


# ============================================================
# Main
# ============================================================

def main():
    shigyo, slot, now = get_today_shigyo_and_slot()
    print(f"[INFO] Date: {now.isoformat()}")
    print(f"[INFO] Shigyo: {shigyo['name']}")
    print(f"[INFO] Slot:   {slot}")

    article = call_claude(shigyo, slot, now)
    print(f"[INFO] News: {article.get('news_title')}")
    print(f"[INFO] Source: {article.get('source_name')} - {article.get('source_url')}")
    print(f"[INFO] Twitter: {len(article.get('twitter',''))}chars")
    print(f"[INFO] Instagram: {len(article.get('instagram',''))}chars")
    print(f"[INFO] Facebook: {len(article.get('facebook',''))}chars")

    image_url = build_image_url(article["image_prompt"])
    print(f"[INFO] Image URL: {image_url}")

    messages = compose_messages(article, shigyo, slot, image_url, now)

    print("\n========== Composed Messages ==========")
    for i, msg in enumerate(messages, 1):
        print(f"\n--- Message {i} ({msg['type']}) ---")
        if msg["type"] == "text":
            print(msg["text"])
        else:
            print(f"[image] {msg.get('originalContentUrl')}")
    print("\n========== End ==========\n")

    if DRY_RUN:
        print("[DRY_RUN] Skipping LINE send")
        return

    send_to_line(messages)
    print("[DONE]")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"[ERROR] {e}", file=sys.stderr)
        sys.exit(1)
