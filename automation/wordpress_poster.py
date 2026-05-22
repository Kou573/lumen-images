from __future__ import annotations

import base64
import json
import logging

import requests

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")


def _build_auth_header(username: str, app_password: str) -> str:
    """Basic認証ヘッダー値を生成する（ログに平文が出ないよう注意）。"""
    credentials = f"{username}:{app_password}"
    encoded = base64.b64encode(credentials.encode("utf-8")).decode("utf-8")
    return f"Basic {encoded}"


def post_article(
    title: str,
    content: str,
    tags: list[str] | None = None,
) -> dict:
    """
    WordPress REST API で記事を公開投稿する。

    Args:
        title:   記事タイトル
        content: HTML形式の本文
        tags:    タグ名のリスト（省略可）

    Returns:
        投稿成功時は WordPress API のレスポンス dict。
        失敗時は {"error": <message>} を返す（例外は出さない）。
    """
    from config import WP_APP_PASSWORD, WP_URL, WP_USERNAME

    if not all([WP_URL, WP_USERNAME, WP_APP_PASSWORD]):
        msg = "WordPress 接続設定（WP_URL / WP_USERNAME / WP_APP_PASSWORD）が未設定です。"
        logger.error(msg)
        return {"error": msg}

    base_url = WP_URL.rstrip("/")
    api_endpoint = f"{base_url}/wp-json/wp/v2/posts"

    headers = {
        "Authorization": _build_auth_header(WP_USERNAME, WP_APP_PASSWORD),
        "Content-Type": "application/json",
    }

    # タグIDの解決（タグ名→IDへの変換）
    tag_ids: list[int] = []
    if tags:
        tag_ids = _resolve_tag_ids(base_url, headers, tags)

    payload: dict = {
        "title": title,
        "content": content,
        "status": "publish",
    }
    if tag_ids:
        payload["tags"] = tag_ids

    logger.info("WordPress への投稿を開始します: %s", title)
    try:
        response = requests.post(
            api_endpoint,
            headers=headers,
            data=json.dumps(payload),
            timeout=30,
        )
        response.raise_for_status()
        result: dict = response.json()
        post_url = result.get("link", "（URL不明）")
        logger.info("投稿成功: %s", post_url)
        return result
    except requests.exceptions.HTTPError as e:
        logger.error("HTTP エラー: %s  レスポンス: %s", e, e.response.text if e.response else "")
        return {"error": str(e)}
    except requests.exceptions.ConnectionError as e:
        logger.error("接続エラー（WP_URL を確認してください）: %s", e)
        return {"error": str(e)}
    except requests.exceptions.Timeout:
        logger.error("タイムアウト: WordPress API が応答しませんでした。")
        return {"error": "timeout"}
    except Exception as e:
        logger.error("予期しないエラー: %s", e)
        return {"error": str(e)}


def _resolve_tag_ids(
    base_url: str,
    headers: dict,
    tag_names: list[str],
) -> list[int]:
    """
    タグ名のリストを WordPress タグ ID のリストに変換する。
    存在しないタグは新規作成する。
    """
    ids: list[int] = []
    for name in tag_names:
        try:
            # まず既存タグを検索
            resp = requests.get(
                f"{base_url}/wp-json/wp/v2/tags",
                headers=headers,
                params={"search": name},
                timeout=15,
            )
            resp.raise_for_status()
            existing = resp.json()
            matched = [t for t in existing if t.get("name") == name]
            if matched:
                ids.append(matched[0]["id"])
            else:
                # 新規作成
                create_resp = requests.post(
                    f"{base_url}/wp-json/wp/v2/tags",
                    headers=headers,
                    data=json.dumps({"name": name}),
                    timeout=15,
                )
                create_resp.raise_for_status()
                ids.append(create_resp.json()["id"])
        except Exception as e:
            logger.warning("タグ '%s' の解決に失敗しました（スキップ）: %s", name, e)
    return ids
