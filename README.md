# Lumen Industries

AI駆動のコンテンツ・自動化ビジネスを運営するリポジトリです。

## 部門構成

| 部門 | 概要 |
|---|---|
| 🌐 アフィリエイト事業部（lightlog） | WordPressへのAI記事自動投稿（毎日 JST 08:00） |
| 📸 Lumen IG部門 | Instagram自動投稿（毎朝8時、Coworkで稼働中） |
| 📰 aiNEWS部門 | AIニュース収集 → Slack #ai-news 配信（毎朝8時） |
| 🎸 BandHub部門 | Notion全DBバックアップ（毎週日曜23時） |

## ディレクトリ構成

```
automation/     ← lightlog自動投稿システム
lumen-ig/       ← Instagram自動投稿部門
  scripts/      ← 投稿スクリプト置き場（daily_post.py 等）
ai-news/        ← AIニュースSlack配信部門
band-hub/       ← BandHub Notionバックアップ部門
agents/         ← Pythonエージェント（APIキー版）
tools/          ← ユーティリティスクリプト
output/         ← 生成物の保存先
articles/       ← 直近の生成記事データ
```

## 起動方法

```bash
# Claude Code をこのディレクトリで開く（推奨）
claude

# APIキーモード（課金あり）
python main.py "ゴール"
```

詳細な操作方法は [CLAUDE.md](./CLAUDE.md) を参照してください。
