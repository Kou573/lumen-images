from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from article_generator import generate_article, load_next_topic, mark_topic_as_posted
from config import validate_affiliate_config


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
        title, content = generate_article(topic)
    except Exception as e:
        print(f"[ERROR] 記事生成に失敗しました: {e}")
        return 1

    # GitHubリポジトリに articles/latest.json として保存
    output_path = Path(__file__).parent.parent / "articles" / "latest.json"
    output_path.parent.mkdir(exist_ok=True)
    output_path.write_text(
        json.dumps({"title": title, "content": content}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"[SUCCESS] 記事を保存しました: {output_path}")
    print(f"[INFO] タイトル: {title}")

    mark_topic_as_posted(topic["id"])

    print("=" * 60)
    print("[DONE] WordPressはGitHubから自動読み込みして投稿します")
    print("=" * 60)
    return 0


if __name__ == "__main__":
    sys.exit(main())
