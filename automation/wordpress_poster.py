from __future__ import annotations

import logging
import re
import xmlrpc.client
from urllib.request import urlopen, Request
from urllib.error import URLError

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")


# ---------------------------------------------------------------------------
# Media upload helper
# ---------------------------------------------------------------------------

def _download_image(img_url: str) -> tuple[bytes, str]:
    """外部URLから画像バイト列と MIME タイプを取得する。"""
    headers = {"User-Agent": "Mozilla/5.0 (compatible; LumenBot/1.0)"}
    req = Request(img_url, headers=headers)
    with urlopen(req, timeout=20) as resp:
        data = resp.read()
        mime = resp.headers.get_content_type() or "image/jpeg"
    return data, mime


def upload_media_from_url(
    server: xmlrpc.client.ServerProxy,
    username: str,
    password: str,
    img_url: str,
    filename: str = "featured.jpg",
) -> int | None:
    """
    外部URLの画像を WordPress メディアライブラリにアップロードし、
    アタッチメント ID を返す。失敗時は None を返す。
    """
    try:
        image_data, mime = _download_image(img_url)
        media = {
            "name": filename,
            "type": mime,
            "bits": xmlrpc.client.Binary(image_data),
            "overwrite": False,
        }
        result = server.wp.uploadFile(1, username, password, media)
        attachment_id = int(result.get("id", 0))
        if attachment_id:
            logger.info(
                "画像アップロード成功: ID=%s  URL=%s",
                attachment_id, result.get("url", "")
            )
            return attachment_id
        logger.warning("uploadFile レスポンスに ID が含まれていません: %s", result)
        return None
    except (URLError, OSError) as e:
        logger.warning("画像ダウンロード失敗: %s", e)
        return None
    except Exception as e:
        logger.warning("画像アップロード失敗 (アイキャッチは記事本文内のものを使用): %s", e)
        return None


# ---------------------------------------------------------------------------
# Post helper
# ---------------------------------------------------------------------------

def post_article(
    title: str,
    content: str,
    tags: list[str] | None = None,
    featured_image_url: str | None = None,
    meta_description: str | None = None,
) -> dict:
    """
    WordPress に記事を投稿する。

    Parameters
    ----------
    title              : 記事タイトル
    content            : HTML 本文
    tags               : タグ文字列のリスト（省略可）
    featured_image_url : アイキャッチ画像の外部 URL（省略可）
    meta_description   : 抜粋テキスト（省略可）
    """
    from config import WP_URL, WP_USERNAME, WP_APP_PASSWORD

    if not all([WP_URL, WP_USERNAME, WP_APP_PASSWORD]):
        msg = "WP_URL / WP_USERNAME / WP_APP_PASSWORD が未設定です。"
        logger.error(msg)
        return {"error": msg}

    endpoint = f"{WP_URL.rstrip('/')}/xmlrpc.php"
    logger.info("WordPress XML-RPC 投稿開始: %s", title)

    try:
        server = xmlrpc.client.ServerProxy(endpoint)

        post_data: dict = {
            "post_title":   title,
            "post_content": content,
            "post_status":  "publish",
            "post_excerpt": meta_description or "",
        }

        if tags:
            post_data["terms_names"] = {"post_tag": tags}

        # ── アイキャッチ画像をアップロードして post_thumbnail に設定 ──
        if featured_image_url:
            logger.info("アイキャッチ画像をアップロード中...")
            safe_name = re.sub(r"[^\w\-]", "_", title[:40]) + ".jpg"
            attachment_id = upload_media_from_url(
                server,
                WP_USERNAME,
                WP_APP_PASSWORD,
                featured_image_url,
                filename=safe_name,
            )
            if attachment_id:
                post_data["post_thumbnail"] = attachment_id
                logger.info("アイキャッチ設定完了: attachment_id=%s", attachment_id)
            else:
                logger.info("アイキャッチのアップロードをスキップ（記事本文の冒頭画像を代用）")

        post_id = server.wp.newPost(1, WP_USERNAME, WP_APP_PASSWORD, post_data)
        logger.info("投稿成功: ID=%s", post_id)
        return {"id": post_id, "link": f"{WP_URL.rstrip('/')}/?p={post_id}"}

    except Exception as e:
        logger.error("XML-RPC エラー: %s", e)
        return {"error": str(e)}
