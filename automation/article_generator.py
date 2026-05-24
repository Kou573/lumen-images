from __future__ import annotations

import json
import re
import sys
import urllib.parse
from pathlib import Path

import anthropic

# パス解決
AUTOMATION_DIR = Path(__file__).parent
TOPICS_FILE = AUTOMATION_DIR / "topics" / "saas_topics.json"
TOOL_DATA_FILE = AUTOMATION_DIR / "tool_data.json"


def load_tool_data() -> dict:
    """tool_data.json を読み込む。ファイルが存在しない場合は空辞書を返す。"""
    if not TOOL_DATA_FILE.exists():
        print(f"[WARN] tool_data.json が見つかりません: {TOOL_DATA_FILE}")
        return {}
    with TOOL_DATA_FILE.open(encoding="utf-8") as f:
        return json.load(f)


def _build_affiliate_html(tool_name: str, tool_data: dict) -> str:
    """
    ツール名に対応するGA4イベント付きアフィリエイトボタンHTMLを生成する。

    ツール名が tool_data に存在しない場合は Google 検索フォールバックURLを使う。
    """
    entry = tool_data.get(tool_name)
    if entry:
        url = entry["official_url"]
    else:
        query = urllib.parse.quote(f"{tool_name} 公式サイト")
        url = f"https://www.google.com/search?q={query}"

    # ツール名内のシングルクォートをエスケープ（インラインonclick用）
    safe_tool_name = tool_name.replace("'", "\\'")

    return (
        '<div class="tool-cta" style="margin: 16px 0; padding: 12px; '
        'background: #f8f9fa; border-radius: 6px; border-left: 3px solid #0066cc;">\n'
        f'  <a href="{url}"\n'
        '     target="_blank"\n'
        '     rel="noopener noreferrer sponsored"\n'
        f"     onclick=\"if(typeof gtag!=='undefined'){{gtag('event','tool_click',"
        f"{{'tool_name':'{safe_tool_name}','event_category':'affiliate_placeholder'}})}}\"\n"
        '     style="color: #0066cc; font-weight: bold; text-decoration: none;">\n'
        f"    {tool_name} の公式サイトを確認する &rarr;\n"
        "  </a>\n"
        "</div>"
    )


def replace_affiliate_placeholders(html_content: str, tool_data: dict) -> str:
    """
    HTML内の <!-- AFFILIATE_LINK: ツール名 --> をGA4イベント付きボタンHTMLに置換する。
    """
    pattern = re.compile(r"<!--\s*AFFILIATE_LINK:\s*(.+?)\s*-->")

    def replacer(match: re.Match) -> str:
        tool_name = match.group(1).strip()
        return _build_affiliate_html(tool_name, tool_data)

    replaced = pattern.sub(replacer, html_content)
    count = len(pattern.findall(html_content))
    if count:
        print(f"[INFO] アフィリエイトプレースホルダーを {count} 件置換しました。")
    return replaced


CATEGORY_IMAGES: dict[str, str] = {
    "会計・経費管理":       "https://images.unsplash.com/photo-1554224155-6726b3ff858f?w=1200&auto=format&fit=crop",
    "AI・生産性":           "https://images.unsplash.com/photo-1677442135703-1787eea5ce01?w=1200&auto=format&fit=crop",
    "デザイン・クリエイティブ": "https://images.unsplash.com/photo-1626785774573-4b799315345d?w=1200&auto=format&fit=crop",
    "プロジェクト管理・メモ":  "https://images.unsplash.com/photo-1611532736597-de2d4265fba3?w=1200&auto=format&fit=crop",
    "電子契約・法務":        "https://images.unsplash.com/photo-1450101499163-c8848c66ca85?w=1200&auto=format&fit=crop",
    "コミュニケーション":     "https://images.unsplash.com/photo-1600880292203-757bb62b4baf?w=1200&auto=format&fit=crop",
    "転職・キャリア":        "https://images.unsplash.com/photo-1521737711867-e3b97375f902?w=1200&auto=format&fit=crop",
    "スキマバイト・副業":     "https://images.unsplash.com/photo-1434626881859-194d67b2b86f?w=1200&auto=format&fit=crop",
    "レンタルサーバー":       "https://images.unsplash.com/photo-1558494949-ef010cbdcc31?w=1200&auto=format&fit=crop",
}
DEFAULT_IMAGE = "https://images.unsplash.com/photo-1460925895917-afdab827c52f?w=1200&auto=format&fit=crop"


