"""
Affiliate article generator with SEO / AIO / LLMO optimisations.

AIO  = AI Overview (Google のAI概要) 対策
LLMO = LLM Optimisation (ChatGPT・Perplexity 等に引用されやすい構造)
SEO  = 従来の検索エンジン最適化
"""
from __future__ import annotations

import json
import re
import urllib.parse
from datetime import datetime
from pathlib import Path

import anthropic

AUTOMATION_DIR = Path(__file__).parent
TOPICS_FILE    = AUTOMATION_DIR / "topics" / "saas_topics.json"
TOOL_DATA_FILE = AUTOMATION_DIR / "tool_data.json"
IMAGES_DIR     = AUTOMATION_DIR.parent / "articles" / "images"

GITHUB_RAW_BASE = (
    "https://raw.githubusercontent.com/Kou573/lumen-images/main/articles/images"
)


# ---------------------------------------------------------------------------
# Tool data helpers
# ---------------------------------------------------------------------------

def load_tool_data() -> dict:
    if not TOOL_DATA_FILE.exists():
        print(f"[WARN] tool_data.json が見つかりません: {TOOL_DATA_FILE}")
        return {}
    with TOOL_DATA_FILE.open(encoding="utf-8") as f:
        return json.load(f)


# ---------------------------------------------------------------------------
# Affiliate CTA button
# ---------------------------------------------------------------------------

def _build_affiliate_html(tool_name: str, tool_data: dict) -> str:
    entry    = tool_data.get(tool_name) or {}
    url      = entry.get("official_url") or (
        "https://www.google.com/search?q=" + urllib.parse.quote(f"{tool_name} 公式サイト")
    )
    logo_url = entry.get("logo_url", "")
    category = entry.get("category", "")
    safe     = tool_name.replace("'", "\\'")

    # ── ロゴ部分（logo_url があれば表示） ──
    if logo_url:
        logo_html = (
            f'<img src="{logo_url}" alt="{tool_name} ロゴ" width="52" height="52" '
            'loading="lazy" style="border-radius:10px;border:1px solid #dde8fa;'
            'background:#fff;padding:5px;object-fit:contain;flex-shrink:0;">'
        )
    else:
        logo_html = (
            '<div style="width:52px;height:52px;border-radius:10px;'
            'background:#0066cc;display:flex;align-items:center;justify-content:center;'
            'color:#fff;font-weight:700;font-size:18px;flex-shrink:0;">'
            f'{tool_name[0]}</div>'
        )

    cat_html = (
        f'<span style="font-size:12px;color:#666;">{category}</span>' if category else ""
    )

    return (
        '<div class="affiliate-cta" style="margin:32px 0;padding:22px 24px;'
        'background:linear-gradient(135deg,#eef5ff,#eaffef);'
        'border-radius:12px;border-left:4px solid #0066cc;'
        'box-shadow:0 4px 16px rgba(0,102,204,0.12);">'
        # ── ヘッダー行：ロゴ + ツール名 ──
        '<div style="display:flex;align-items:center;gap:14px;margin-bottom:14px;">'
        f'{logo_html}'
        '<div>'
        f'<p style="margin:0 0 3px;font-size:16px;font-weight:700;color:#1a1a1a;">{tool_name}</p>'
        f'{cat_html}'
        '</div>'
        '</div>'
        # ── CTA ボタン ──
        f'<a href="{url}" target="_blank" rel="noopener noreferrer sponsored"'
        f' onclick="if(typeof gtag!==\'undefined\'){{gtag(\'event\',\'tool_click\','
        f'{{\'tool_name\':\'{safe}\',\'event_category\':\'affiliate\'}})}}"'
        ' style="display:inline-block;padding:13px 32px;background:#0066cc;color:#fff;'
        'font-weight:700;font-size:15px;text-decoration:none;border-radius:8px;'
        'box-shadow:0 2px 8px rgba(0,102,204,0.30);">'
        f'{tool_name} 公式サイトを確認する &#x2192;</a>'
        '<p style="margin:10px 0 0;font-size:11px;color:#999;">※ 広告リンクを含みます</p>'
        '</div>'
    )


