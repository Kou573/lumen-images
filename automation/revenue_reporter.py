from __future__ import annotations

import base64
import json
import logging
import math
import os
import re
import tempfile
from datetime import date, timedelta
from pathlib import Path

# ロギング設定（認証情報がログに出力されないよう basicConfig のみ使用）
logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

AUTOMATION_DIR = Path(__file__).parent
TOOL_DATA_FILE = AUTOMATION_DIR / "tool_data.json"
REPO_ROOT = AUTOMATION_DIR.parent
OUTPUT_DIR = REPO_ROOT / "output" / "revenue_reports"

REVENUE_GOAL = 200_000  # 月間収益目標（円）


# ---------------------------------------------------------------------------
# 認証セットアップ
# ---------------------------------------------------------------------------

def _setup_ga4_credentials() -> str | None:
    """
    環境変数 GA4_SERVICE_ACCOUNT_JSON（base64）からサービスアカウントJSONを
    一時ファイルに展開し、そのパスを返す。

    Returns:
        一時ファイルのパス。環境変数未設定の場合は None。
    """
    encoded = os.environ.get("GA4_SERVICE_ACCOUNT_JSON", "")
    if not encoded:
        return None
    try:
        sa_json = base64.b64decode(encoded).decode("utf-8")
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False, prefix="ga4sa_"
        ) as f:
            f.write(sa_json)
            return f.name
    except Exception as e:
        logger.error("サービスアカウントJSONのデコードに失敗しました: %s", e)
        return None


# ---------------------------------------------------------------------------
# GA4 データ取得
# ---------------------------------------------------------------------------

def fetch_tool_clicks(property_id: str, creds_path: str) -> dict[str, int]:
    """
    GA4 Data API で過去30日間の tool_click イベントを取得し、
    {ツール名: クリック数} の辞書を返す。

    Args:
        property_id: GA4 プロパティID（数字のみ）
        creds_path: サービスアカウントJSONの一時ファイルパス

    Returns:
        {tool_name: click_count}
    """
    try:
        from google.analytics.data_v1beta import BetaAnalyticsDataClient
        from google.analytics.data_v1beta.types import (
            DateRange,
            Dimension,
            Metric,
            RunReportRequest,
        )
    except ImportError:
        logger.error(
            "google-analytics-data パッケージが見つかりません。"
            "`pip install google-analytics-data` を実行してください。"
        )
        return {}

    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = creds_path

    try:
        client = BetaAnalyticsDataClient()
    except Exception as e:
        logger.error("GA4クライアントの初期化に失敗しました: %s", e)
        return {}

    end_date = date.today()
    start_date = end_date - timedelta(days=30)

    request = RunReportRequest(
        property=f"properties/{property_id}",
        date_ranges=[
            DateRange(
                start_date=start_date.strftime("%Y-%m-%d"),
                end_date=end_date.strftime("%Y-%m-%d"),
            )
        ],
        dimensions=[
            Dimension(name="eventName"),
            Dimension(name="customEvent:tool_name"),
        ],
        metrics=[Metric(name="eventCount")],
        dimension_filter={
            "filter": {
                "field_name": "eventName",
                "string_filter": {"value": "tool_click"},
            }
        },
    )

    try:
        response = client.run_report(request)
    except Exception as e:
        logger.error("GA4 API リクエストに失敗しました: %s", e)
        return {}

    clicks: dict[str, int] = {}
    for row in response.rows:
        tool_name = row.dimension_values[1].value
        count = int(row.metric_values[0].value)
        if tool_name and tool_name != "(not set)":
            clicks[tool_name] = clicks.get(tool_name, 0) + count

    logger.info("GA4からツール別クリックデータを取得しました: %d ツール", len(clicks))
    return clicks


# ---------------------------------------------------------------------------
# 収益計算
# ---------------------------------------------------------------------------

