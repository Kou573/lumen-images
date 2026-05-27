"""
Affiliate article generator with SEO / AIO / LLMO optimisations.

AIO  = AI Overview (Google のAI概要) 対策
LLMO = LLM Optimisation (ChatGPT・Perplexity 等に引用されやすい構造)
SEO  = 従来の検索エンジン最適化

Design: Claude-inspired UI — warm whites, coral/amber accents, clean cards
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
# Claude-inspired design system (CSS)
# ---------------------------------------------------------------------------

ARTICLE_CSS = """\
<style>
/* ===== Lightlog Article — Claude Design System ===== */

/* Base */
.lg {
  font-family: 'Hiragino Kaku Gothic ProN', 'Noto Sans JP', 'Yu Gothic Medium',
               'YuGothic', 'Meiryo', sans-serif;
  color: #1c1917;
  line-height: 1.9;
  font-size: 16px;
  background: #fafaf8;
}

/* Headings */
.lg h1 {
  font-size: 28px;
  font-weight: 800;
  color: #0f172a;
  line-height: 1.45;
  margin: 8px 0 24px;
  letter-spacing: -0.3px;
}
.lg h2 {
  font-size: 21px;
  font-weight: 700;
  color: #0f172a;
  margin: 52px 0 20px;
  padding: 12px 18px;
  background: #fffbf5;
  border-left: 4px solid #d97706;
  border-radius: 0 8px 8px 0;
  box-shadow: 0 1px 4px rgba(217,119,6,0.08);
}
.lg h3 {
  font-size: 17px;
  font-weight: 700;
  color: #1e3a5f;
  margin: 28px 0 12px;
  padding-left: 14px;
  border-left: 3px solid #fb923c;
  line-height: 1.5;
}

/* Paragraph */
.lg p {
  margin-bottom: 1.5em;
  line-height: 1.9;
}

/* Lead paragraph */
.lg .lg-lead {
  font-size: 15.5px;
  color: #44403c;
  line-height: 1.95;
  padding: 4px 0;
}