def replace_affiliate_placeholders(html: str, tool_data: dict) -> str:
    """
    <!-- AFFILIATE_LINK: ツール名 --> を CTA ボタン HTML に置換する。
    3 箇所以上ある場合は先頭と末尾の 2 箇所だけ残し、中間のものは空文字で除去する。
    """
    pattern = re.compile(r"<!--\s*AFFILIATE_LINK:\s*(.+?)\s*-->")
    matches = list(pattern.finditer(html))
    n = len(matches)
    if n == 0:
        return html

    # 残す位置: 先頭と末尾のみ（2箇所以下なら全部残す）
    if n <= 2:
        keep_starts = {m.start() for m in matches}
    else:
        keep_starts = {matches[0].start(), matches[-1].start()}
        print(f"[INFO] CTA {n}箇所 → 先頭と末尾の2箇所のみ残しました（中間 {n - 2} 箇所を除去）。")

    result = pattern.sub(
        lambda m: _build_affiliate_html(m.group(1).strip(), tool_data)
        if m.start() in keep_starts else "",
        html,
    )
    kept = min(n, 2)
    print(f"[INFO] アフィリエイトCTA {kept}箇所を置換しました。")
    return result


# ---------------------------------------------------------------------------
# Image generation (GPT-image / DALL-E 3 → fallback Unsplash)
# ---------------------------------------------------------------------------

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


def _unsplash_fallback(category: str, topic_id: int) -> str:
    """
    カテゴリ対応の Unsplash 画像を返す。
    sig=topic_id を追加することで記事ごとに異なる画像が配信される。
    """
    base = CATEGORY_IMAGES.get(category, DEFAULT_IMAGE)
    sep  = "&" if "?" in base else "?"
    return f"{base}{sep}sig={topic_id}"


def _generate_ai_image(keyword: str, category: str, topic_id: int) -> str:
    """
    GPT-image-1 (gpt-image-1) または DALL-E 3 で記事専用画像を生成する。
    生成した画像は articles/images/{topic_id}.jpg に保存してGitHub raw URLを返す。
    OPENAI_API_KEY が未設定の場合は Unsplash フォールバック URL を返す（sig で記事ごとに差別化）。
    """
    from config import OPENAI_API_KEY
    if not OPENAI_API_KEY:
        return _unsplash_fallback(category, topic_id)

    try:
        import requests as req
        from openai import OpenAI

        client = OpenAI(api_key=OPENAI_API_KEY)
        prompt = (
            f"Professional, clean blog header image for a Japanese business website. "
            f"Topic: {keyword}. Category: {category}. "
            "Modern flat illustration or infographic style. No text. "
            "Soft blue and white color palette. 16:9 ratio composition."
        )
        print(f"[INFO] AI画像を生成中: {keyword}")

        # gpt-image-1 を試みて、なければ dall-e-3 へフォールバック
        for model in ("gpt-image-1", "dall-e-3"):
            try:
                resp = client.images.generate(
                    model=model,
                    prompt=prompt,
                    size="1024x1024",
                    quality="standard",
                    n=1,
                )
                image_url = resp.data[0].url
                break
            except Exception:
                continue
        else:
            raise RuntimeError("画像生成モデルが利用できませんでした")

        # ダウンロードしてリポジトリに保存
        IMAGES_DIR.mkdir(parents=True, exist_ok=True)
        img_path = IMAGES_DIR / f"{topic_id}.jpg"
        img_bytes = req.get(image_url, timeout=30).content
        img_path.write_bytes(img_bytes)
        print(f"[INFO] AI画像を保存しました: {img_path.name}")

        return f"{GITHUB_RAW_BASE}/{topic_id}.jpg"

    except Exception as e:
        print(f"[WARN] AI画像生成に失敗しました ({e})。Unsplash にフォールバック。")
        return _unsplash_fallback(category, topic_id)


