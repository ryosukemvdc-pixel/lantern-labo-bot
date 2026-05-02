# 🏮 5分でセットアップ クイックガイド

エンジニアでない方向けの最短手順です。

## 必要なもの (事前準備)

- [ ] GitHub アカウント (無料): <https://github.com/signup>
- [ ] Anthropic アカウント (有料・少額): <https://console.anthropic.com/>
- [ ] LINE Developers アカウント (無料): <https://developers.line.biz/>

## ステップ 1: リポジトリをフォーク

このプロジェクトをご自身のGitHubアカウントにフォーク (右上の Fork ボタン)。

## ステップ 2: 3つの「鍵」を準備

### 🔑 鍵 1: Anthropic APIキー

1. <https://console.anthropic.com/> にログイン
2. 左メニュー「API Keys」→ 「Create Key」
3. 出てきた `sk-ant-...` をコピー(画面を閉じると見られなくなるので注意)
4. 「Plans & Billing」で **クレジットを $5 ほどチャージ**

> 💰 1日2回配信 × 30日 ＝ 60回。1回あたり数十円程度。$5で2〜3ヶ月持ちます。

### 🔑 鍵 2: LINE チャネルアクセストークン

1. <https://developers.line.biz/console/> にログイン
2. 「新規プロバイダー作成」(自分の名前や事業名でOK)
3. プロバイダー内で「**Messaging API**」のチャネルを作成
   - チャネル名: 「らんたんLABO ニュース」
   - チャネル説明: 「士業向け最新ニュース配信」
   - 大業種・小業種: 任意 (個人/メディア など)
4. 作成後、**「Messaging API設定」タブ** へ
5. 一番下の「**チャネルアクセストークン(長期)**」の **「発行」** をクリック
6. 出てきた長い文字列をコピー → これが `LINE_CHANNEL_ACCESS_TOKEN`

### 🔑 鍵 3: LINE 配信先ID

1. 同じ「Messaging API設定」画面の **QRコード** を、自分のスマホLINEで読み取り
2. **Bot を友だち追加**
3. 同画面で「**応答メッセージ**」「**あいさつメッセージ**」を **オフ** に
4. 「**Webhook**」を**オフ** で OK
5. 自分のユーザーID取得は2通り:
   - 簡単な方法: ターミナル(Mac)/コマンドプロンプト(Win)で:
     ```
     curl -H "Authorization: Bearer ここに鍵2のトークン" https://api.line.me/v2/bot/followers/ids
     ```
     → 返ってきた `U` で始まる文字列がご自身のユーザーID
   - グループ配信したい場合: グループにBotを招待 → グループ内で発言 →
     LINE Developers 画面のログで `groupId` を確認 (`C` で始まる)

## ステップ 3: GitHub Secrets に登録

フォークしたリポジトリで:

1. **Settings** タブ
2. 左メニュー **Secrets and variables → Actions**
3. **New repository secret** ボタンで以下を1つずつ追加:

| Name | Secret (値) |
|---|---|
| `ANTHROPIC_API_KEY` | 鍵1 |
| `LINE_CHANNEL_ACCESS_TOKEN` | 鍵2 |
| `LINE_TARGET_ID` | 鍵3 |
| `APPLY_URL` | 応募フォームのURL |
| `EVENT_DETAILS` | イベント詳細(改行OK) |

## ステップ 4: Actions を有効化 + テスト送信

1. **Actions** タブ → 「I understand...」をクリックして有効化
2. 左メニューに「Lantern LABO Daily Post」が出る
3. 「**Run workflow**」ボタン:
   - `slot`: `morning` または `evening`
   - `dry_run`: **最初は `true`** で送信せずプレビュー
4. 数分後、緑のチェックマークが出たら成功
5. ジョブをクリック → ログを開いて、生成された記事内容を確認
6. 問題なければ `dry_run: false` で再実行 → LINE が届くはず!

## ステップ 5: 自動配信スタート

ステップ4で成功すれば、もう完了です。
明日の朝8時から自動的に配信が始まります。

---

## よくある質問

**Q. LINE が届きません**
- Bot を友だち追加していますか?
- `LINE_TARGET_ID` の先頭が `U` (ユーザー) または `C` (グループ) ですか?
- `LINE_CHANNEL_ACCESS_TOKEN` のコピーミスはないですか?

**Q. 「8時ちょうどに届かない」**
- GitHub Actions の cron は 5〜15分の遅延があります(無料プランの仕様)。
- どうしても厳密にしたい場合は別途有料サービス(Cloud Scheduler等)が必要。

**Q. 内容を事前にチェックしてから配信したい**
- `daily_post.yml` を編集して、自動cron をコメントアウト → `workflow_dispatch` のみに。
- 毎朝・夕方に手動で「Run workflow」を実行する運用に。

**Q. 画像生成を別のサービスにしたい**
- `post_to_line.py` の `build_image_url()` 関数を差し替えれば OK。
- 例: Stability AI、DALL-E、Midjourney(有料/手動)など。

**Q. 配信先を増やしたい**
- LINEグループを作成 → Botを招待 → グループID取得 → `LINE_TARGET_ID` をグループIDに変更。

---

困ったらこのリポジトリを Claude に見せて相談してください。
