from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from article_generator import generate_article, load_next_topic, mark_topic_as_posted
from config import validate_affiliate_config
from wordpress_poster import post_article


def main() -> int:
    print("=" * 60)
    print("[START] アフィリエイト自動投稿を開始します")
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
        title, content = generate_article(topic)
    except Exception as e:
        print(f"[ERROR] 記事生成に失敗しました: {e}")
        return 1

    result = post_article(title=title, content=content)

    if "error" in result:
        print(f"[ERROR] WordPress投稿に失敗しました: {result['error']}")
        return 1

    mark_topic_as_posted(topic["id"])

    print("=" * 60)
    print(f"[SUCCESS] 投稿完了: {result.get('link', '（URL不明）')}")
    print("=" * 60)
    return 0


if __name__ == "__main__":
    sys.exit(main())
