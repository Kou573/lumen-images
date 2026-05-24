from __future__ import annotations

import os
from dotenv import load_dotenv

load_dotenv()

ANTHROPIC_API_KEY: str = os.environ.get("ANTHROPIC_API_KEY", "")
WP_URL: str = os.environ.get("WP_URL", "")

def validate_affiliate_config() -> bool:
    """アフィリエイト投稿に必要な設定が揃っているか確認する。"""
    missing = []
    if not ANTHROPIC_API_KEY:
        missing.append("ANTHROPIC_API_KEY")
    if not WP_URL:
        missing.append("WP_URL")
    if missing:
        print(f"[ERROR] 必須環境変数が未設定です: {', '.join(missing)}")
        return False
    return True

def validate_note_config() -> bool:
    """note下書き生成に必要な設定が揃っているか確認する。"""
    if not ANTHROPIC_API_KEY:
        print("[ERROR] 必須環境変数が未設定です: ANTHROPIC_API_KEY")
        return False
    return True
