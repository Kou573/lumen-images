from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from article_generator import generate_article, load_next_topic, mark_topic_as_posted
from config import validate_affiliate_config
from wordpress_poster import post_article


def main() -> int:
    print("=" * 60)
    print("[START] アフィリエイト記事生成を開始します")
    print("=" * 60)

    if not validate_affiliate_config():
        print("[ABORT] 設定が不完全なため処理を中断します。")
        return 1

    topic = load_next_topic()
    if topic is None:
        print("[ABORT] 投稿可能なトピックがありません。")
        return 0

    print(f"[INFO] 処理トピック: {topic['title']}")

    try:
        title, content, meta_description, img_url = generate_article(topic)
    except Exception as e:
        print(f"[ERROR] 記事生成に失敗しました: {e}")
        return 1

    # ── latest.json に保存 ──
    output_path = Path(__file__).parent.parent / "articles" / "latest.json"
    output_path.parent.mkdir(exist_ok=True)
    output_path.write_text(
        json.dumps(
            {
                "title":              title,
                "content":            content,
                "meta_description":   meta_description,
                "featured_image_url": img_url,
                "wp_post_id":         None,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    # ── WordPress へ投稿（アイキャッチ + メタ説明を渡す） ──
    result = post_article(
        title=title,
        content=content,
        featured_image_url=img_url,
        meta_description=meta_description,
        tags=topic.get("affiliate_tools", []),
    )

    if "error" in result:
        print(f"[WARN] WordPress 投稿に失敗しました: {result['error']}")
        print("[INFO] 記事は latest.json に保存済みです。手動で投稿してください。")
    else:
        wp_post_id = result.get("id")
        print(f"[SUCCESS] WordPress 投稿完了: ID={wp_post_id}  URL={result.get('link', '')}")

    mark_topic_as_posted(topic["id"])

    print(f"[INFO]    メタ説明: {meta_description[:60]}...")
    print(f"[INFO]    アイキャッチ: {img_url[:80]}")
    print("=" * 60)
    return 0


if __name__ == "__main__":
    sys.exit(main())
