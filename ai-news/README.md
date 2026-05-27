# aiNEWS部門 — Slack配信ルール

毎朝8:05 JST に `#ai-news` チャンネルへ自動投稿する。

---

## コンテンツ優先順位

| 優先度 | 内容 |
|---|---|
| ★★★ | 大手LLMの新モデルリリース・バージョンアップ（OpenAI / Anthropic / Google / DeepMind / Meta） |
| ★★☆ | API仕様変更・料金改定・廃止予告 |
| ★★☆ | 障害・インシデント情報 |
| ★☆☆ | 大型資金調達・買収・提携 |
| ★☆☆ | その他の業界動向 |

---

## 出力フォーマット

```
🤖 AI最新ニュース | 2026年5月27日（水）

（🔴【要注意】— 緊急時のみ、通常は省略）

🟢 OpenAI
*① タイトル*
説明1〜2行
• 詳細（箇条書き）
> 背景・影響（重要な場合のみ）
:paperclip: <URL>

🔵 Anthropic
...

🟡 Google / DeepMind
...

⚪ その他企業
...

📌 業界動向
_収集元: ... / 対象期間: 過去24時間_
```

---

## フォーマットルール

- 区切り線（`---`）は使わない
- セクション間は空行1行のみ
- URLは `:paperclip: <URL>` 形式
- 情報がない企業セクションは省略
- 情報がない日は「本日の主要アップデートなし」と記載
- 日本語で出力

### 🔴【要注意】セクションの条件（いずれかを満たす場合のみ）

- モデル・APIの廃止予告（移行期限あり）
- 既存APIの破壊的変更
- 大規模障害・サービス停止
- 開発者が即日対応を迫られる料金変更

---

## ファイル構成

| ファイル | 役割 |
|---|---|
| `fetch_raw_news.py` | 10サイトから生データ取得、stdoutへ出力 |
| `post_to_slack.py` | stdinからテキストを受け取りSlackへ投稿 |
| `requirements.txt` | Python依存ライブラリ |

## ワークフロー

`.github/workflows/ai-news-daily.yml` で管理。  
要約は `claude -p`（Claude Pro OAuthトークン）で実行するためAPI課金なし。

## 取得ソース

- OpenAI News / Changelog
- Anthropic News / API Release Notes
- Google AI Blog / DeepMind Blog / Gemini Changelog
- TechCrunch AI / The Verge AI / VentureBeat AI
