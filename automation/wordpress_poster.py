from __future__ import annotations

import base64
import logging
import re
import xmlrpc.client
from urllib.request import urlopen, Request
from urllib.error import URLError

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")


# ---------------------------------------------------------------------------
# Duplicate-post guard
# ---------------------------------------------------------------------------

def find_existing_post(
    server: xmlrpc.client.ServerProxy,
    username: str,
    password: str,
    title: str,
) -> str | None:
    """
    WordPress 上に同じタイトルの公開済み記事が存在するか検索する。
    見つかれば post_id（文字列）を返し、なければ None を返す。
    XML-RPC が利用できない環境ではログを出して None を返す（投稿続行）。
    """
    try:
        posts = server.wp.getPosts(
            1, username, password,
            {"search": title, "number": 10, "post_status": "publish"},
            ["post_id", "post_title"],
        )
        for post in posts:
            if post.get("post_title", "").strip() == title.strip():
                return str(post["post_id"])
    except Exception as e:
        logger.warning("既存記事の重複チェックに失敗しました（投稿は続行）: %s", e)
    return None


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


def upload_media_rest_api(
    wp_url: str,
    username: str,
    password: str,
    img_url: str,
    filename: str = "featured.jpg",
) -> int | None:
    """WordPress REST API 経由で画像をアップロードし attachment ID を返す。"""
    try:
        import requests as _requests
        image_data, mime = _download_image(img_url)
        cred = base64.b64encode(f"{username}:{password}".encode()).decode()
        resp = _requests.post(
            f"{wp_url.rstrip('/')}/wp-json/wp/v2/media",
            headers={
                "Authorization": f"Basic {cred}",
                "Content-Type": mime,
                "Content-Disposition": f'attachment; filename="{filename}"',
            },
            data=image_data,
            timeout=60,
        )
        resp.raise_for_status()
        attachment_id = resp.json().get("id")
        if attachment_id:
            logger.info("REST API 画像アップロード成功: ID=%s", attachment_id)
            return int(attachment_id)
        logger.warning("REST API レスポンスに ID がありません: %s", resp.text[:200])
        return None
    except (URLError, OSError) as e:
        logger.warning("画像ダウンロード失敗: %s", e)
        return None
    except Exception as e:
        logger.warning("REST API 画像アップロード失敗: %s", e)
        return None


def upload_media_from_url(
    server: xmlrpc.client.ServerProxy,
    username: str,
    password: str,
    img_url: str,
    filename: str = "featured.jpg",
    wp_url: str | None = None,
) -> int | None:
    """
    外部URLの画像を WordPress メディアライブラリにアップロードし、
    アタッチメント ID を返す。REST API を優先し、失敗時に XML-RPC へフォールバック。
    """
    # REST API を優先
    if wp_url:
        attachment_id = upload_media_rest_api(wp_url, username, password, img_url, filename)
        if attachment_id:
            return attachment_id
        logger.info("REST API 失敗 → XML-RPC にフォールバック")

    # XML-RPC フォールバック
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
                "XML-RPC 画像アップロード成功: ID=%s  URL=%s",
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

        # ── 重複投稿ガード：同タイトルの記事が既に存在すればスキップ ──
        existing_id = find_existing_post(server, WP_USERNAME, WP_APP_PASSWORD, title)
        if existing_id:
            logger.info(
                "同じタイトルの記事が WordPress に既に存在します (ID=%s)。"
                "重複投稿をスキップします。",
                existing_id,
            )
            return {
                "id":      existing_id,
                "skipped": True,
                "link":    f"{WP_URL.rstrip('/')}/?p={existing_id}",
            }

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
                wp_url=WP_URL,
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


# ---------------------------------------------------------------------------
# Update existing post
# ---------------------------------------------------------------------------

def update_article(
    post_id: str,
    title: str,
    content: str,
    featured_image_url: str | None = None,
    meta_description: str | None = None,
) -> dict:
    """
    既存の WordPress 記事を wp.editPost で上書き更新する。
    アイキャッチ画像も再アップロードして差し替える。
    """
    from config import WP_URL, WP_USERNAME, WP_APP_PASSWORD

    if not all([WP_URL, WP_USERNAME, WP_APP_PASSWORD]):
        msg = "WP_URL / WP_USERNAME / WP_APP_PASSWORD が未設定です。"
        logger.error(msg)
        return {"error": msg}

    endpoint = f"{WP_URL.rstrip('/')}/xmlrpc.php"
    logger.info("WordPress 記事更新開始: post_id=%s  title=%s", post_id, title)

    try:
        server = xmlrpc.client.ServerProxy(endpoint)

        post_data: dict = {
            "post_content": content,
            "post_excerpt": meta_description or "",
        }

        if featured_image_url:
            logger.info("アイキャッチ画像をアップロード中...")
            safe_name = re.sub(r"[^\w\-]", "_", title[:40]) + "_updated.jpg"
            attachment_id = upload_media_from_url(
                server, WP_USERNAME, WP_APP_PASSWORD,
                featured_image_url, filename=safe_name,
                wp_url=WP_URL,
            )
            if attachment_id:
                post_data["post_thumbnail"] = attachment_id
                logger.info("アイキャッチ更新完了: attachment_id=%s", attachment_id)

        success = server.wp.editPost(1, WP_USERNAME, WP_APP_PASSWORD, post_id, post_data)
        if success:
            logger.info("記事更新成功: post_id=%s", post_id)
            return {"id": post_id, "link": f"{WP_URL.rstrip('/')}/?p={post_id}"}
        return {"error": f"wp.editPost returned False for post_id={post_id}"}

    except Exception as e:
        logger.error("XML-RPC エラー: %s", e)
        return {"error": str(e)}