def _estimate_read_time(content: str) -> int:
    """HTML タグを除去した文字数から読了時間（分）を推定する（日本語 400字/分）。"""
    text = re.sub(r"<[^>]+>", "", content)
    return max(3, round(len(text) / 400))


def _eyecatch_html(
    keyword: str,
    img_url: str,
    category: str = "",
    read_time: int = 0,
) -> str:
    """
    ヒーローバナー HTML。
    - 画像の下部にグラデーションオーバーレイ
    - カテゴリバッジ + 読了時間を表示
    """
    alt       = keyword.replace('"', "&quot;")
    cat_badge = ""
    if category:
        cat_badge = (
            f'<span style="display:inline-block;background:#0066cc;color:#fff;'
            f'font-size:11px;font-weight:700;padding:4px 14px;border-radius:20px;'
            f'letter-spacing:0.8px;margin-bottom:10px;">{category}</span>'
        )
    rt_badge = ""
    if read_time:
        rt_badge = (
            f'<span style="color:rgba(255,255,255,0.88);font-size:13px;">'
            f'📖 読了時間：約{read_time}分 &nbsp;|&nbsp; 🗓 2026年最新</span>'
        )

    return (
        '<div class="article-hero" style="position:relative;width:100%;margin:0 0 40px;'
        'border-radius:14px;overflow:hidden;box-shadow:0 8px 40px rgba(0,0,0,0.20);">'
        f'<img src="{img_url}" alt="{alt}" loading="eager"'
        ' style="width:100%;height:380px;object-fit:cover;display:block;">'
        # グラデーションオーバーレイ
        '<div style="position:absolute;inset:0;'
        'background:linear-gradient(170deg,rgba(0,30,80,0.06) 30%,rgba(0,20,60,0.68) 100%);">'
        '</div>'
        # バッジエリア
        '<div style="position:absolute;bottom:0;left:0;right:0;padding:24px 32px;">'
        f'{cat_badge}<br>'
        f'{rt_badge}'
        '</div>'
        '</div>\n'
    )


def _tool_overview_html(affiliate_tools: list[str], tool_data: dict) -> str:
    """
    記事冒頭に挿入する「この記事で紹介するツール」カードグリッド。
    logo_url があればロゴ画像を表示し、権威性を高める。
    """
    if not affiliate_tools:
        return ""

    cards = []
    for name in affiliate_tools:
        entry    = tool_data.get(name) or {}
        logo_url = entry.get("logo_url", "")
        url      = entry.get("official_url", "#")

        if logo_url:
            logo_html = (
                f'<img src="{logo_url}" alt="{name} ロゴ" width="36" height="36" '
                'loading="lazy" style="border-radius:6px;object-fit:contain;'
                'background:#fff;border:1px solid #e4ecfa;padding:3px;">'
            )
        else:
            logo_html = (
                '<div style="width:36px;height:36px;border-radius:6px;'
                'background:#0066cc;color:#fff;font-weight:700;font-size:14px;'
                'display:flex;align-items:center;justify-content:center;">'
                f'{name[0]}</div>'
            )

        cards.append(
            f'<a href="{url}" target="_blank" rel="noopener noreferrer" '
            'style="display:flex;align-items:center;gap:10px;'
            'background:#fff;border:1px solid #dde8fa;border-radius:8px;'
            'padding:10px 14px;text-decoration:none;min-width:150px;'
            'transition:box-shadow 0.2s;" '
            'onmouseover="this.style.boxShadow=\'0 4px 12px rgba(0,102,204,0.15)\'" '
            'onmouseout="this.style.boxShadow=\'none\'">'
            f'{logo_html}'
            f'<span style="font-size:14px;font-weight:600;color:#1a1a1a;">{name}</span>'
            '</a>'
        )

    cards_html = "\n    ".join(cards)
    return (
        '<div class="tools-overview" '
        'style="background:#f4f8ff;border:1px solid #d0e0ff;border-radius:12px;'
        'padding:20px 24px;margin:0 0 36px;">'
        '<p style="margin:0 0 14px;font-size:12px;font-weight:700;color:#555;'
        'text-transform:uppercase;letter-spacing:1.2px;">この記事で紹介するツール</p>'
        '<div style="display:flex;flex-wrap:wrap;gap:10px;">'
        f'\n    {cards_html}\n'
        '</div>'
        '</div>\n'
    )


