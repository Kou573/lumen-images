# Automation — セットアップガイド

## システム概要

| ワークフロー | 実行タイミング | 動作内容 |
|---|---|---|
| `affiliate_auto_post.yml` | 毎日 JST 10:00 | Claude Haiku でSaaS比較記事を生成 → WordPress に自動投稿 |
| `note_draft_generator.yml` | 毎週月曜 JST 9:00 | Claude Haiku でnote記事ドラフトを生成 → `note_drafts/` に保存 |

---

## 1. GitHub Secrets の設定

GitHubリポジトリの **Settings → Secrets and variables → Actions → New repository secret** から以下の4つを登録してください。

| Secret名 | 説明 | 例 |
|---|---|---|
| `ANTHROPIC_API_KEY` | Anthropic APIキー | `sk-ant-api03-...` |
| `WP_URL` | WordPressサイトのURL | `https://yoursite.com` |
| `WP_USERNAME` | WordPressのログインユーザー名 | `admin` |
| `WP_APP_PASSWORD` | WordPressアプリケーションパスワード（後述） | `xxxx xxxx xxxx xxxx xxxx xxxx` |

> **note下書き生成のみ使う場合**は `ANTHROPIC_API_KEY` だけ設定すれば動作します。

---

## 2. WordPress アプリケーションパスワードの取得

通常のログインパスワードとは別の「アプリケーションパスワード」が必要です。

1. WordPress管理画面にログインし **ユーザー → プロフィール** を開く
2. ページ下部の「**アプリケーションパスワード**」セクションで名前（例: `GitHub Actions`）を入力し「**新しいアプリケーションパスワードを追加**」をクリック
3. 表示された **24文字のパスワード**（スペース区切り）を `WP_APP_PASSWORD` としてコピーして保存する

> パスワードは一度しか表示されません。必ず即座にコピーしてください。

---

## 3. 動作確認（手動実行）

1. GitHub リポジトリの **Actions** タブを開く
2. 左サイドバーから実行したいワークフロー名をクリック
   - `Affiliate Site Auto Post`
   - `Note Draft Generator`
3. 右上の **「Run workflow」** ボタンをクリック → **「Run workflow」** を選択
4. ワークフローが緑色のチェックマークで完了すれば成功

---

## 4. ローカル実行

```bash
cd /path/to/repo

# 依存パッケージのインストール
pip install -r automation/requirements.txt

# .env ファイルを作成（.gitignore に追加推奨）
cp .env.example .env  # または手動で作成

# アフィリエイト記事を生成・投稿
python automation/run_affiliate.py

# note記事ドラフトを生成
python automation/run_note.py
```

`.env` ファイルの形式:

```env
ANTHROPIC_API_KEY=sk-ant-api03-...
WP_URL=https://yoursite.com
WP_USERNAME=admin
WP_APP_PASSWORD=xxxx xxxx xxxx xxxx xxxx xxxx
```

---

## 5. トピックの追加・編集

- **SaaS比較記事**: `automation/topics/saas_topics.json` を編集
- **note記事ドラフト**: `automation/topics/note_topics.json` を編集

`"posted": false` のトピックが順番に処理されます。追加する際は `id` が重複しないようにしてください。

---

## 6. 生成物の確認

- **WordPress記事**: 投稿後にWordPress管理画面の「投稿一覧」で確認
- **note下書き**: `automation/note_drafts/YYYYMMDD_タイトル.md` に保存されます
  - ファイルを開いて内容を note.com のエディタに貼り付け → 公開ボタンを押すだけです

---

## 7. GA4クリック計測 + 収益推定レポートのセットアップ

### 概要
記事内のツールリンクのクリック数をGA4で計測し、毎月1日に推定収益レポートを自動生成します。
収益化（アフィリエイトリンク有効化）のタイミングを数値で判断できます。

### 必要なもの
- Google アカウント（無料）
- Google Cloud プロジェクト（無料枠で足ります）

### セットアップ手順

#### Step 1: Google Analytics 4 プロパティ作成
1. analytics.google.com にアクセス
2. 「プロパティを作成」→ サイト名・URLを入力
3. 「プロパティID」（例: `123456789`）をメモ

#### Step 2: WordPressにGA4を設置
1. WordPress管理画面 → プラグイン → 「Site Kit by Google」をインストール・有効化
2. Googleアカウントで連携 → GA4プロパティを選択
3. これでサイトのGA4計測が開始されます

#### Step 3: Google Cloud サービスアカウント作成
1. console.cloud.google.com にアクセス
2. 新規プロジェクト作成（名前は何でもOK）
3. 「APIとサービス」→「ライブラリ」→「Google Analytics Data API」を有効化
4. 「APIとサービス」→「認証情報」→「サービスアカウントを作成」
5. サービスアカウントのメールアドレスをコピー（例: `xxx@yyy.iam.gserviceaccount.com`）
6. 「キー」タブ → 「鍵を追加」→「JSON」→ ダウンロード

#### Step 4: GA4にサービスアカウントを追加
1. analytics.google.com → 管理 → 「プロパティのアクセス管理」
2. 「＋」→ Step 3のサービスアカウントのメールアドレスを追加（権限: 閲覧者）

#### Step 5: GitHub Secretsに2つ追加
| Secret名 | 値 |
|---|---|
| `GA4_PROPERTY_ID` | Step 1でメモしたプロパティID（数字のみ） |
| `GA4_SERVICE_ACCOUNT_JSON` | Step 3でダウンロードしたJSONファイルの内容をbase64エンコードした文字列 |

base64エンコードの方法（ターミナル）:
```bash
base64 -i your-service-account.json | tr -d '\n'
```

### レポートの確認
毎月1日に `output/revenue_reports/YYYYMM_estimate.md` が自動生成されます。
推定収益が20万円を超えると「🟢 収益化タイミングです」と表示されます。