def calc_revenue(clicks: dict[str, int], tool_data: dict) -> list[dict]:
    """
    クリック数 × CVR × 単価 で各ツールの推定収益を計算する。

    Returns:
        各ツールの計算結果リスト（収益降順でソート済み）
    """
    results: list[dict] = []
    for tool_name, click_count in clicks.items():
        entry = tool_data.get(tool_name, {})
        cvr = entry.get("cvr_estimate", 0.02)
        unit_price = entry.get("affiliate_unit_price", 5000)
        estimated_conversions = click_count * cvr
        estimated_revenue = math.floor(estimated_conversions * unit_price)
        results.append(
            {
                "tool_name": tool_name,
                "clicks": click_count,
                "cvr": cvr,
                "estimated_conversions": estimated_conversions,
                "unit_price": unit_price,
                "estimated_revenue": estimated_revenue,
            }
        )
    results.sort(key=lambda x: x["estimated_revenue"], reverse=True)
    return results


# ---------------------------------------------------------------------------
# 前月レポート読み込み
# ---------------------------------------------------------------------------

def _load_prev_revenue(current_ym: str) -> int | None:
    """
    前月のレポートファイルから推定収益を読み取って返す。

    Args:
        current_ym: 今月の YYYYMM 文字列

    Returns:
        前月の推定収益（円）。ファイルが存在しない場合は None。
    """
    year = int(current_ym[:4])
    month = int(current_ym[4:])
    if month == 1:
        prev_ym = f"{year - 1:04d}12"
    else:
        prev_ym = f"{year:04d}{month - 1:02d}"

    prev_file = OUTPUT_DIR / f"{prev_ym}_estimate.md"
    if not prev_file.exists():
        return None

    text = prev_file.read_text(encoding="utf-8")
    match = re.search(r"\*\*推定月間収益\*\*.*?¥([\d,]+)", text)
    if match:
        return int(match.group(1).replace(",", ""))
    return None


# ---------------------------------------------------------------------------
# レポート生成
# ---------------------------------------------------------------------------

def _monetization_status(total_revenue: int) -> str:
    if total_revenue >= REVENUE_GOAL:
        return "🟢 収益化タイミングです"
    elif total_revenue >= REVENUE_GOAL * 0.5:
        remaining = REVENUE_GOAL - total_revenue
        months_to_goal = (
            math.ceil(REVENUE_GOAL / total_revenue) - 1 if total_revenue > 0 else "?"
        )
        return (
            f"🟡 目標の50%達成。あと{months_to_goal}ヶ月で到達予測"
            f"（残り ¥{remaining:,}）"
        )
    else:
        remaining = REVENUE_GOAL - total_revenue
        return f"⏳ 成長中。目標まで ¥{remaining:,}"


