#!/usr/bin/env python3
"""Slack投稿スクリプト - 標準入力またはファイルからテキストを受け取って投稿"""
import os
import sys
from datetime import datetime, timezone, timedelta
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

JST = timezone(timedelta(hours=9))
TODAY_JST = datetime.now(JST).strftime("%Y年%m月%d日")
SLACK_CHANNEL = "C0AU8RW9W94"

def main():
    text = sys.stdin.read().strip()
    if not text:
        print("ERROR: no input", file=sys.stderr)
        sys.exit(1)

    client = WebClient(token=os.environ["SLACK_BOT_TOKEN"])
    header = f"*🤖 AI NEWS — {TODAY_JST}*\n\n"
    try:
        client.chat_postMessage(channel=SLACK_CHANNEL, text=header + text, mrkdwn=True)
        print("[OK] Slack送信完了")
    except SlackApiError as e:
        print(f"[ERROR] {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
