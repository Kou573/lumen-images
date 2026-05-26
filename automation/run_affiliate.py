from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from article_generator import generate_article, load_next_topic, mark_topic_as_posted
from config import validate_affiliate_config

# JST = UTC+9
JST = timezone(timedelta(hours=9))

# -----------------------------------------------------------------------
# 終了コード
# -----------------------------------------------------------------------
EXIT_SUCCESS = 0   # 新規記事生成 & 保存完了
EXIT_ERROR   = 1   # 致命的エラー（ワークフロー失敗扱い）
EXIT_SKIP    = 0   # スキップ（当日生成済み or トピックなし）— エラーではないので 0

# -----------------------------------------------------------------------
# 当日生成済みチェック
# -----------------------------------------------------------------------

def already_generated_today(output_path: Path) -> bool:
    """
    latest.json の generated_at が今日の JST 日付と一致する場合 True を返す。
    手動トリガーや多重実行による同一記事の連投を防ぐガード。
    FORCE_REGENERATE=true の場合はこのチェックをバイパスする。
    """
    if os.environ.get("FORCE_REGENERATE", "false").lower() == "true":
        print("[INFO] FORCE_REGENERATE=true のためスキップチェックをバイパスします。")
        return False

    if not output_path.exists():
        return False

    try:
        data = json.loads(output_path.read_text(encoding="utf-8"))
        generated_at_str = data.get("generated_at", "")
        if not generated_at_str:
            return False
        dt = datetime.fromisoformat(generated_at_str)
        today_jst = datetime.now(JST).date()
        if dt.astimezone(JST).date() == today_jst:
            print(f"[SKIP] 本日（JST {today_jst}）は topic_id={data.get('topic_id', '?')} "
                  f"「{data.get('title', '?')}」をすでに生成済みです。")
            return True
    except Exception as e:
        print(f"[WARN] generated_at チェックに失敗しました（{e}）。生成を続行します。")

    return False


# -----------------------------------------------------------------------
# メイン
# -----------------------------------------------------------------------

def main() -> int:
    print("=" * 60)
    print("[START] アフィリエイト記事生成を開始します")
    print("=" * 60)

    if not validate_affiliate_config():
        print("[ABORT] 設定が不完全なため処理を中断します。")
        return EXIT_ERROR

    output_path = Path(__file__).parent.parent / "articles" / "latest.json"
    marker_path = Path(__file__).parent.parent / "articles" / ".new_article"

    # マーカーをリセット（前回の残骸を消す）
    marker_path.unlink(missing_ok=True)

    # --- 当日生成済みチェック ---
    if already_generated_today(output_path):
        print("[SKIP] 本日分は生成済みのため終了します。")
        print("[SKIP]   強制再生成が必要な場合は workflow_dispatch で "
              "force_regenerate=true を指定してください。")
        return EXIT_SKIP

    topic = load_next_topic()
    if topic is None:
        print("[INFO] 未投稿トピックがありません。全トピック投稿完了です。")
        return EXIT_SKIP

    print(f"[INFO] 処理トピック: {topic['title']}  (id={topic['id']})")

    try:
        title, content, meta_description, img_url = generate_article(topic)
    except Exception as e:
        print(f"[ERROR] 記事生成に失敗しました: {e}")
        return EXIT_ERROR

    now_jst = datetime.now(JST).isoformat()
    output_path.parent.mkdir(exist_ok=True)
    output_path.write_text(
        json.dumps(
            {
                "topic_id":           topic["id"],
                "title":              title,
                "content":            content,
                "meta_description":   meta_description,
                "featured_image_url": img_url,
                "generated_at":       now_jst,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    mark_topic_as_posted(topic["id"])

    # 新規記事マーカーを書き込む（ワークフローが WP-Cron 条件分岐に使用）
    marker_path.write_text(str(topic["id"]), encoding="utf-8")

    print(f"[SUCCESS] 記事を保存しました: {title}")
    print(f"[INFO]    topic_id:     {topic['id']}")
    print(f"[INFO]    generated_at: {now_jst}")
    print(f"[INFO]    メタ説明:     {meta_description[:60]}...")
    print(f"[INFO]    アイキャッチ: {img_url[:80]}")
    print("=" * 60)
    return EXIT_SUCCESS


if __name__ == "__main__":
    sys.exit(main())
