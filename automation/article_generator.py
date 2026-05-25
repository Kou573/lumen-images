from __future__ import annotations

import json
import re
import sys
import urllib.parse
from pathlib import Path

import anthropic

AUTOMATION_DIR = Path(__file__).parent
TOPICS_FILE = AUTOMATION_DIR / "topics" / "saas_topics.json"
TOOL_DATA_FILE = AUTOMATION_DIR / "tool_data.json"


def load_tool_data() -> dict:
    if not TOOL_DATA_FILE.exists():
        print(f"[WARN] tool_data.json が見つかりません: {TOOL_DATA_FILE}")
        return {}
    with TOOL_DATA_FILE.open(encoding="utf-8") as f:
        return json.load(f)


def _build_affiliate_html(tool_name: str, tool_data: dict) -> str:
    entry = tool_data.get(tool_name)
    if entry:
        url = entry["official_url"]
    else:
        query = urllib.parse.quote(f"{tool_name} 公式サイト")
        url = f"https://www.google.com/search?q={query}"

    safe_tool_name = tool_name.replace("'", "\\'")

    return (
        '<div class="affiliate-cta" style="margin:24px 0;padding:20px 24px;'
        'background:linear-gradient(135deg,#f0f7ff,#e8f4e8);'
        'border-radius:10px;border-left:4px solid #0066cc;'
        'box-shadow:0 2px 8px rgba(0,102,204,0.12);">\n'
        f'  <p style="margin:0 0 12px;font-size:15px;font-weight:700;color:#1a1a1a;">'
        f'【PR】{tool_name} を試してみる</p>\n'
        f'  <a href="{url}"\n'
        '     target="_blank"\n'
        '     rel="noopener noreferrer sponsored"\n'
        f"     onclick=\"if(typeof gtag!=='undefined'){{gtag('event','tool_click',"
        f"{{'tool_name':'{safe_tool_name}','event_category':'affiliate'}})}}\"\n"
        '     style="display:inline-block;padding:12px 28px;'
        'background:#0066cc;color:#fff;font-weight:700;font-size:15px;'
        'text-decoration:none;border-radius:6px;letter-spacing:0.03em;'
        'transition:background 0.2s;">\n'
        f"    {tool_name} 公式サイトを確認する &#x2192;\n"
        "  </a>\n"
        '  <p style="margin:8px 0 0;font-size:12px;color:#666;">'
        '※ 本記事のリンクは広告を含みます</p>\n'
        "</div>"
    )


def replace_affiliate_placeholders(html_content: str, tool_data: dict) -> str:
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
    "会計・経費管理":           "https://images.unsplash.com/photo-1554224155-6726b3ff858f?w=1200&auto=format&fit=crop",
    "AI・生産性":               "https://images.unsplash.com/photo-1677442135703-1787eea5ce01?w=1200&auto=format&fit=crop",
    "デザイン・クリエイティブ": "https://images.unsplash.com/photo-1626785774573-4b799315345d?w=1200&auto=format&fit=crop",
    "プロジェクト管理・メモ":   "https://images.unsplash.com/photo-1611532736597-de2d4265fba3?w=1200&auto=format&fit=crop",
    "プロジェクト管理":         "https://images.unsplash.com/photo-1611532736597-de2d4265fba3?w=1200&auto=format&fit=crop",
    "電子契約・法務":           "https://images.unsplash.com/photo-1450101499163-c8848c66ca85?w=1200&auto=format&fit=crop",
    "コミュニケーション":       "https://images.unsplash.com/photo-1600880292203-757bb62b4baf?w=1200&auto=format&fit=crop",
    "コミュニケーション・動画": "https://images.unsplash.com/photo-1600880292203-757bb62b4baf?w=1200&auto=format&fit=crop",
    "Web会議・コミュニケーション": "https://images.unsplash.com/photo-1587614382346-4ec70e388b28?w=1200&auto=format&fit=crop",
    "転職・キャリア":           "https://images.unsplash.com/photo-1521737711867-e3b97375f902?w=1200&auto=format&fit=crop",
    "副業・スキマバイト":       "https://images.unsplash.com/photo-1434626881859-194d67b2b86f?w=1200&auto=format&fit=crop",
    "スキマバイト・副業":       "https://images.unsplash.com/photo-1434626881859-194d67b2b86f?w=1200&auto=format&fit=crop",
    "レンタルサーバー":         "https://images.unsplash.com/photo-1558494949-ef010cbdcc31?w=1200&auto=format&fit=crop",
    "業務改善・ローコード":     "https://images.unsplash.com/photo-1519389950473-47ba0277781c?w=1200&auto=format&fit=crop",
    "業務自動化":               "https://images.unsplash.com/photo-1518432031352-d6fc5c10da5a?w=1200&auto=format&fit=crop",
    "CRM・マーケティング":      "https://images.unsplash.com/photo-1533750349088-cd871a92f312?w=1200&auto=format&fit=crop",
}
DEFAULT_IMAGE = "https://images.unsplash.com/photo-1460925895917-afdab827c52f?w=1200&auto=format&fit=crop"


