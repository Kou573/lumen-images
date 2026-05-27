#!/usr/bin/env python3
"""
AI News Raw Fetcher - 生データ取得のみ（Claude呼び出しなし）
"""
import sys
from datetime import datetime, timezone, timedelta
import requests
from bs4 import BeautifulSoup

JST = timezone(timedelta(hours=9))
TODAY_JST = datetime.now(JST).strftime("%Y年%m月%d日")

SOURCES = [
    ("OpenAI News",       "https://openai.com/news/"),
    ("Anthropic News",    "https://www.anthropic.com/news"),
    ("Google AI Blog",    "https://blog.google/technology/ai/"),
    ("DeepMind Blog",     "https://deepmind.google/blog/"),
    ("TechCrunch AI",     "https://techcrunch.com/category/artificial-intelligence/"),
    ("The Verge AI",      "https://www.theverge.com/ai-artificial-intelligence"),
    ("VentureBeat AI",    "https://venturebeat.com/ai/"),
    ("Anthropic API RN",  "https://docs.anthropic.com/en/release-notes/overview"),
    ("OpenAI Changelog",  "https://platform.openai.com/docs/changelog"),
    ("Gemini Changelog",  "https://ai.google.dev/gemini-api/docs/changelog"),
]

HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; LumenNewsBot/1.0)"}


def fetch_page(name, url):
    try:
        r = requests.get(url, headers=HEADERS, timeout=15)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "lxml")
        text = soup.get_text(separator="\n", strip=True)[:3000]
        return f"=== {name} ({url}) ===\n{text}\n"
    except Exception as e:
        print(f"[SKIP] {name}: {e}", file=sys.stderr)
        return f"=== {name} ({url}) ===\n[取得失敗]\n"


if __name__ == "__main__":
    print(f"DATE: {TODAY_JST}")
    for name, url in SOURCES:
        print(fetch_page(name, url))
