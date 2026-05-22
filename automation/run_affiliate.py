from __future__ import annotations

import sys
from pathlib import Path

# 相対インポートを解決するため automation/ をパスに追加
sys.path.insert(0, str(Path(__file__).parent))

from article_generator import generate_article, load_next_topic, mark_topic_as_posted
from config import validate_affiliate_config
from wordpress_poster import post_article


def main() -> int:
    """アフィリエイト記事の生成→WordPress投稿を実行する。"""
    print("=" * 60)
    print("[START] アフィリエイト自動投稿を開始します")
    print("=" * 60)

    # 設定チェック
    if not validate_affiliate_config():
        print("[ABORT] 設定が不完全なため処理を中断します。")
        return 1

    # トピック取得
    topic = load_next_topic()
    if topic is None:
        print("[ABORT] 投稿可能なトピックがありません。")
        return 0

    print(f"[INFO] 処理トピック: {topic['title']}")

    # 記事生成
    try:
        title, content = generate_article(topic)
    except Exception as e:
        print(f"[ERROR] 記事生成に失敗しました: {e}")
        return 1

    # WordPress投稿
    tags: list[str] = [topic.get("category", ""), *topic.get("affiliate_tools", [])]
    tags = [t for t in tags if t]  # 空文字を除去

    result = post_article(title=title, content=content, tags=tags)

    if "error" in result:
        print(f"[ERROR] WordPress投稿に失敗しました: {result['error']}")
        return 1

    # 投稿済みマーク
    mark_topic_as_posted(topic["id"])

    print("=" * 60)
    post_url = result.get("link", "（URL不明）")
    print(f"[SUCCESS] 投稿完了: {post_url}")
    print("=" * 60)
    return 0


if __name__ == "__main__":
    sys.exit(main())