def _section_image_html(keyword: str, topic_id: int) -> str:
    """
    セクション画像はアイキャッチと異なる Unsplash フォトを使う。
    topic_id + 1000 を sig に使うことでアイキャッチ（sig=topic_id）と別の画像になる。
    """
    alt = keyword.replace('"', "&quot;") + " 活用イメージ"
    # ビジネス/チームワークをテーマにした別の写真ベース（アイキャッチと被らない）
    base = "https://images.unsplash.com/photo-1522071820081-009f0129c71c?w=800&auto=format&fit=crop"
    url  = f"{base}&sig={topic_id + 1000}"
    return (
        f'<figure class="wp-block-image" style="margin:32px 0;">'
        f'<img src="{url}" alt="{alt}" loading="lazy"'
        f' style="width:100%;max-width:720px;height:auto;border-radius:8px;">'
        f'</figure>\n'
    )


# ---------------------------------------------------------------------------
# JSON-LD schema helpers
# ---------------------------------------------------------------------------

def _build_article_schema(title: str, url_slug: str, description: str) -> str:
    today = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
    schema = {
        "@context": "https://schema.org",
        "@type": "Article",
        "headline": title,
        "description": description,
        "datePublished": today,
        "dateModified":  today,
        "author": {
            "@type": "Organization",
            "name":  "Lightlog",
            "url":   "https://glowlog.net"
        },
        "publisher": {
            "@type": "Organization",
            "name":  "Lightlog",
            "logo":  {
                "@type": "ImageObject",
                "url":   "https://glowlog.net/wp-content/uploads/logo.png"
            }
        },
        "mainEntityOfPage": {
            "@type": "@id",
            "@id":   f"https://glowlog.net/{url_slug}/"
        }
    }
    return (
        '<script type="application/ld+json">\n'
        + json.dumps(schema, ensure_ascii=False, indent=2)
        + '\n</script>\n'
    )


def _build_faq_schema(faq_items: list[dict]) -> str:
    """faq_items: [{"q": "...", "a": "..."}, ...]"""
    if not faq_items:
        return ""
    schema = {
        "@context": "https://schema.org",
        "@type": "FAQPage",
        "mainEntity": [
            {
                "@type": "Question",
                "name": item["q"],
                "acceptedAnswer": {
                    "@type": "Answer",
                    "text":  item["a"]
                }
            }
            for item in faq_items
        ]
    }
    return (
        '<script type="application/ld+json">\n'
        + json.dumps(schema, ensure_ascii=False, indent=2)
        + '\n</script>\n'
    )


_FAQ_PATTERN = re.compile(
    r'<h[23][^>]*>\s*(?:Q[\.．:：]?\s*|【Q】)?(.*?)\s*</h[23]>\s*<p>(.*?)</p>',
    re.DOTALL | re.IGNORECASE
)


