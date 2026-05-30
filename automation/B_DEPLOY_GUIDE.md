# Plan B デプロイ手順 — サーバーサイド pull 投稿（XServer Cron 方式）

## これは何か / なぜやるか

現在 lightlog の自動投稿は **GitHub Actions → REST API → WordPress** で動いている。
これは「エックスサーバーの国外IPアクセス制限を OFF にした」ことで通っている。

Plan B は投稿の「最後の一歩」だけをサーバー側に移す方式：

```
GitHub Actions（記事生成のみ）
  └─ articles/latest.json を main にコミット
        ▼（GitHubに置くだけ。WordPressには触らない）
XServer Cron（毎朝・日本IP）
  └─ server_pull_post.php が latest.json を取得し WordPress に直接投稿
        ・REST も XML-RPC も HTTP も使わない（wp-load.php 直叩き）
        ・国外IP制限・WAF の影響をゼロにできる
```

### Plan B の利点
- **国外IPアクセス制限を ON に戻せる**（REST/XML-RPC を再び塞いでセキュリティを回復）。
- **WAF(XSS対策) を気にしなくてよい**（記事内の `<script>` JSON-LD で 403 になる心配がない）。
- **重複投稿が構造的に起きない**（後述の三重ガード）。

### 旧プラグインの「1日9回投稿」を再発させない仕組み
旧方式の事故原因は「WP-Cron が訪問のたびに発火 × 重複チェック無し」だった。本スクリプトは：
1. **本物の Cron で1日1回だけ実行**（訪問トリガーではない）
2. **状態ファイル** `last_posted.json` に最後の投稿タイトルを記録し、一致ならスキップ
3. **WordPress 上の同タイトル公開記事**があればスキップ
4. **flock 多重起動ロック**で Cron 重複起動でも二重投稿しない

---

## 前提

- 対象サイト: glowlog.net（XServer スタンダードプラン、PHP 8.3）
- 必要なもの: XServer サーバーパネルへのログイン、ファイルマネージャ or FTP

---

## ステップ 1：パスを確認する

XServer の「ファイルマネージャ」または SSH で、以下2つの絶対パスを確認する。

1. **wp-load.php のパス**（例）
   `/home/xs752098/glowlog.net/public_html/wp-load.php`
   ※ `xs752098` はサーバーID、`public_html` 配下に WordPress がある前提。実際の構成に合わせる。

2. **スクリプト設置ディレクトリ**（Web から見えない場所が望ましい）
   例: `/home/xs752098/glowlog.net/lumen/`（public_html の外に新規作成）

---

## ステップ 2：スクリプトを設置・設定

1. `automation/server_pull_post.php` を上記ディレクトリ（例 `.../glowlog.net/lumen/`）にアップロード。
2. ファイル先頭の設定を環境に合わせて編集（環境変数 `LUMEN_WP_LOAD` 等でも上書き可）：
   - `$WP_LOAD` … ステップ1で確認した wp-load.php の絶対パス
   - `$LATEST_URL` … 既定のままで可（main の raw URL）
   - `$DEFAULT_AUTHOR_ID` … 投稿者ユーザーID（通常 1）

---

## ステップ 3：DRY RUN でテスト（投稿せず判定だけ）

SSH が使えるなら：

```bash
LUMEN_DRY_RUN=1 php /home/xs752098/glowlog.net/lumen/server_pull_post.php
```

- 「DRY_RUN: 新規投稿対象として検出」と出れば取得・解析・重複判定まで OK。
- 「重複（…）のためスキップ」と出る場合は、その記事が既にサイトにある状態（正常）。

SSH が無い場合は XServer の「Cron設定」で一度だけ DRY_RUN コマンドを登録して実行ログを確認。

---

## ステップ 4：本番投稿を1回テスト

`articles/latest.json` が「まだサイトに無い記事」の状態で：

```bash
php /home/xs752098/glowlog.net/lumen/server_pull_post.php
```

- `pull_post.log` に「投稿成功 ID=xxx」が出て、サイトに記事が1本増えれば成功。

> ⚠️ 現在は GitHub Actions の REST 投稿も生きている。両方動くと同じ記事を投稿しうるが、
> 三重ガード（特に「同タイトル既存ならスキップ」）で二重投稿は防がれる。
> とはいえクリーンにするため、B が成功したらステップ6で REST 側を止める。

---

## ステップ 5：XServer Cron に登録

サーバーパネル → **Cron設定** → 新規追加：

- 実行時刻: **毎日 08:30**（GitHub Actions の生成 08:00 JST より後にする。30分の余裕）
- コマンド:
  ```
  php /home/xs752098/glowlog.net/lumen/server_pull_post.php >> /home/xs752098/glowlog.net/lumen/cron.log 2>&1
  ```

> GitHub Actions（記事生成）は 23:00 UTC = 08:00 JST。B はその後の 08:30 JST に回す。

---

## ステップ 6：切替の仕上げ（B が安定したら）

1. **国外IPアクセス制限を ON に戻す**
   サーバーパネル → WordPressセキュリティ設定 → glowlog.net →
   国外IPアクセス制限設定 → **REST API / XML-RPC を ON**（セキュリティ回復）。
   ※ B はこれを ON に戻しても影響を受けない。

2. **GitHub Actions の REST 投稿ステップを止める**（二重投稿の芽を断つ）
   `.github/workflows/affiliate_auto_post.yml` の
   `- name: Post to WordPress` ステップを削除またはコメントアウト。
   → 記事生成＋ latest.json コミットだけ Actions が行い、投稿は B（サーバー Cron）が担う。

---

## ロールバック（B をやめて REST に戻す場合）

1. XServer の国外IPアクセス制限（REST/XML-RPC）を **OFF** に戻す。
2. ワークフローの `Post to WordPress` ステップを復活させる。
3. XServer Cron を停止。

REST 経路のコードはそのまま残してあるため、いつでも往復できる。

---

## 補足：生成パイプラインは変更不要

本 PR では `articles/latest.json` の形式や記事生成側（`run_affiliate.py` 等）は一切変えていない。
`server_pull_post.php` は既存の latest.json をそのまま読むだけなので、**完全に追加（additive）** で、
現行の REST 投稿フローを壊さない。B はデプロイして初めて有効になる。
