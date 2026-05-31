"""
既存投稿にアイキャッチ（featured image）を一括設定するバックフィルスクリプト。

WordPress REST API を使用して:
  1. アイキャッチ未設定の公開済み投稿を取得
  2. 記事本文の最初の <img src> URL を抽出
  3. 画像を WordPress メディアライブラリにアップロード
  4. 投稿の featured_media に設定

使い方:
  python automation/set_featured_images.py           # 全投稿を処理
  python automation/set_featured_images.py --limit 5 # 最大5件のみ処理
"""
from __future__ import annotations

import argparse
import base64
import json
import re
import sys
import time
from pathlib import Path
from urllib.request import urlopen, Request
from urllib.error import URLError

import requests

sys.path.insert(0, str(Path(__file__).parent))
from config import WP_URL, WP_USERNAME, WP_APP_PASSWORD

SLEEP_BETWEEN_POSTS = 3  # seconds


def _cred() -> str:
    return base64.b64encode(f"{WP_USERNAME}:{WP_APP_PASSWORD}".encode()).decode()


def _auth_headers() -> dict:
    return {"Authorization": f"Basic {_cred()}"}


def _get_posts_without_featured_image(limit: int | None = None) -> list[dict]:
    """アイキャッチ未設定の公開済み投稿を REST API で取得する。"""
    posts: list[dict] = []
    page = 1
    while True:
        resp = requests.get(
            f"{WP_URL.rstrip('/')}/wp-json/wp/v2/posts",
            headers=_auth_headers(),
            params={
                "page": page,
                "per_page": 20,
                "status": "publish",
                "_fields": "id,title,content,featured_media",
            },
            timeout=30,
        )
        if resp.status_code == 400:
            break
        resp.raise_for_status()
        batch = resp.json()
        if not batch:
            break
        for post in batch:
            if post.get("featured_media", 0) == 0:
                posts.append(post)
        if len(batch) < 20:
            break
        page += 1
        if limit and len(posts) >= limit:
            break
    return posts[:limit] if limit else posts


def _extract_first_image_url(content_html: str) -> str | None:
    """記事本文の最初の <img src> を返す。"""
    match = re.search(r'<img[^>]+src=["\']([^"\']+)["\']', content_html)
    return match.group(1) if match else None


def _download_image(img_url: str) -> tuple[bytes, str]:
    headers = {"User-Agent": "Mozilla/5.0 (compatible; LumenBot/1.0)"}
    req = Request(img_url, headers=headers)
    with urlopen(req, timeout=30) as resp:
        data = resp.read()
        mime = resp.headers.get_content_type() or "image/jpeg"
    return data, mime


def _upload_image(image_data: bytes, mime: str, filename: str) -> int | None:
    """画像を WordPress メディアライブラリにアップロードし attachment ID を返す。"""
    resp = requests.post(
        f"{WP_URL.rstrip('/')}/wp-json/wp/v2/media",
        headers={
            **_auth_headers(),
            "Content-Type": mime,
            "Content-Disposition": f'attachment; filename="{filename}"',
        },
        data=image_data,
        timeout=60,
    )
    resp.raise_for_status()
    attachment_id = resp.json().get("id")
    return int(attachment_id) if attachment_id else None


def _set_featured_media(post_id: int, attachment_id: int) -> bool:
    """投稿の featured_media を設定する。"""
    resp = requests.post(
        f"{WP_URL.rstrip('/')}/wp-json/wp/v2/posts/{post_id}",
        headers={**_auth_headers(), "Content-Type": "application/json"},
        json={"featured_media": attachment_id},
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json().get("featured_media") == attachment_id


def main() -> int:
    parser = argparse.ArgumentParser(description="アイキャッチ画像バックフィル")
    parser.add_argument("--limit", type=int, default=None,
                        help="処理する最大投稿数")
    args = parser.parse_args()

    print("=" * 60)
    print("[START] アイキャッチ画像バックフィル開始")
    print("=" * 60)

    if not all([WP_URL, WP_USERNAME, WP_APP_PASSWORD]):
        print("[ABORT] WP_URL / WP_USERNAME / WP_APP_PASSWORD が未設定です。")
        return 1

    print("[INFO] アイキャッチ未設定の投稿を取得中...")
    try:
        posts = _get_posts_without_featured_image(limit=args.limit)
    except Exception as e:
        print(f"[ERROR] 投稿の取得に失敗しました: {e}")
        return 1

    print(f"[INFO] 対象投稿数: {len(posts)} 件")
    if not posts:
        print("[INFO] 対象投稿はありません。処理終了。")
        return 0

    success_count = 0
    fail_count = 0
    results: list[dict] = []

    def _record(pid, title, stage, img_url=None, error=None):
        results.append({
            "id": pid, "title": title, "stage": stage,
            "img_url": img_url, "error": error,
        })

    for i, post in enumerate(posts):
        post_id = post["id"]
        title = post.get("title", {}).get("rendered", f"Post {post_id}")
        print(f"\n[{i+1}/{len(posts)}] ID={post_id}  {title}")

        # 記事本文から最初の画像URLを抽出
        content_html = post.get("content", {}).get("rendered", "")
        img_url = _extract_first_image_url(content_html)
        if not img_url:
            print("  [SKIP] 記事本文に画像URLが見つかりません")
            fail_count += 1
            _record(post_id, title, "no_image_in_content")
            continue
        print(f"  [INFO] 画像URL: {img_url[:80]}")

        # 画像ダウンロード
        try:
            image_data, mime = _download_image(img_url)
            print(f"  [OK] ダウンロード完了 ({len(image_data):,} bytes, {mime})")
        except (URLError, OSError) as e:
            print(f"  [ERROR] 画像ダウンロード失敗: {e}")
            fail_count += 1
            _record(post_id, title, "download_failed", img_url, str(e))
            continue

        # WordPress にアップロード
        # ファイル名は ASCII のみ（日本語を含むと HTTP ヘッダの latin-1 エンコードで失敗する）
        safe_name = (re.sub(r"[^a-zA-Z0-9_-]", "", title[:40]) or "featured") + ".jpg"
        try:
            attachment_id = _upload_image(image_data, mime, safe_name)
            if not attachment_id:
                print("  [ERROR] アップロード失敗: attachment_id が取得できませんでした")
                fail_count += 1
                _record(post_id, title, "upload_no_id", img_url)
                continue
            print(f"  [OK] アップロード完了: attachment_id={attachment_id}")
        except Exception as e:
            print(f"  [ERROR] アップロード失敗: {e}")
            fail_count += 1
            _record(post_id, title, "upload_failed", img_url, str(e))
            continue

        # アイキャッチに設定
        try:
            _set_featured_media(post_id, attachment_id)
            print("  [SUCCESS] アイキャッチ設定完了")
            success_count += 1
            _record(post_id, title, "success", img_url)
        except Exception as e:
            print(f"  [ERROR] アイキャッチ設定失敗: {e}")
            fail_count += 1
            _record(post_id, title, "set_featured_failed", img_url, str(e))

        if i < len(posts) - 1:
            time.sleep(SLEEP_BETWEEN_POSTS)

    out = Path("output/featured_images_result.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({
        "success": success_count, "fail": fail_count, "results": results,
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n[DONE] 成功 {success_count} / 失敗 {fail_count} → {out}")

    print("\n" + "=" * 60)
    print(f"完了: 成功={success_count}  失敗={fail_count}")
    print("=" * 60)
    return 0 if fail_count == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
