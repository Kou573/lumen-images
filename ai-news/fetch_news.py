#!/usr/bin/env python3
"""
AI News Daily Fetcher
過去24時間のOpenAI・Anthropic・Google AIニュースを収集してSlackに送信する
"""
import os
import sys
from datetime import datetime, timezone, timedelta
import requests
from bs4 import BeautifulSoup
import anthropic
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

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
SLACK_CHANNEL = "C0AU8RW9W94"


def fetch_page(name: str, url: str) -> str:
    try:
        r = requests.get(url, headers=HEADERS, timeout=15)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "lxml")
        # テキストを最大3000文字に絞る
        text = soup.get_text(separator="\n", strip=True)[:3000]
        return f"=== {name} ({url}) ===\n{text}\n"
    except Exception as e:
        print(f"[SKIP] {name}: {e}", file=sys.stderr)
        return f"=== {name} ({url}) ===\n[取得失敗: {e}]\n"


def summarize_with_claude(raw: str) -> str:
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    prompt = f"""今日は{TODAY_JST}です。以下の各AIニュースサイトから取得したコンテンツを分析し、
過去24時間以内の重要なAIニュースをSlack向けにまとめてください。

フォーマット:
- 見出しは太字（*見出し*）
- 各ニュースにソースURLを記載
- モデルリリース・API変更・障害情報は特に強調
- 開発者とビジネスユーザー双方に有益な情報を含める
- 古いニュースや24時間以上前の情報は除外
- 日本語で出力

--- コンテンツ ---
{raw[:12000]}
"""
    msg = client.messages.create(
        model="claude-sonnet-4-5",
        max_tokens=2000,
        messages=[{"role": "user", "content": prompt}]
    )
    return msg.content[0].text


def post_to_slack(text: str) -> None:
    client = WebClient(token=os.environ["SLACK_BOT_TOKEN"])
    header = f"*🤖 AI NEWS — {TODAY_JST}*\n\n"
    try:
        client.chat_postMessage(channel=SLACK_CHANNEL, text=header + text, mrkdwn=True)
        print("[OK] Slack送信完了")
    except SlackApiError as e:
        print(f"[ERROR] Slack送信失敗: {e}", file=sys.stderr)
        sys.exit(1)


def main():
    print(f"AI News fetching started: {TODAY_JST}")
    raw_contents = []
    for name, url in SOURCES:
        content = fetch_page(name, url)
        raw_contents.append(content)
        print(f"[OK] {name}")

    print("Claude で要約中...")
    summary = summarize_with_claude("\n".join(raw_contents))

    print("Slack に送信中...")
    post_to_slack(summary)
    print("完了")


if __name__ == "__main__":
    main()
