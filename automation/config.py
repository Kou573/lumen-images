from __future__ import annotations

import os
from dotenv import load_dotenv

load_dotenv()

ANTHROPIC_API_KEY: str = os.environ.get("ANTHROPIC_API_KEY", "")
OPENAI_API_KEY:    str = os.environ.get("OPENAI_API_KEY", "")
WP_URL:            str = os.environ.get("WP_URL", "")
WP_USERNAME:       str = os.environ.get("WP_USERNAME", "Lightlog")
WP_APP_PASSWORD:   str = os.environ.get("WP_APP_PASSWORD", "")


def validate_affiliate_config() -> bool:
    missing = []
    if not ANTHROPIC_API_KEY:
        missing.append("ANTHROPIC_API_KEY")
    if not WP_URL:
        missing.append("WP_URL")
    if not WP_APP_PASSWORD:
        missing.append("WP_APP_PASSWORD")
    if missing:
        print(f"[ERROR] 必須環境変数が未設定です: {', '.join(missing)}")
        return False
    return True


def validate_note_config() -> bool:
    if not ANTHROPIC_API_KEY:
        print("[ERROR] 必須環境変数が未設定です: ANTHROPIC_API_KEY")
        return False
    return True