def build_report(
    clicks: dict[str, int],
    tool_data: dict,
    current_ym: str,
    end_date: date,
) -> str:
    """Markdown形式のレポート文字列を生成する。"""
    results = calc_revenue(clicks, tool_data)
    total_clicks = sum(r["clicks"] for r in results)
    total_revenue = sum(r["estimated_revenue"] for r in results)

    start_date = end_date - timedelta(days=30)
    report_date_str = end_date.strftime("%Y年%m月%d日")
    period_str = (
        f"{start_date.strftime('%Y年%m月%d日')} 〜 {end_date.strftime('%Y年%m月%d日')}"
    )

    year_str = current_ym[:4]
    month_str = current_ym[4:]
    title_month = f"{year_str}年{month_str}月"

    status_str = _monetization_status(total_revenue)
    remaining = max(REVENUE_GOAL - total_revenue, 0)

    # サマリー行
    if total_revenue >= REVENUE_GOAL:
        summary_row = f"| 収益化判断 | {status_str} |"
    else:
        summary_row = f"| 収益化判断 | ⏳ 目標まで ¥{remaining:,} |"

    # ツール別テーブル行
    tool_rows = "\n".join(
        f"| {r['tool_name']} | {r['clicks']:,} | "
        f"{r['cvr'] * 100:.1f}% | "
        f"{r['estimated_conversions']:.1f}件 | "
        f"¥{r['unit_price']:,} | "
        f"¥{r['estimated_revenue']:,} |"
        for r in results
    )
    if not tool_rows:
        tool_rows = "| （データなし） | - | - | - | - | - |"

    # 前月比セクション
    prev_revenue = _load_prev_revenue(current_ym)
    if prev_revenue is None:
        mom_section = "初回レポートのため前月比較はありません。"
    else:
        diff = total_revenue - prev_revenue
        sign = "+" if diff >= 0 else ""
        mom_section = (
            f"前月推定収益: ¥{prev_revenue:,}  \n"
            f"今月推定収益: ¥{total_revenue:,}  \n"
            f"前月比: {sign}¥{diff:,}"
        )

    # 次のアクション
    if total_revenue >= REVENUE_GOAL:
        next_action = (
            "- 推定収益が目標の ¥200,000 を超えました。"
            "アフィリエイトASP（A8.net、もしもアフィリエイト等）への登録を検討してください。\n"
            "- 登録後、本記事内のプレースホルダーリンクを正式なアフィリエイトリンクに差し替えてください。"
        )
    else:
        top_tools = [r["tool_name"] for r in results[:3]]
        tools_str = "、".join(top_tools) if top_tools else "（なし）"
        next_action = (
            f"- クリック数上位ツール（{tools_str}）に関連する記事を追加して流入を増やしましょう。\n"
            "- 既存記事の見出しやCTAボタンの文言を見直し、クリック率改善を図ってください。"
        )

    report = f"""\
# Lightlog 推定収益レポート — {title_month}

**集計期間**: {period_str}
**レポート生成**: {report_date_str}

## サマリー

| 指標 | 値 |
|---|---|
| 総クリック数（全ツール合計） | {total_clicks:,} 回 |
| **推定月間収益** | **¥{total_revenue:,}** |
{summary_row}

> 目標：月200,000円を超えたら収益化を検討

## 収益化ステータス

{status_str}

## ツール別クリック・推定収益

| ツール | 月間クリック | 推定CVR | 推定成約数 | 単価 | 推定収益 |
|---|---|---|---|---|---|
{tool_rows}

## 前月比

{mom_section}

## 次のアクション

{next_action}
"""
    return report


def save_report(report: str, current_ym: str) -> Path:
    """レポートを output/revenue_reports/YYYYMM_estimate.md に保存する。"""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    out_file = OUTPUT_DIR / f"{current_ym}_estimate.md"
    out_file.write_text(report, encoding="utf-8")
    logger.info("レポートを保存しました: %s", out_file)
    return out_file


# ---------------------------------------------------------------------------
# エントリーポイント
# ---------------------------------------------------------------------------

def main() -> None:
    # 必須環境変数チェック
    property_id = os.environ.get("GA4_PROPERTY_ID", "")
    if not property_id:
        logger.error(
            "環境変数 GA4_PROPERTY_ID が未設定です。"
            "GA4プロパティIDを設定してから再実行してください。"
        )
        return

    sa_encoded = os.environ.get("GA4_SERVICE_ACCOUNT_JSON", "")
    if not sa_encoded:
        logger.error(
            "環境変数 GA4_SERVICE_ACCOUNT_JSON が未設定です。"
            "base64エンコードされたサービスアカウントJSONを設定してください。"
        )
        return

    # 認証情報セットアップ
    creds_path = _setup_ga4_credentials()
    if creds_path is None:
        logger.error("GA4認証情報のセットアップに失敗しました。処理を終了します。")
        return

    # tool_data.json 読み込み
    if not TOOL_DATA_FILE.exists():
        logger.error("tool_data.json が見つかりません: %s", TOOL_DATA_FILE)
        return
    with TOOL_DATA_FILE.open(encoding="utf-8") as f:
        tool_data: dict = json.load(f)

    # 日付設定
    today = date.today()
    current_ym = today.strftime("%Y%m")

    # GA4 データ取得
    logger.info("GA4からクリックデータを取得中...")
    clicks = fetch_tool_clicks(property_id, creds_path)

    # 一時ファイルを削除（認証情報をファイルシステムに残さない）
    try:
        os.unlink(creds_path)
    except OSError:
        pass

    # レポート生成・保存
    report = build_report(clicks, tool_data, current_ym, today)
    out_file = save_report(report, current_ym)
    logger.info("レポート生成完了: %s", out_file.name)


if __name__ == "__main__":
    main()