def _eyecatch_html(keyword: str, category: str) -> str:
    img_url = CATEGORY_IMAGES.get(category, DEFAULT_IMAGE)
    alt = keyword.replace('"', "&quot;")
    return (
        f'<figure class="wp-block-image size-large" style="margin:0 0 32px;">'
        f'<img src="{img_url}" alt="{alt}" '
        f'style="width:100%;height:auto;border-radius:10px;'
        f'box-shadow:0 4px 16px rgba(0,0,0,0.12);">'
        f'</figure>\n'
    )


def _section_image_html(keyword: str, category: str, index: int) -> str:
    """セクション内の補助画像（eyecatchとは別のURLでバリエーションを持たせる）"""
    base_url = CATEGORY_IMAGES.get(category, DEFAULT_IMAGE)
    # クエリパラメータで別カットを取得
    variant_url = base_url.replace("w=1200", "w=800") + f"&q=80&sat=-10"
    alt = f"{keyword} のイメージ {index}"
    return (
        f'<figure class="wp-block-image" style="margin:20px 0;">'
        f'<img src="{variant_url}" alt="{alt}" '
        f'style="width:100%;max-width:720px;height:auto;border-radius:8px;">'
        f'</figure>\n'
    )


SYSTEM_PROMPT = """\
あなたは日本語SEOアフィリエイトライターです。デジタルサービス・ツールの比較・レビュー記事を書きます。
対応カテゴリ：SaaS・ビジネスツール、AIツール、レンタルサーバー、転職・キャリア、スキマバイト・副業

【厳守ルール】
- 読者：副業・効率化・転職に関心のある20〜40代
- 語調：です・ます調、専門的だが読みやすい
- SEO：メインキーワードを自然に本文に組み込む（詰め込まない）
- 構成：導入→特徴比較→料金・条件→こんな人向け→まとめ
- アフィリエイトリンク位置に <!-- AFFILIATE_LINK: ツール名 --> を挿入（各H2セクションに1箇所）
- 比較テーブルをHTML <table>タグで作成（必須）
- 事実に基づいて書く。不確かな情報は「〜とされている」と書く
- 転職・求人カテゴリは慎重に。断定的な収入保証は書かない
- 記事中の年号は2026年（「2025年最新」は書かない）
- コンバージョンを高めるため、まとめセクションに強いCTAボタン用プレースホルダーを入れる\
"""


def load_next_topic() -> dict | None:
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

【必須要件】
1. HTML形式で出力（<h2>, <h3>, <p>, <ul>, <li>, <table> タグを使用）
2. <h1>タグでタイトルを最初に書く
3. 導入文 400字以上（読者の課題・悩みを具体的に提示してから記事の価値を説明）
4. H2セクション 4〜5個
5. 各H2セクション内に <!-- AFFILIATE_LINK: ツール名 --> を1箇所挿入
6. 料金・機能比較テーブルをHTMLで作成（thead/tbody使用、スタイル付き）:
   - style="width:100%;border-collapse:collapse;margin:20px 0;"
   - thにstyle="background:#f0f0f0;padding:10px;text-align:left;border:1px solid #ddd;"
   - tdにstyle="padding:10px;border:1px solid #ddd;"
7. 「こんな人におすすめ」チェックリスト（<ul>+<li>で5項目以上）
8. まとめセクション 300字以上（明確な推薦と <!-- AFFILIATE_LINK: ツール名 --> を末尾に）
9. 合計 2,000〜2,500字
10. <html>, <body>, <head> タグは不要。記事本文のみ出力。
11. コードブロック（```html など）は使わない。HTMLタグをそのまま出力。\
"""

    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    print(f"[INFO] 記事生成開始: {title}")

    try:
        response = client.messages.create(
            model="claude-haiku-4-5-20251001",
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
        content = re.sub(r"^```html\s*\n?", "", content.strip())
        content = re.sub(r"\n?```\s*$", "", content.strip())

        # アフィリエイトプレースホルダーをGA4イベント付きボタンHTMLに置換
        tool_data = load_tool_data()
        content = replace_affiliate_placeholders(content, tool_data)

        # セクション画像を中間部分に追加（h2の2番目の後ろ）
        section_img = _section_image_html(keyword, category, 1)
        h2_matches = list(re.finditer(r"<h2[^>]*>", content))
        if len(h2_matches) >= 2:
            insert_pos = h2_matches[1].start()
            content = content[:insert_pos] + section_img + content[insert_pos:]

        # 記事冒頭にアイキャッチ画像を追加
        eyecatch = _eyecatch_html(keyword, category)
        content = eyecatch + content

        return title, content
    except anthropic.APIError as e:
        print(f"[ERROR] Claude API エラー: {e}")
        raise
