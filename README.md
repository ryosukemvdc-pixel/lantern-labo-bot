# 🏮 らんたんLABO 士業向けLINE自動配信ボット

毎日2回、8つの士業をローテーションしながら、最新ニュースをLINEに自動配信するシステムです。

```
朝8時 (JST)  → 一般ニュースサイト中心
夕方17時(JST) → 公的機関中心
```

## 配信ローテーション

| 曜日（年初からの日数 mod 8） | 士業 |
|---|---|
| 1日目 | 税理士 |
| 2日目 | 弁護士 |
| 3日目 | 社労士 |
| 4日目 | 司法書士 |
| 5日目 | 行政書士 |
| 6日目 | 公認会計士 |
| 7日目 | 弁理士 |
| 8日目 | 中小企業診断士 |

8日サイクルで永久に回ります。

## 配信内容

各メッセージには以下が含まれます:

1. **AI生成画像** (Pollinations.ai で記事に合った画像を自動生成)
2. **記事本文**
   - 強い見出し (30字以内)
   - 本文 350〜500字
   - 検索ヒットを狙ったハッシュタグ 10〜15個
   - 出典名 + ソースURL
3. **らんたんLABO案内** (イベント詳細 + 応募URL)

---

## セットアップ手順

### 1. このリポジトリを自分のGitHubアカウントにフォーク

GitHub にログインした状態で、画面右上の「Fork」をクリック。

### 2. 必要なAPIキー・トークンを取得

#### A. Anthropic APIキー
1. <https://console.anthropic.com/> にアクセス
2. アカウント作成 → 「API Keys」から発行
3. クレジットを少額チャージ (毎日2回の配信なら月数百円程度)

#### B. LINE Messaging API
1. <https://developers.line.biz/console/> にアクセスしLINEアカウントでログイン
2. 「Create a new provider」(新規プロバイダー作成)
3. 「Create a Messaging API channel」(チャネル作成)
   - チャネル名: `らんたんLABO Bot` など
   - その他必要事項を入力
4. 作成後、「Messaging API設定」タブから:
   - **チャネルアクセストークン** を発行 → `LINE_CHANNEL_ACCESS_TOKEN`
5. 同じ画面の QRコードを LINE で読み取り、Botを **友だち追加**
6. **自分のLINEユーザーID取得**:
   - 「Messaging API設定」→ 「Webhook URL」を一時的にどこかに設定
   - もしくは下記の方法でユーザーIDを取得:
     ```bash
     # Botに何かメッセージを送った後、↓ で確認
     curl -H "Authorization: Bearer YOUR_CHANNEL_ACCESS_TOKEN" \
          https://api.line.me/v2/bot/followers/ids
     ```
   - 取得した `Uxxxxxxxxxxxx` 形式のIDを `LINE_TARGET_ID` に設定
   - **複数人に送りたい場合**は LINEグループを作って Botを招待し、
     グループID(`Cxxxxxxx`)を取得する方法もあり

### 3. GitHub Secrets を設定

フォークしたリポジトリで:
**Settings → Secrets and variables → Actions → New repository secret** から以下を登録:

| Secret名 | 値 |
|---|---|
| `ANTHROPIC_API_KEY` | Anthropic APIキー |
| `LINE_CHANNEL_ACCESS_TOKEN` | LINEチャネルアクセストークン |
| `LINE_TARGET_ID` | 配信先のLINEユーザーID or グループID |
| `APPLY_URL` | 応募フォームのURL (例: `https://forms.gle/xxxxx`) |
| `EVENT_DETAILS` | イベント詳細(任意・複数行可) |

`EVENT_DETAILS` の例:
```
📅 2026年6月19日(金) 18:00
📍 ロイヤルパークホテル日本橋
💴 士業15,000円 / 一般20,000円
```

### 4. GitHub Actions を有効化

フォーク直後は Actions が無効です。
**Actions タブ** をクリックし、「I understand my workflows, go ahead and enable them」を選択。

### 5. 動作確認 (手動実行)

**Actions タブ → "Lantern LABO Daily Post" → "Run workflow"** をクリック:

- `slot`: `morning` か `evening` を選択
- `dry_run`: `true` にすると LINE送信なしでログだけ確認

`dry_run=true` で実行 → ログにメッセージ内容が出力される → 内容を確認 → 問題なければ `false` で本番実行。

### 6. 自動配信開始

GitHub Secrets を全て設定し、Actions が enabled になっていれば、自動的に毎日:

- **朝8:00 JST** (UTC 23:00)
- **夕方17:00 JST** (UTC 08:00)

に配信が走ります。

> ⚠️ **GitHub Actions の cron は数分〜十数分の遅延があります**。
> 厳密に 8:00:00 ちょうどには動きません。

---

## カスタマイズ

### 配信時間を変える

`.github/workflows/daily_post.yml` の `cron` を編集:

```yaml
on:
  schedule:
    - cron: "0 22 * * *"  # 朝7時 JST に変更 (UTC 22:00)
    - cron: "0 9 * * *"   # 夕方18時 JST に変更 (UTC 09:00)
```

### 士業のローテーション順や内容を変える

`post_to_line.py` 上部の `SHIGYO_LIST` を編集。
各士業に以下を設定可能:

- `name`: 表示名
- `search_focus`: Web検索のフォーカスワード
- `hot_topics`: 関心トピック (記事生成のヒントとして使用)
- `search_hashtags`: 参考ハッシュタグ

### 配信文面のフォーマットを変える

`post_to_line.py` の `compose_message()` 関数を編集。

---

## トラブルシューティング

### LINE が届かない
- Botを友だち追加していますか?
- `LINE_TARGET_ID` は `U` で始まる18文字 (ユーザー) または `C` で始まる(グループ)?
- LINE Messaging API の **無料プラン** は月1,000通までです (1日2通なら問題なし)

### Actions が動かない
- フォーク直後は Actions タブから手動有効化が必要
- Settings → Actions → General → Workflow permissions が `Read and write permissions` になっているか確認

### 記事内容が古い・検索が浅い
- `post_to_line.py` の `web_search` の `max_uses` を増やす(デフォルト5)
- ただし API使用料が増えます

### 画像が表示されない
- Pollinations.ai は無料サービスのため、稀にダウンします
- 別の画像生成サービスを使う場合は `build_image_url()` を差し替え

---

## ローカルでテスト

```bash
# 環境変数を設定
export ANTHROPIC_API_KEY=sk-...
export LINE_CHANNEL_ACCESS_TOKEN=xxxxx
export LINE_TARGET_ID=Uxxxxx
export APPLY_URL=https://...
export EVENT_DETAILS="📅 2026年6月19日..."
export SLOT=morning
export DRY_RUN=true   # 送信せずプレビューだけ

# 実行
pip install -r requirements.txt
python post_to_line.py
```

`DRY_RUN=false` にすれば実際にLINEに届きます。

---

## ライセンス・注意事項

- 生成される記事は AI による要約・解釈です。法的アドバイスを保証するものではありません
- 必ず公開前に内容を目視チェックする運用を推奨します(`DRY_RUN=true` で確認 → 手動転送、など)
- LINE Messaging API、Anthropic API の利用規約を遵守してください

---

🏮 **らんたんLABO** — 本気で遊び、本気で学ぶ