def _extract_faq_items(html: str) -> list[dict]:
    """FAQ セクション内の Q&A を抽出する（ベストエフォート）。"""
    faq_section = re.search(
        r'<h2[^>]*>.*?よくある質問.*?</h2>(.*?)(?=<h2|$)',
        html, re.DOTALL | re.IGNORECASE
    )
    if not faq_section:
        return []
    block = faq_section.group(1)
    items = []
    for m in re.finditer(
        r'<(?:h3|dt)[^>]*>(.*?)</(?:h3|dt)>\s*<(?:p|dd)[^>]*>(.*?)</(?:p|dd)>',
        block, re.DOTALL
    ):
        q = re.sub(r'<[^>]+>', '', m.group(1)).strip()
        a = re.sub(r'<[^>]+>', '', m.group(2)).strip()
        if q and a:
            items.append({"q": q, "a": a[:200]})
    return items[:5]


# ---------------------------------------------------------------------------
# System prompts (SEO / AIO / LLMO 対応)
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = """\
あなたは日本のSEO・AIO・LLMOに精通したアフィリエイトライターです。
下記のルールに従って記事を作成してください。

【SEO対策】
- メインキーワードはタイトル・H1・最初のpタグ・まとめに必ず含める
- LSIキーワード（関連語）を本文全体に自然に散りばめる
- H2 → H3 の階層を正しく守る

【AIO対策（Google AI Overview / AI概要）】
- 各H2直下に40〜60字の「要点ボックス」 (<div class="summary-box">) を置く
- 冒頭の「この記事でわかること」で記事の結論を先出しする
- 「よくある質問」セクションは <dl><dt><dd> 形式で 4〜5 Q&A を書く
- 数字・固有名詞・料金・日付を積極的に使い、AI が引用しやすい事実ベースの文章にする

【LLMO対策（ChatGPT・Perplexity 等への最適化）】
- 「結論→理由→根拠→具体例」の PREP 構造で各セクションを書く
- ツール名・会社名・料金・機能を箇条書きで明示する
- 比較テーブルに ○△× や 具体的数値 を入れる
- 「〜によると」「〜のデータでは」など引用フレーズを使う（事実ベース）

【その他ルール】
- HTML形式（<h1><h2><h3><p><ul><li><table><dl><dt><dd>）
- 記事中の年号は2026年（2025年最新は書かない）
- <!-- AFFILIATE_LINK: ツール名 --> は記事全体で厳密に2箇所のみ（1つ目は導入文の直後、2つ目はまとめセクションの末尾）
- 各 H2 セクションには必ず上下に余白を設ける: <h2 style="margin-top:48px;padding-top:8px;border-top:2px solid #e8e8e8;">
- 各段落 <p> には style="margin-bottom:1.4em;line-height:1.85;" を付ける
- <html><body><head>タグは不要、記事本文のみ
- コードブロック（```）は使わない\
"""

USER_PROMPT_TEMPLATE = """\
以下のトピックで、SEO・AIO・LLMOに最適化されたアフィリエイト記事を書いてください。

タイトル: {title}
メインキーワード: {keyword}
カテゴリ: {category}
紹介ツール: {tools}
メタ説明（140字以内）: ← 記事の冒頭コメントに <!-- META_DESCRIPTION: ... --> として埋め込む

【必須構成】
1. <!-- META_DESCRIPTION: 140字以内のメタ説明 -->（コメントとして冒頭）
2. <h1> タイトル
3. <div class="summary-box"> この記事でわかること（ul 3〜5項目）</div>
4. 導入文 350字以上（読者の悩みを具体的に提示）
5. H2 × 4〜5個（各H2直下に40〜60字の要点ボックス）※CTAは導入文直後と まとめ末尾の2箇所のみ
6. 料金・機能比較テーブル（thead/tbody使用、○△×や数値で明記）
7. <h2>よくある質問</h2>（<dl><dt><dd> 形式で 4〜5 Q&A）
8. <h2>まとめ</h2>（結論と強いCTAを含む）
9. 合計 2,200〜2,800字（日本語）

【テーブルスタイル例】
<table style="width:100%;border-collapse:collapse;margin:20px 0;">
  <thead><tr>
    <th style="background:#1a5cad;color:#fff;padding:10px;border:1px solid #ddd;">項目</th>
    ...
  </tr></thead>
  <tbody><tr>
    <td style="padding:10px;border:1px solid #ddd;">内容</td>
    ...
  </tr></tbody>
</table>

【要点ボックスのスタイル例】
<div class="summary-box" style="background:#f0f7ff;border-left:3px solid #1a5cad;padding:12px 16px;margin:12px 0;border-radius:4px;font-size:14px;">
  <strong>ポイント：</strong>テキスト
</div>\
"""


