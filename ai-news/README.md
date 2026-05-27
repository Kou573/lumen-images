# aiNEWS部門 — Slack配信ルール

毎朝8:05 JST に `#ai-news` チャンネル（ID: `C0AU8RW9W94`）へ自動投稿する。

---

## 収集ルール

- **対象期間**: 過去24時間以内の情報のみ（古いニュースは含めない）
- **情報源**: 以下のソースを優先的に使用すること

### 一次情報（公式サイト）

| ソース | URL |
|---|---|
| OpenAI公式ニュース | https://openai.com/news/ |
| Anthropic公式ニュース | https://www.anthropic.com/news |
| Google AI公式ブログ | https://blog.google/technology/ai/ |
| Google DeepMind公式 | https://deepmind.google/blog/ |
| Anthropic APIリリースノート | https://docs.anthropic.com/en/release-notes/overview |
| Gemini APIチェンジログ | https://ai.google.dev/gemini-api/docs/changelog |
| OpenAI APIチェンジログ | https://platform.openai.com/docs/changelog |
| Anthropic障害情報 | https://status.anthropic.com |
| OpenAI障害情報 | https://status.openai.com |

### X（旧Twitter）公式アカウント（参考）

- @OpenAI / @sama（Sam Altman）/ @gdb（Greg Brockman）
- @AnthropicAI / @dariobei（Dario Amodei）
- @GoogleDeepMind / @sundarpichai（Sundar Pichai）

> GitHub Actions上ではX直接取得不可。WebSearchで補完する。

### 速報・深掘りメディア

| ソース | URL |
|---|---|
| TechCrunch AI | https://techcrunch.com/category/artificial-intelligence/ |
| The Verge AI | https://theverge.com/ai |
| VentureBeat AI | https://venturebeat.com/ai/ |
| LLM Stats Updates | https://llm-stats.com/llm-updates |
| LLM Stats AI News | https://llm-stats.com/ai-news |

---

## 検索方法

WebSearchを使い、以下のクエリで順番に検索する：

1. `site:openai.com OR site:anthropic.com OR site:blog.google "今日の日付 例: April 29 2026"`
2. `OpenAI Anthropic Google AI news [今日の日付] 2026`
3. `site:x.com @OpenAI OR @AnthropicAI OR @GoogleDeepMind [今日の日付]`
4. `OpenAI [今日の日付] 2026 site:techcrunch.com OR site:theverge.com OR site:venturebeat.com`
5. 気になるトピックは個別にWebSearchで深掘り検索する

公式サイトはWebFetchで直接取得し、最新記事のURLを抽出してから各記事を読み込む。

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

## 送信内容のガイドライン

- **表面的な情報ではなく、背景・理由・業界への影響まで深掘りすること**
- モデルリリース、API仕様変更、ビジネス動向、法的・政策動向をすべてカバー
- 開発者・ビジネスユーザー双方に有益な情報を含める
- 仕様変更・廃止予告など「見逃すと困る」情報は特に強調する
- 各ニュースに必ずソースURLを添付する
- 障害・ダウン情報があれば必ず含める

---

## 出力フォーマット

```
🤖 AI最新ニュース | 2026年5月27日（水）

（🔴【要注意】— 廃止予告・破壊的API変更・大規模障害など緊急時のみ、通常は省略）

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

### フォーマットルール

- 区切り線（`---`）は使わない
- セクション間は空行1行のみ
- URLは `:paperclip: <URL>` 形式
- 情報がない企業セクションは省略
- 情報がない日は「本日の主要アップデートなし」と記載
- 日本語で出力

### 🔴【要注意】の発動条件（いずれかを満たす場合のみ）

- モデル・APIの廃止予告（移行期限あり）
- 既存APIの破壊的変更
- 大規模障害・サービス停止
- 開発者が即日対応を迫られる料金変更

---

## ファイル構成

| ファイル | 役割 |
|---|---|
| `fetch_raw_news.py` | フォールバック用：requestsで生データ取得（通常は不使用） |
| `post_to_slack.py` | stdinからテキストを受け取りSlackへ投稿 |
| `requirements.txt` | Python依存ライブラリ |

## ワークフロー

`.github/workflows/ai-news-daily.yml` で管理。  
`claude -p` が WebSearch / WebFetch ツールで能動的にニュースを収集・要約し、`post_to_slack.py` で送信する。  
API課金なし（Claude Pro OAuthトークン使用）。
