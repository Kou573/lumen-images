from __future__ import annotations

import logging

import requests

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")

AUTOPOST_SECRET = "glowlog_secret_2026"


def post_article(
    title: str,
    content: str,
    tags: list[str] | None = None,
) -> dict:
    from config import WP_URL

    if not WP_URL:
        msg = "WP_URL が未設定です。"
        logger.error(msg)
        return {"error": msg}

    api_endpoint = f"{WP_URL.rstrip('/')}/wp-json/autopost/v1/post"

    logger.info("WordPress への投稿を開始します: %s", title)
    try:
        response = requests.post(
            api_endpoint,
            data={"secret": AUTOPOST_SECRET, "title": title, "content": content},
            timeout=30,
        )
        response.raise_for_status()
        result: dict = response.json()
        logger.info("投稿成功: %s", result.get("link", "（URL不明）"))
        return result
    except requests.exceptions.HTTPError as e:
        logger.error("HTTP エラー: %s  レスポンス: %s", e, e.response.text if e.response else "")
        return {"error": str(e)}
    except requests.exceptions.ConnectionError as e:
        logger.error("接続エラー: %s", e)
        return {"error": str(e)}
    except requests.exceptions.Timeout:
        logger.error("タイムアウト")
        return {"error": "timeout"}
    except Exception as e:
        logger.error("予期しないエラー: %s", e)
        return {"error": str(e)}