# ---------------------------------------------------------------------------
# Topic management
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# Main article generator
# ---------------------------------------------------------------------------

def generate_article(topic: dict) -> tuple[str, str, str, str]:
    """
    Returns (title, html_content, meta_description, img_url) with:
    - SEO / AIO / LLMO optimised HTML
    - AI-generated or Unsplash eyecatch image
    - JSON-LD Article + FAQ schema
    - Affiliate CTA buttons
    """
    from config import ANTHROPIC_API_KEY

    title:          str       = topic["title"]
    keyword:        str       = topic.get("keyword", title)
    category:       str       = topic.get("category", "")
    topic_id:       int       = topic.get("id", 0)
    affiliate_tools: list[str] = topic.get("affiliate_tools", [])
    tools_str = "、".join(affiliate_tools) if affiliate_tools else "各ツール"

    # 1) 画像を取得（AI生成 or Unsplash）
    img_url = _generate_ai_image(keyword, category, topic_id)

    # 2) Claude で記事本文を生成
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    user_prompt = USER_PROMPT_TEMPLATE.format(
        title=title, keyword=keyword, category=category, tools=tools_str
    )
    print(f"[INFO] 記事生成開始: {title}")

    response = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=8192,
        system=[{"type": "text", "text": SYSTEM_PROMPT,
                 "cache_control": {"type": "ephemeral"}}],
        messages=[{"role": "user", "content": user_prompt}],
    )
    content: str = response.content[0].text
    print(f"[INFO] 記事生成完了: {len(content)}文字")

    # 3) コードブロックマーカーを除去
    content = re.sub(r"^```html\s*\n?", "", content.strip())
    content = re.sub(r"\n?```\s*$", "",  content.strip())

    # 4) メタ説明を抽出（後で wp_insert_post の excerpt に使える）
    meta_m = re.search(r'<!--\s*META_DESCRIPTION:\s*(.+?)\s*-->', content)
    meta_description = meta_m.group(1).strip() if meta_m else title

    # 5) アフィリエイトプレースホルダーをボタンHTMLに置換
    tool_data = load_tool_data()
    content = replace_affiliate_placeholders(content, tool_data)

    # 6) セクション画像をH2の2番目の前に挿入（アイキャッチと異なる画像）
    h2_matches = list(re.finditer(r"<h2[^>]*>", content))
    if len(h2_matches) >= 2:
        pos = h2_matches[1].start()
        content = content[:pos] + _section_image_html(keyword, topic_id) + content[pos:]

    # 7) FAQ JSON-LD スキーマを抽出して末尾に追加
    faq_items = _extract_faq_items(content)
    faq_schema = _build_faq_schema(faq_items)

    # 8) Article JSON-LD スキーマ
    slug = re.sub(r'[^\w\-]', '-', keyword.lower())
    article_schema = _build_article_schema(title, slug, meta_description)

    # 9) アイキャッチ（ヒーローバナー）・ツール紹介カードを冒頭に追加し、スキーマを末尾に追加
    read_time    = _estimate_read_time(content)
    eyecatch     = _eyecatch_html(keyword, img_url, category=category, read_time=read_time)
    tool_overview = _tool_overview_html(affiliate_tools, tool_data)
    content = eyecatch + tool_overview + content + "\n" + article_schema + faq_schema

    return title, content, meta_description, img_url
