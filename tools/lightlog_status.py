"""
lightlog_status.py — lightlog（アフィリエイト事業部）進捗集約ツール

Lumen Industries COO が lightlog の状況を即座に把握するためのツール。
APIキー不要で動作します。

使い方:
    python tools/lightlog_status.py
    python tools/lightlog_status.py --json  # JSON形式で出力
"""

from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).parent.parent
TOPICS_FILE = ROOT / "automation" / "topics" / "saas_topics.json"
LATEST_ARTICLE = ROOT / "articles" / "latest.json"
REVENUE_DIR = ROOT / "output" / "revenue_reports"
NOTE_DRAFTS_DIR = ROOT / "automation" / "note_drafts"


def load_topics() -> dict:
    """saas_topics.json を読み込んでトピック統計を返す"""
    if not TOPICS_FILE.exists():
        return {"error": f"{TOPICS_FILE} が見つかりません"}

    with open(TOPICS_FILE, encoding="utf-8") as f:
        topics = json.load(f)

    posted = [t for t in topics if t.get("posted") is True]
    pending = [t for t in topics if t.get("posted") is not True]

    return {
        "total": len(topics),
        "posted_count": len(posted),
        "pending_count": len(pending),
        "posted_titles": [t.get("title", t.get("topic", "（タイトル不明）")) for t in posted],
        "next_topics": [t.get("title", t.get("topic", "（タイトル不明）")) for t in pending[:5]],
    }


def load_latest_article() -> dict:
    """articles/latest.json から直近の投稿記事情報を返す"""
    if not LATEST_ARTICLE.exists():
        return {"error": "latest.json が見つかりません（まだ記事が生成されていない可能性）"}

    with open(LATEST_ARTICLE, encoding="utf-8") as f:
        data = json.load(f)

    return {
        "title": data.get("title", "（タイトル不明）"),
        "meta_description": data.get("meta_description", ""),
        "has_affiliate": "affiliate" in data.get("content", "").lower(),
    }


def load_revenue_reports() -> dict:
    """output/revenue_reports/ 以下の最新レポートを返す"""
    if not REVENUE_DIR.exists():
        return {"status": "GA4計測中 ✅ — 翌月1日に初回レポートが自動生成されます"}

    reports = sorted(REVENUE_DIR.glob("*.md"), reverse=True)
    if not reports:
        return {"status": "GA4計測中 ✅ — 翌月1日に初回レポートが自動生成されます"}

    latest = reports[0]
    content = latest.read_text(encoding="utf-8")

    # 推定収益行を抽出
    revenue_line = ""
    for line in content.splitlines():
        if "推定" in line or "収益" in line or "円" in line:
            revenue_line = line.strip()
            break

    return {
        "latest_report": latest.name,
        "snippet": revenue_line or content[:200],
        "report_count": len(reports),
    }


def load_note_drafts() -> dict:
    """note_drafts の生成状況を返す"""
    if not NOTE_DRAFTS_DIR.exists():
        return {"count": 0, "latest": None}

    drafts = sorted(NOTE_DRAFTS_DIR.glob("*.md"), reverse=True)
    return {
        "count": len(drafts),
        "latest": drafts[0].name if drafts else None,
    }


def build_report(as_json: bool = False) -> str:
    """全データを集約してレポートを生成"""
    topics = load_topics()
    latest = load_latest_article()
    revenue = load_revenue_reports()
    notes = load_note_drafts()

    now = datetime.now().strftime("%Y-%m-%d %H:%M")

    if as_json:
        return json.dumps(
            {
                "generated_at": now,
                "site": "https://glowlog.net",
                "topics": topics,
                "latest_article": latest,
                "revenue": revenue,
                "note_drafts": notes,
            },
            ensure_ascii=False,
            indent=2,
        )

    # テキスト形式レポート
    lines = [
        "=" * 60,
        "  lightlog — アフィリエイト事業部 進捗レポート",
        f"  生成日時: {now}",
        f"  サイト: https://glowlog.net",
        "=" * 60,
        "",
    ]

    # コンテンツ進捗
    lines.append("【コンテンツ進捗】")
    if "error" in topics:
        lines.append(f"  ⚠️  {topics['error']}")
    else:
        progress_pct = int(topics["posted_count"] / topics["total"] * 100) if topics["total"] > 0 else 0
        bar_len = 20
        filled = int(bar_len * topics["posted_count"] / topics["total"]) if topics["total"] > 0 else 0
        bar = "█" * filled + "░" * (bar_len - filled)
        lines.append(f"  投稿済み: {topics['posted_count']}件 / 全{topics['total']}件  [{bar}] {progress_pct}%")
        lines.append(f"  残りトピック: {topics['pending_count']}件")
        if topics["posted_titles"]:
            lines.append("")
            lines.append("  ✅ 投稿済み記事:")
            for title in topics["posted_titles"]:
                lines.append(f"     • {title}")
    lines.append("")

    # 直近の投稿
    lines.append("【直近の生成記事】")
    if "error" in latest:
        lines.append(f"  ⚠️  {latest['error']}")
    else:
        lines.append(f"  タイトル: {latest['title']}")
        if latest["meta_description"]:
            lines.append(f"  概要: {latest['meta_description'][:80]}...")
        lines.append(f"  アフィリエイトリンク: {'✅ 含む' if latest['has_affiliate'] else '❌ なし'}")
    lines.append("")

    # 次回投稿予定
    if "error" not in topics and topics["next_topics"]:
        lines.append("【次回投稿予定トピック（上位5件）】")
        for i, title in enumerate(topics["next_topics"], 1):
            lines.append(f"  {i}. {title}")
        lines.append("")

    # 収益状況
    lines.append("【収益状況】")
    if "status" in revenue:
        lines.append(f"  {revenue['status']}")
    else:
        lines.append(f"  最新レポート: {revenue.get('latest_report', '—')}")
        lines.append(f"  レポート数: {revenue.get('report_count', 0)}件")
        if revenue.get("snippet"):
            lines.append(f"  概要: {revenue['snippet'][:100]}")
    lines.append("")

    # note下書き
    lines.append("【note 下書き】")
    if notes["count"] == 0:
        lines.append("  まだ下書きがありません")
    else:
        lines.append(f"  生成済み: {notes['count']}件")
        if notes["latest"]:
            lines.append(f"  最新: {notes['latest']}")
    lines.append("")

    # 自動化設定
    lines.append("【自動化ステータス】")
    lines.append("  📅 GitHub Actions: 毎日 JST 08:00 自動投稿")
    lines.append("  📝 note下書き: 毎週月曜 JST 9:00 自動生成")
    lines.append("  📊 収益レポート: 毎月1日 自動生成（GA4計測中 ✅）")
    lines.append("")
    lines.append("=" * 60)

    return "\n".join(lines)


if __name__ == "__main__":
    as_json = "--json" in sys.argv
    print(build_report(as_json=as_json))
