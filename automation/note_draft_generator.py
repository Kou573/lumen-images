from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

import anthropic

AUTOMATION_DIR = Path(__file__).parent
TOPICS_FILE = AUTOMATION_DIR / "topics" / "note_topics.json"
DRAFTS_DIR = AUTOMATION_DIR / "note_drafts"

SYSTEM_PROMPT = """\
あなたはRinged Tail Studioというnoteアカウントのライターです。
ルール：
- 感情・個人情報を一切書かない
- 数字・ツール名・手順を主役にする
- 「試した→結果→判定」の構造で書く
- 文体：である調、箇条書き多用
- 見出し：H2/H3構成
- 文字数：1,200〜1,500字
- 有料記事の場合：最初の400字で無料公開し、残りを有料パートとして区切り線で示す\
"""


def load_next_note_topic() -> dict | None:
    """未投稿のnoteトピックを1件取得する。"""
    if not TOPICS_FILE.exists():
        print(f"[ERROR] トピックファイルが見つかりません: {TOPICS_FILE}")
        return None
    with TOPICS_FILE.open(encoding="utf-8") as f:
        topics: list[dict] = json.load(f)
    for topic in topics:
        if not topic.get("posted", False):
            return topic
    print("[INFO] 未投稿のnoteトピックがありません。")
    return None


def mark_note_topic_as_posted(topic_id: int) -> None:
    """指定IDのnoteトピックを投稿済みにマークする。"""
    with TOPICS_FILE.open(encoding="utf-8") as f:
        topics: list[dict] = json.load(f)
    for topic in topics:
        if topic["id"] == topic_id:
            topic["posted"] = True
            break
    with TOPICS_FILE.open("w", encoding="utf-8") as f:
        json.dump(topics, f, ensure_ascii=False, indent=2)
    print(f"[INFO] noteトピック ID={topic_id} を投稿済みにマークしました。")


def _safe_filename(title: str) -> str:
    """タイトルをファイル名に使える文字列に変換する。"""
    # ファイル名として使えない文字を除去・置換
    replacements = str.maketrans(
        {
            "/": "・",
            "\\": "・",
            ":": "：",
            "*": "＊",
            "?": "？",
            '"': "'",
            "<": "＜",
            ">": "＞",
            "|": "｜",
            " ": "_",
            "\t": "_",
        }
    )
    return title.translate(replacements)[:60]


def generate_note_draft(topic: dict) -> Path:
    """
    Claude Haiku でnote記事ドラフトを生成してMarkdownファイルに保存する。

    Returns:
        保存したファイルのパス
    """
    from config import ANTHROPIC_API_KEY

    title: str = topic["title"]
    article_type: str = topic.get("type", "free")
    tags: list[str] = topic.get("tags", [])
    memo: str = topic.get("memo", "")

    is_paid = article_type == "paid"
    paid_instruction = (
        "\n- 有料記事として構成する：最初の400字を無料公開パートとし、"
        "\n  「---\n## ここから有料パート\n---」の区切り線で残りの有料パートを示す"
        if is_paid
        else ""
    )

    user_prompt = f"""\
以下のトピックでnote記事のドラフトを書いてください。

タイトル: {title}
記事タイプ: {"有料記事" if is_paid else "無料記事"}
タグ: {", ".join(tags)}
メモ・方針: {memo}{paid_instruction}

出力形式: Markdown（タイトルは # で始めること）
文字数: 1,200〜1,500字\
"""

    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    print(f"[INFO] note記事ドラフト生成開始: {title}")

    try:
        response = client.messages.create(
            model="claude-haiku-4-5",
            max_tokens=4096,
            system=[
                {
                    "type": "text",
                    "text": SYSTEM_PROMPT,
                    "cache_control": {"type": "ephemeral"},
                }
            ],
            messages=[{"role": "user", "content": user_prompt}],
        )
        draft_body = response.content[0].text
    except anthropic.APIError as e:
        print(f"[ERROR] Claude API エラー: {e}")
        raise

    # ファイルヘッダー（投稿手順コメント）
    tags_str = ", ".join(tags)
    header = f"""\
<!--
📋 noteへの投稿手順：
1. このファイルの内容をコピー（タグ設定を除く）
2. note.comでエディタを開いて貼り付け
3. タグを設定: [{tags_str}]
4. 公開ボタンを押す
-->

"""

    full_content = header + draft_body

    # 保存先ディレクトリを確保
    DRAFTS_DIR.mkdir(parents=True, exist_ok=True)

    date_str = datetime.now().strftime("%Y%m%d")
    safe_title = _safe_filename(title)
    filename = f"{date_str}_{safe_title}.md"
    output_path = DRAFTS_DIR / filename

    output_path.write_text(full_content, encoding="utf-8")
    print(f"[INFO] ドラフト保存完了: {output_path}")
    return output_path