/* Summary "この記事でわかること" */
.lg .lg-know {
  background: linear-gradient(135deg, #fffbeb 0%, #fff7ed 100%);
  border: 1px solid #fed7aa;
  border-left: 4px solid #f97316;
  border-radius: 12px;
  padding: 22px 26px;
  margin: 32px 0;
}
.lg .lg-know-title {
  font-size: 13px;
  font-weight: 700;
  color: #c2410c;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  margin: 0 0 12px;
  display: flex;
  align-items: center;
  gap: 6px;
}
.lg .lg-know-title::before {
  content: '📋';
  font-size: 15px;
}
.lg .lg-know ul {
  margin: 0;
  padding: 0 0 0 20px;
  list-style: none;
}
.lg .lg-know ul li {
  position: relative;
  padding: 4px 0 4px 8px;
  color: #292524;
  font-size: 15px;
  line-height: 1.7;
}
.lg .lg-know ul li::before {
  content: '✓';
  position: absolute;
  left: -14px;
  color: #f97316;
  font-weight: 700;
}

/* Point box (H2直下サマリー) */
.lg .summary-box {
  background: #f0f9ff;
  border: 1px solid #bae6fd;
  border-left: 4px solid #0ea5e9;
  border-radius: 8px;
  padding: 14px 18px;
  margin: 16px 0 24px;
  font-size: 14px;
  line-height: 1.75;
  color: #0c4a6e;
}
.lg .summary-box strong {
  color: #0284c7;
}

/* Affiliate CTA card */
.lg .lg-cta {
  background: linear-gradient(135deg, #fff7ed 0%, #fffbf5 60%, #fef3c7 100%);
  border: 1px solid #fed7aa;
  border-radius: 16px;
  padding: 28px 32px;
  margin: 40px 0;
  box-shadow: 0 4px 20px rgba(249,115,22,0.10);
  text-align: center;
}
.lg .lg-cta-badge {
  display: inline-block;
  background: #fff4ed;
  border: 1px solid #fdba74;
  color: #ea580c;
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.08em;
  padding: 3px 10px;
  border-radius: 100px;
  margin-bottom: 12px;
  text-transform: uppercase;
}
.lg .lg-cta-title {
  font-size: 17px;
  font-weight: 700;
  color: #1c1917;
  margin: 0 0 6px;
}
.lg .lg-cta-sub {
  font-size: 13px;
  color: #78716c;
  margin: 0 0 18px;
}
.lg .lg-cta-btn {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 14px 36px;
  background: linear-gradient(135deg, #f97316 0%, #ea580c 100%);
  color: #ffffff !important;
  font-weight: 700;
  font-size: 16px;
  text-decoration: none !important;
  border-radius: 100px;
  box-shadow: 0 4px 14px rgba(249,115,22,0.35);
  transition: box-shadow 0.2s, transform 0.2s;
  letter-spacing: 0.02em;
}
.lg .lg-cta-btn:hover {
  box-shadow: 0 6px 20px rgba(249,115,22,0.45);
  transform: translateY(-1px);
}
.lg .lg-cta-btn::after {
  content: '→';
  font-size: 18px;
}
.lg .lg-cta-note {
  font-size: 11px;
  color: #a8a29e;
  margin: 12px 0 0;
}

/* Table */
.lg table {
  width: 100%;
  border-collapse: collapse;
  margin: 28px 0;
  border-radius: 12px;
  overflow: hidden;
  box-shadow: 0 2px 12px rgba(0,0,0,0.07);
  font-size: 14px;
}
.lg table thead tr th {
  background: #0f172a;
  color: #f8fafc;
  padding: 13px 16px;
  text-align: left;
  font-weight: 700;
  font-size: 13px;
  letter-spacing: 0.04em;
  border: none;
}
.lg table tbody tr:nth-child(odd) td {
  background: #ffffff;
}
.lg table tbody tr:nth-child(even) td {
  background: #f8fafc;
}
.lg table tbody tr:hover td {
  background: #fff7ed;
  transition: background 0.15s;
}
.lg table td {
  padding: 12px 16px;
  border-bottom: 1px solid #f1f5f9;
  color: #334155;
  vertical-align: top;
  line-height: 1.6;
}

/* FAQ */
.lg dl.lg-faq {
  margin: 16px 0;
}
.lg dl.lg-faq dt {
  background: #0f172a;
  color: #f8fafc;
  padding: 14px 20px 14px 52px;
  border-radius: 8px 8px 0 0;
  font-weight: 700;
  font-size: 15px;
  line-height: 1.6;
  position: relative;
  margin-top: 16px;
}
.lg dl.lg-faq dt::before {
  content: 'Q';
  position: absolute;
  left: 16px;
  top: 50%;
  transform: translateY(-50%);
  background: #f97316;
  color: #fff;
  width: 24px;
  height: 24px;
  border-radius: 6px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 13px;
  font-weight: 800;
  line-height: 24px;
  text-align: center;
}
.lg dl.lg-faq dd {
  background: #ffffff;
  border: 1px solid #e2e8f0;
  border-top: none;
  border-radius: 0 0 8px 8px;
  padding: 16px 20px 16px 52px;
  margin: 0;
  font-size: 14.5px;
  line-height: 1.8;
  color: #334155;
  position: relative;
}
.lg dl.lg-faq dd::before {
  content: 'A';
  position: absolute;
  left: 16px;
  top: 18px;
  background: #0ea5e9;
  color: #fff;
  width: 24px;
  height: 24px;
  border-radius: 6px;
  font-size: 13px;
  font-weight: 800;
  line-height: 24px;
  text-align: center;
}

/* List items */
.lg ul, .lg ol {
  padding-left: 24px;
  margin: 12px 0 20px;
}
.lg ul li, .lg ol li {
  margin-bottom: 8px;
  line-height: 1.8;
  color: #292524;
}
.lg ul li::marker {
  color: #f97316;
}

/* Highlight / strong */
.lg strong {
  color: #0f172a;
  font-weight: 700;
}

/* Section separator */
.lg .lg-section-img {
  border-radius: 12px;
  overflow: hidden;
  margin: 36px 0;
  box-shadow: 0 4px 20px rgba(0,0,0,0.10);
}
.lg .lg-section-img img {
  width: 100%;
  height: auto;
  display: block;
  max-width: 720px;
}

/* Eyecatch */
.lg .lg-eyecatch {
  border-radius: 14px;
  overflow: hidden;
  margin: 0 0 36px;
  box-shadow: 0 6px 28px rgba(0,0,0,0.12);
  line-height: 0;
}
.lg .lg-eyecatch img {
  width: 100%;
  height: auto;
  display: block;
  aspect-ratio: 16/9;
  object-fit: cover;
}

/* Responsive */
@media (max-width: 640px) {
  .lg h1 { font-size: 22px; }
  .lg h2 { font-size: 18px; padding: 10px 14px; }
  .lg h3 { font-size: 16px; }
  .lg .lg-cta { padding: 20px 18px; }
  .lg .lg-cta-btn { font-size: 14px; padding: 12px 24px; }
  .lg table { font-size: 12px; }
  .lg table td, .lg table th { padding: 9px 10px; }
}
</style>
"""


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
# Affiliate CTA button — Claude design
# ---------------------------------------------------------------------------

def _build_affiliate_html(tool_name: str, tool_data: dict) -> str:
    entry = tool_data.get(tool_name)
    url   = entry["official_url"] if entry else (
        "https://www.google.com/search?q=" + urllib.parse.quote(f"{tool_name} 公式サイト")
    )
    safe = tool_name.replace("'", "\\'")
    return (
        '<div class="lg-cta">'
        '<span class="lg-cta-badge">PR / Sponsored</span>'
        f'<p class="lg-cta-title">{tool_name} を無料で試してみる</p>'
        f'<p class="lg-cta-sub">公式サイトで最新プランと料金を確認できます</p>'
        f'<a href="{url}" target="_blank" rel="noopener noreferrer sponsored"'
        f' class="lg-cta-btn"'
        f' onclick="if(typeof gtag!==\'undefined\'){{gtag(\'event\',\'tool_click\','
        f'{{\'tool_name\':\'{safe}\',\'event_category\':\'affiliate\'}})}}">'
        f'{tool_name} 公式サイトを見る'
        f'</a>'
        '<p class="lg-cta-note">※ 本リンクには広告が含まれます</p>'
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
            "Warm amber and white color palette. 16:9 ratio composition."
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


def _eyecatch_html(keyword: str, img_url: str) -> str:
    alt = keyword.replace('"', "&quot;")
    return (
        f'<figure class="lg-eyecatch">'
        f'<img src="{img_url}" alt="{alt}" loading="eager" width="1200" height="675">'
        f'</figure>\n'
    )


def _section_image_html(keyword: str, topic_id: int) -> str:
    """
    セクション画像はアイキャッチと異なる Unsplash フォトを使う。
    topic_id + 1000 を sig に使うことでアイキャッチ（sig=topic_id）と別の画像になる。
    """
    alt = keyword.replace('"', "&quot;") + " 活用イメージ"
    base = "https://images.unsplash.com/photo-1522071820081-009f0129c71c?w=800&auto=format&fit=crop"
    url  = f"{base}&sig={topic_id + 1000}"
    return (
        f'<div class="lg-section-img">'
        f'<img src="{url}" alt="{alt}" loading="lazy" width="800" height="450">'
        f'</div>\n'
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
# System prompts (SEO / AIO / LLMO 対応 + Claude design)
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = """\
あなたは日本のSEO・AIO・LLMOに精通したアフィリエイトライターです。
下記のルールに従って記事を作成してください。

【デザインシステム（重要）】
- 記事全体を <div class="lg"> で囲む
- h1〜h3 タグにはクラスや style を追加しない（CSSが自動で適用される）
- 「この記事でわかること」ボックスは <div class="lg-know"> を使う
- H2直下の要点ボックスは <div class="summary-box"> を使う（style不要）
- FAQ は <dl class="lg-faq"> 形式で書く
- テーブルは class="lg-table" を付ける
- CTAプレースホルダー <!-- AFFILIATE_LINK: ツール名 --> はそのまま記述
- <p> タグに style は不要（CSSで制御済み）
- inline style は原則使わない（デザインシステムのCSSに任せる）

【SEO対策】
- メインキーワードはタイトル・H1・最初のpタグ・まとめに必ず含める
- LSIキーワード（関連語）を本文全体に自然に散りばめる
- H2 → H3 の階層を正しく守る

【AIO対策（Google AI Overview / AI概要）】
- 各H2直下に40〜60字の「要点ボックス」 <div class="summary-box"> を置く
- 冒頭の「この記事でわかること」で記事の結論を先出しする
- 「よくある質問」セクションは <dl class="lg-faq"><dt><dd> 形式で 4〜5 Q&A を書く
- 数字・固有名詞・料金・日付を積極的に使い、AI が引用しやすい事実ベースの文章にする

【LLMO対策（ChatGPT・Perplexity 等への最適化）】
- 「結論→理由→根拠→具体例」の PREP 構造で各セクションを書く
- ツール名・会社名・料金・機能を箇条書きで明示する
- 比較テーブルに ○△× や 具体的数値 を入れる
- 「〜によると」「〜のデータでは」など引用フレーズを使う（事実ベース）

【その他ルール】
- 記事中の年号は2026年（2025年最新は書かない）
- <!-- AFFILIATE_LINK: ツール名 --> は記事全体で厳密に2箇所のみ
  （1つ目は導入文の直後、2つ目はまとめセクションの末尾）
- <html><body><head>タグは不要、記事本文のみ
- コードブロック（\`\`\`）は使わない\
"""

USER_PROMPT_TEMPLATE = """\
以下のトピックで、SEO・AIO・LLMOに最適化されたアフィリエイト記事を書いてください。

タイトル: {title}
メインキーワード: {keyword}
カテゴリ: {category}
紹介ツール: {tools}
メタ説明（140字以内）: ← 記事の冒頭コメントに <!-- META_DESCRIPTION: ... --> として埋め込む

【必須構成】（※全体を <div class="lg"> で囲むこと）

1. <!-- META_DESCRIPTION: 140字以内のメタ説明 -->（コメントとして冒頭）
2. <div class="lg"> ← 開始タグ
3. <h1> タイトル
4. 「この記事でわかること」ボックス（下記テンプレート参照）
5. 導入文 350字以上（読者の悩みを具体的に提示）
6. CTAプレースホルダー <!-- AFFILIATE_LINK: ツール名 -->
7. H2 × 4〜5個（各H2直下に要点ボックス）
8. 料金・機能比較テーブル（class="lg-table" を付ける）
9. <h2>よくある質問</h2>（<dl class="lg-faq"> 形式で 4〜5 Q&A）
10. <h2>まとめ</h2>（結論と強いCTAを含む）
11. CTAプレースホルダー <!-- AFFILIATE_LINK: ツール名 -->
12. </div> ← 終了タグ
13. 合計 2,200〜2,800字（日本語）

【この記事でわかること ボックス テンプレート】
<div class="lg-know">
  <p class="lg-know-title">この記事でわかること</p>
  <ul>
    <li>ポイント1</li>
    <li>ポイント2</li>
    <li>ポイント3</li>
  </ul>
</div>

【要点ボックス テンプレート（H2直下）】
<div class="summary-box"><strong>ポイント：</strong>テキスト（40〜60字）</div>

【比較テーブル テンプレート】
<table class="lg-table">
  <thead><tr>
    <th>項目</th>
    <th>プランA</th>
    <th>プランB</th>
  </tr></thead>
  <tbody>
    <tr><td>料金</td><td>無料</td><td>月額2,980円</td></tr>
  </tbody>
</table>

【よくある質問 テンプレート】
<dl class="lg-faq">
  <dt>質問1</dt>
  <dd>回答1</dd>
  <dt>質問2</dt>
  <dd>回答2</dd>
</dl>\
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
    - Claude-design inspired HTML (warm whites × coral accent)
    - SEO / AIO / LLMO optimised structure
    - AI-generated or Unsplash eyecatch image
    - JSON-LD Article + FAQ schema
    - Affiliate CTA buttons
    """
    from config import ANTHROPIC_API_KEY

    title:           str       = topic["title"]
    keyword:         str       = topic.get("keyword", title)
    category:        str       = topic.get("category", "")
    topic_id:        int       = topic.get("id", 0)
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

    # 9) CSS + アイキャッチ画像を冒頭に追加し、スキーマを末尾に追加
    eyecatch = _eyecatch_html(keyword, img_url)
    content = ARTICLE_CSS + eyecatch + content + "\n" + article_schema + faq_schema

    return title, content, meta_description, img_url
