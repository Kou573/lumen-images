from __future__ import annotations

import sys
from pathlib import Path

# 相対インポートを解決するため automation/ をパスに追加
sys.path.insert(0, str(Path(__file__).parent))

from config import validate_note_config
from note_draft_generator import (
    generate_note_draft,
    load_next_note_topic,
    mark_note_topic_as_posted,
)


def main() -> int:
    """note記事ドラフトの生成→Markdownファイル保存を実行する。"""
    print("=" * 60)
    print("[START] note記事ドラフト生成を開始します")
    print("=" * 60)

    # 設定チェック
    if not validate_note_config():
        print("[ABORT] 設定が不完全なため処理を中断します。")
        return 1

    # トピック取得
    topic = load_next_note_topic()
    if topic is None:
        print("[ABORT] 生成可能なトピックがありません。")
        return 0

    print(f"[INFO] 処理トピック: {topic['title']}")

    # ドラフト生成・保存
    try:
        saved_path = generate_note_draft(topic)
    except Exception as e:
        print(f"[ERROR] ドラフト生成に失敗しました: {e}")
        return 1

    # 投稿済みマーク
    mark_note_topic_as_posted(topic["id"])

    print("=" * 60)
    print(f"[SUCCESS] ドラフト保存完了: {saved_path}")
    print("  → ファイルを開いてnoteに貼り付け→公開ボタンを押してください。")
    print("=" * 60)
    return 0


if __name__ == "__main__":
    sys.exit(main())
