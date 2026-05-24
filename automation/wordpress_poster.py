from __future__ import annotations

import logging
import xmlrpc.client

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")


def post_article(title: str, content: str, tags: list[str] | None = None) -> dict:
    from config import WP_URL, WP_USERNAME, WP_APP_PASSWORD

    if not all([WP_URL, WP_USERNAME, WP_APP_PASSWORD]):
        msg = "WP_URL / WP_USERNAME / WP_APP_PASSWORD が未設定です。"
        logger.error(msg)
        return {"error": msg}

    endpoint = f"{WP_URL.rstrip('/')}/xmlrpc.php"
    logger.info("WordPress XML-RPC投稿開始: %s", title)

    try:
        server = xmlrpc.client.ServerProxy(endpoint)
        post_data = {
            "post_title": title,
            "post_content": content,
            "post_status": "publish",
        }
        post_id = server.wp.newPost(1, WP_USERNAME, WP_APP_PASSWORD, post_data)
        logger.info("投稿成功: ID=%s", post_id)
        return {"id": post_id, "link": f"{WP_URL.rstrip('/')}/?p={post_id}"}
    except Exception as e:
        logger.error("XML-RPC エラー: %s", e)
        return {"error": str(e)}
