"""
サイト状態スナップショット（読み取り専用）
==========================================
GitHub Actions（サイトに到達できる環境）から glowlog.net の WordPress REST API を叩き、
各記事のアイキャッチ（featured_media）有無などを output/site_status.json に書き出す。

実行環境（このリポジトリを開く Claude のサンドボックス）からは glowlog.net へ
到達できないため、状態をリポジトリに「公開」しておくことで git 経由で確認可能にする。
"""
from __future__ import annotations

import base64
import datetime as _dt
import json
import os
import sys
from pathlib import Path

import requests

WP_URL = os.environ.get("WP_URL", "").rstrip("/")
WP_USER = os.environ.get("WP_USERNAME", "Lightlog")
WP_PW = os.environ.get("WP_APP_PASSWORD", "")
OUT = Path("output/site_status.json")


def main() -> int:
    if not WP_URL:
        print("[ERROR] WP_URL が未設定です。")
        return 1

    headers = {"User-Agent": "LumenStatus/1.0"}
    if WP_PW:
        token = base64.b64encode(f"{WP_USER}:{WP_PW}".encode("utf-8")).decode("ascii")
        headers["Authorization"] = f"Basic {token}"

    OUT.parent.mkdir(parents=True, exist_ok=True)

    try:
        resp = requests.get(
            f"{WP_URL}/wp-json/wp/v2/posts",
            headers=headers,
            params={
                "per_page": 50,
                "_fields": "id,title,featured_media,link,date",
                "orderby": "date",
                "order": "desc",
            },
            timeout=40,
        )
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        body = ""
        try:
            body = resp.text[:300]  # type: ignore[name-defined]
        except Exception:
            pass
        print(f"[ERROR] REST 取得失敗: {e} {body}")
        OUT.write_text(
            json.dumps({"error": f"{e} {body}", "fetched_at": _dt.datetime.utcnow().isoformat() + "Z"},
                       ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return 1

    posts = []
    for p in data:
        fm = p.get("featured_media", 0) or 0
        posts.append({
            "id": p.get("id"),
            "title": (p.get("title", {}) or {}).get("rendered", ""),
            "featured_media": fm,
            "has_thumbnail": bool(fm and fm > 0),
            "date": p.get("date"),
            "link": p.get("link"),
        })

    summary = {
        "fetched_at": _dt.datetime.utcnow().isoformat() + "Z",
        "total_posts": len(posts),
        "with_thumbnail": sum(1 for p in posts if p["has_thumbnail"]),
        "without_thumbnail": sum(1 for p in posts if not p["has_thumbnail"]),
        "posts": posts,
    }
    OUT.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[OK] {len(posts)}件 / サムネ有={summary['with_thumbnail']} 無={summary['without_thumbnail']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
