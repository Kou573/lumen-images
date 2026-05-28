"""
WordPress 投稿スクリプト（重複防止付き）

このスクリプトは GitHub Actions ワークフローで
  git commit + git push（記事データのコミット）
の成功後にのみ実行される。

重複投稿防止の二重構造:
  1. latest.json の wp_post_id フィールドが設定済みであればスキップ
  2. WordPress 側で同タイトル記事が存在すればスキップ（find_existing_post）
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from config import validate_affiliate_config
from wordpress_poster import post_article

LATEST_JSON = Path(__file__).parent.parent / "articles" / "latest.json"


def _load_latest() -> dict | None:
    if not LATEST_JSON.exists():
        print("[ERROR] articles/latest.json が見つかりません。")
        return None
    with LATEST_JSON.open(encoding="utf-8") as f:
        return json.load(f)


def _save_wp_post_id(data: dict, post_id: str) -> None:
    """wp_post_id を latest.json に書き戻す。"""
    data["wp_post_id"] = post_id
    LATEST_JSON.write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def _git_commit_and_push(post_id: str, title: str) -> bool:
    """wp_post_id を記録した latest.json を git push する。"""
    try:
        subprocess.run(
            ["git", "config", "user.email", "action@github.com"], check=True
        )
        subprocess.run(
            ["git", "config", "user.name", "GitHub Actions"], check=True
        )
        subprocess.run(
            ["git", "add", str(LATEST_JSON)], check=True
        )
        result = subprocess.run(
            ["git", "diff", "--staged", "--quiet"], capture_output=True
        )
        if result.returncode == 0:
            print("[INFO] wp_post_id の変更なし。コミットをスキップします。")
            return True
        subprocess.run(
            ["git", "commit", "-m",
             f"Record wp_post_id={post_id} for '{title[:40]}' [skip ci]"],
            check=True,
        )
        subprocess.run(["git", "push"], check=True)
        print(f"[INFO] wp_post_id={post_id} を latest.json にコミットしました。")
        return True
    except subprocess.CalledProcessError as e:
        print(f"[WARN] wp_post_id のコミット/プッシュに失敗しました: {e}")
        return False


def main() -> int:
    print("=" * 60)
    print("[START] WordPress 投稿を開始します（重複チェック付き）")
    print("=" * 60)

    from config import WP_APP_PASSWORD
    if not validate_affiliate_config():
        print("[ABORT] 設定が不完全なため処理を中断します。")
        return 1

    if not WP_APP_PASSWORD:
        print("[ABORT] WP_APP_PASSWORD が未設定です。WordPress への投稿をスキップします。")
        return 0

    data = _load_latest()
    if data is None:
        return 1

    title = data.get("title", "")
    if not title:
        print("[ERROR] latest.json にタイトルがありません。")
        return 1

    # ── 重複チェック①: latest.json に既に wp_post_id が設定されている ──
    existing_wp_id = data.get("wp_post_id")
    if existing_wp_id:
        print(f"[SKIP] この記事は既に WordPress に投稿済みです (wp_post_id={existing_wp_id})。")
        print(f"[SKIP] タイトル: {title}")
        return 0

    # ── WordPress へ投稿（wordpress_poster が重複チェック②を内部で実施） ──
    result = post_article(
        title=title,
        content=data.get("content", ""),
        featured_image_url=data.get("featured_image_url"),
        meta_description=data.get("meta_description"),
        tags=data.get("affiliate_tools", []),
    )

    if "error" in result:
        print(f"[ERROR] WordPress 投稿に失敗しました: {result['error']}")
        return 1

    post_id = str(result["id"])

    if result.get("skipped"):
        print(f"[SKIP] 重複記事のため投稿をスキップしました (wp_post_id={post_id})")
    else:
        print(f"[SUCCESS] WordPress 投稿完了: {result.get('link', '')}")

    # ── wp_post_id を latest.json に記録して git push ──
    _save_wp_post_id(data, post_id)
    _git_commit_and_push(post_id, title)

    print("=" * 60)
    return 0


if __name__ == "__main__":
    sys.exit(main())
