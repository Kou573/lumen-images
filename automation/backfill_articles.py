"""
過去に投稿済みの記事を最新デザイン水準にバックフィルするスクリプト。

処理内容:
  1. saas_topics.json から posted:true のトピックを取得
  2. 各トピックの記事を article_generator.py で再生成
     （ヒーローバナー・ツールロゴ・カードグリッド・アイキャッチ対応）
  3. WordPress で同タイトルの記事を検索して post_id を特定
  4. wp.editPost で本文・アイキャッチを上書き更新

使い方:
  python automation/backfill_articles.py          # 全投稿済み記事を更新
  python automation/backfill_articles.py --dry-run # 再生成のみ、WPへの書き込みなし
  python automation/backfill_articles.py --id 3   # 特定 id のみ
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from article_generator import generate_article
from config import validate_affiliate_config
from wordpress_poster import find_existing_post, update_article

import xmlrpc.client

TOPICS_FILE = Path(__file__).parent / "topics" / "saas_topics.json"
OUTPUT_DIR  = Path(__file__).parent.parent / "articles" / "backfill"

# 記事生成の間隔（Claude API レート制限対策）
SLEEP_BETWEEN_ARTICLES = 8  # 秒


def _get_server():
    from config import WP_URL
    endpoint = f"{WP_URL.rstrip('/')}/xmlrpc.php"
    return xmlrpc.client.ServerProxy(endpoint)


def _load_posted_topics(only_id: int | None) -> list[dict]:
    with TOPICS_FILE.open(encoding="utf-8") as f:
        topics = json.load(f)
    posted = [t for t in topics if t.get("posted")]
    if only_id is not None:
        posted = [t for t in posted if t["id"] == only_id]
    return posted


def backfill(dry_run: bool, only_id: int | None) -> int:
    print("=" * 60)
    mode = "[DRY-RUN] " if dry_run else ""
    print(f"{mode}バックフィル開始")
    print("=" * 60)

    if not validate_affiliate_config():
        print("[ABORT] 設定が不完全なため処理を中断します。")
        return 1

    topics = _load_posted_topics(only_id)
    if not topics:
        print("[INFO] 対象トピックが見つかりません。")
        return 0
    print(f"[INFO] 対象: {len(topics)} 件")

    from config import WP_USERNAME, WP_APP_PASSWORD
    server = _get_server() if not dry_run else None

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    success_count = 0
    fail_count    = 0

    for i, topic in enumerate(topics):
        tid   = topic["id"]
        title = topic["title"]
        print(f"\n[{i+1}/{len(topics)}] ID={tid}  {title}")

        # ── 記事を再生成 ──
        try:
            _, content, meta_description, img_url = generate_article(topic)
            print(f"  [OK] 記事生成完了 ({len(content)} 文字)")
        except Exception as e:
            print(f"  [ERROR] 記事生成失敗: {e}")
            fail_count += 1
            continue

        # ── dry-run はここまで ──
        if dry_run:
            out = OUTPUT_DIR / f"{tid}.html"
            out.write_text(content, encoding="utf-8")
            print(f"  [DRY-RUN] 保存しました: {out}")
            success_count += 1
            continue

        # ── WP で既存記事を探す ──
        post_id = find_existing_post(server, WP_USERNAME, WP_APP_PASSWORD, title)
        if not post_id:
            print(f"  [WARN] WordPress に該当記事が見つかりません（スキップ）: {title}")
            fail_count += 1
            continue
        print(f"  [INFO] WP post_id={post_id} を更新します")

        # ── 記事を更新 ──
        result = update_article(
            post_id=post_id,
            title=title,
            content=content,
            featured_image_url=img_url,
            meta_description=meta_description,
        )
        if "error" in result:
            print(f"  [ERROR] 更新失敗: {result['error']}")
            fail_count += 1
        else:
            print(f"  [SUCCESS] 更新完了: {result.get('link', '')}")
            success_count += 1

        # ── 次の記事まで待機 ──
        if i < len(topics) - 1:
            print(f"  [WAIT] {SLEEP_BETWEEN_ARTICLES}秒待機...")
            time.sleep(SLEEP_BETWEEN_ARTICLES)

    print("\n" + "=" * 60)
    print(f"完了: 成功={success_count}  失敗={fail_count}")
    print("=" * 60)
    return 0 if fail_count == 0 else 1


def main() -> int:
    parser = argparse.ArgumentParser(description="lightlog 過去記事バックフィル")
    parser.add_argument("--dry-run", action="store_true",
                        help="WPへの書き込みを行わず記事HTMLをローカルに保存するだけ")
    parser.add_argument("--id", type=int, default=None,
                        help="特定のトピック id のみ処理する")
    args = parser.parse_args()
    return backfill(dry_run=args.dry_run, only_id=args.id)


if __name__ == "__main__":
    sys.exit(main())
