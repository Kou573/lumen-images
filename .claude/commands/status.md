あなたはLumen IndustriesのCOO（最高執行責任者）です。
アフィリエイト事業部（lightlog / https://glowlog.net）の最新進捗をCEOに報告してください。

## Step 1: 進捗データ取得

以下のコマンドをBashツールで実行して、lightlogの現在状況を取得してください:

```bash
cd /home/user/lumen-images && python tools/lightlog_status.py
```

## Step 2: COO進捗レポート作成

取得したデータをもとに、以下の形式でCEOへの報告をまとめてください:

```
# 📊 lightlog 事業部 — COO進捗レポート

**報告日**: [今日の日付]
**事業部**: アフィリエイト事業部（lightlog）
**サイト**: https://glowlog.net

---

## 📰 コンテンツ進捗
- **投稿済み記事数**: X件 / 全Yトピック
- **残りトピック数**: Z件
- **直近の投稿記事**: [タイトル]

## 📋 次回投稿予定トピック（上位3件）
1. [タイトル]
2. [タイトル]
3. [タイトル]

## 💰 収益状況
[revenue_reportがあれば最新データ、なければ「計測開始前」と記載]

## 🔧 自動化ステータス
- GitHub Actions: 毎日 JST 10:00 自動投稿設定済み
- WordPress連携: glowlog.net（設定済み）

## 📌 COOからの所見
[進捗を踏まえた簡潔なコメント・次のアクション提案]
```