def _prepend_eyecatch_image(keyword: str, category: str) -> str:
    img_url = CATEGORY_IMAGES.get(category, DEFAULT_IMAGE)
    alt = keyword.replace('"', "&quot;")
    return (
        f'<figure class="wp-block-image size-large">'
        f'<img src="{img_url}" alt="{alt}" style="width:100%;height:auto;border-radius:8px;">'
        f'</figure>'
    )


SYSTEM_PROMPT = """\
あなたは日本語SEOライターです。デジタルサービス・ツールの比較・レビュー記事を書きます。
対応カテゴリ：SaaS・ビジネスツール、AIツール、レンタルサーバー、転職・キャリアアプリ、スキマバイト・副業アプリ
ルール：
- 読者：副業・効率化・転職に関心のある20〜40代
- 語調：です・ます調、専門的だが読みやすい
- SEO：キーワードを自然に本文に組み込む（詰め込まない）
- 構成：導入→特徴比較→料金・条件→こんな人向け→まとめ
- アフィリエイトリンク挿入位置に <!-- AFFILIATE_LINK: ツール名 --> を入れる
- 事実に基づいて書く。不確かな情報は「〜とされている」と書く
- 転職・求人カテゴリは特に慎重に。断定的な収入保証は書かない\
"""


def load_next_topic() -> dict | None:
    """未投稿のトピックを1件取得する。"""
    if not TOPICS_FILE.exists():
        print(f"[ERROR] トピックファイルが見つかりません: {TOPICS_FILE}")
        return None
    with TOPICS_FILE.open(encoding="utf-8") as f:
        topics: list[dict] = json.load(f)
    for topic in topics:
        if not topic.get("posted", False):
            return topic
    print("[INFO] 未投稿のトピックがありません。")
    return None


def mark_topic_as_posted(topic_id: int) -> None:
    """指定IDのトピックを投稿済みにマークする。"""
    with TOPICS_FILE.open(encoding="utf-8") as f:
        topics: list[dict] = json.load(f)
    for topic in topics:
        if topic["id"] == topic_id:
            topic["posted"] = True
            break
    with TOPICS_FILE.open("w", encoding="utf-8") as f:
        json.dump(topics, f, ensure_ascii=False, indent=2)
    print(f"[INFO] トピック ID={topic_id} を投稿済みにマークしました。")


def generate_article(topic: dict) -> tuple[str, str]:
    """
    Claude Haiku でSEOアフィリエイト記事を生成する。

    Returns:
        (title, html_content)
    """
    from config import ANTHROPIC_API_KEY

    title: str = topic["title"]
    keyword: str = topic.get("keyword", title)
    category: str = topic.get("category", "")
    affiliate_tools: list[str] = topic.get("affiliate_tools", [])

    tools_str = "、".join(affiliate_tools) if affiliate_tools else "各ツール"

    user_prompt = f"""\
以下のトピックでSEOアフィリエイト記事を書いてください。

タイトル: {title}
メインキーワード: {keyword}
カテゴリ: {category}
紹介するツール: {tools_str}

要件:
- HTML形式で出力（<h1>, <h2>, <h3>, <p>, <ul>, <li> タグを使用）
- <h1> でタイトルを最初に書く
- 導入文 300字以上
- H2セクション 4〜5個
- 各セクション内に <!-- AFFILIATE_LINK: ツール名 --> を1箇所挿入
- まとめセクション 200字以上
- 合計 1,500〜2,000字（日本語）
- <html>, <body>, <head> タグは不要。記事本文のみ出力。\
"""

    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    print(f"[INFO] 記事生成開始: {title}")

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
        content = response.content[0].text
        print(f"[INFO] 記事生成完了: {len(content)}文字")

        # ```html や ``` のコードブロックマーカーを除去
        content = re.sub(r"^```html\s*", "", content.strip())
        content = re.sub(r"```\s*$", "", content.strip())

        # アフィリエイトプレースホルダーをGA4イベント付きボタンHTMLに置換
        tool_data = load_tool_data()
        content = replace_affiliate_placeholders(content, tool_data)

        # 記事冒頭にカテゴリ対応のアイキャッチ画像を追加
        content = _prepend_eyecatch_image(keyword, category) + "\n" + content

        return title, content
    except anthropic.APIError as e:
        print(f"[ERROR] Claude API エラー: {e}")
        raise
