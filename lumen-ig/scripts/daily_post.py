#!/usr/bin/env python3
"""
Lumen IG Daily Post Script
Instagram Graph API + Cloudinary を使って1日1枚投稿する。

Usage:
    python daily_post.py --caption-file /tmp/caption.txt --concept-note "今日のコンセプト"
"""

import argparse
import datetime
import json
import os
import sys
import time
from pathlib import Path

import requests

try:
    import cloudinary
    import cloudinary.uploader
except ImportError:
    print("[FATAL] cloudinary not installed. pip install cloudinary", flush=True)
    sys.exit(1)


# ---------------------------------------------------------------------------
# 設定（環境変数から取得）
# ---------------------------------------------------------------------------
IG_USER_ID    = os.environ.get("IG_USER_ID", "")
IG_ACCESS_TOKEN = os.environ.get("IG_ACCESS_TOKEN", "")
IG_GRAPH_BASE = os.environ.get("IG_GRAPH_BASE", "https://graph.instagram.com")
CLOUD_NAME    = os.environ.get("CLOUDINARY_CLOUD_NAME", "")
CLOUD_API_KEY = os.environ.get("CLOUDINARY_API_KEY", "")
CLOUD_SECRET  = os.environ.get("CLOUDINARY_API_SECRET", "")
HF_TOKEN      = os.environ.get("HF_TOKEN", "")


def configure_cloudinary():
    cloudinary.config(
        cloud_name=CLOUD_NAME,
        api_key=CLOUD_API_KEY,
        api_secret=CLOUD_SECRET,
    )


# ---------------------------------------------------------------------------
# 画像取得 (キュー → HF FLUX → Pollinations)
# ---------------------------------------------------------------------------
def get_image_from_queue(queue_dir: Path):
    """images/queue/ の最古ファイルを返す。なければ None。"""
    exts = ("*.jpg", "*.jpeg", "*.png", "*.webp")
    images = []
    for ext in exts:
        images.extend(sorted(queue_dir.glob(ext)))
    if not images:
        return None
    return images[0]


def generate_with_hf(concept: str) -> bytes | None:
    """HF FLUX schnell で縦長画像を生成して bytes を返す。失敗なら None。"""
    if not HF_TOKEN:
        print("[INFO] HF_TOKEN not set, skipping HF generation", flush=True)
        return None

    prompt = (
        f"cinematic vertical portrait, {concept}, moody atmosphere, "
        "dark background, ultra-detailed, 4K, 9:16 aspect ratio, photorealistic"
    )
    url = "https://api-inference.huggingface.co/models/black-forest-labs/FLUX.1-schnell"
    headers = {"Authorization": f"Bearer {HF_TOKEN}"}

    print(f"[INFO] HF FLUX: {prompt[:60]}...", flush=True)
    try:
        resp = requests.post(url, headers=headers, json={"inputs": prompt}, timeout=120)
        ct = resp.headers.get("content-type", "")
        if resp.status_code == 200 and ct.startswith("image"):
            print(f"[OK] HF FLUX generated ({len(resp.content)//1024}KB)", flush=True)
            return resp.content
        else:
            print(f"[WARN] HF FLUX {resp.status_code}: {resp.text[:120]}", flush=True)
    except Exception as e:
        print(f"[WARN] HF FLUX exception: {e}", flush=True)
    return None


def generate_with_pollinations(concept: str) -> bytes | None:
    """Pollinations.ai で縦長画像を生成して bytes を返す。"""
    from urllib.parse import quote
    prompt_str = f"cinematic portrait {concept} moody dark atmosphere vertical art"
    encoded = quote(prompt_str)
    url = f"https://image.pollinations.ai/prompt/{encoded}?width=1080&height=1350&nologo=true"

    print(f"[INFO] Pollinations: {prompt_str[:60]}...", flush=True)
    try:
        resp = requests.get(url, timeout=90)
        if resp.status_code == 200 and len(resp.content) > 10_000:
            print(f"[OK] Pollinations generated ({len(resp.content)//1024}KB)", flush=True)
            return resp.content
        else:
            print(f"[WARN] Pollinations {resp.status_code}", flush=True)
    except Exception as e:
        print(f"[WARN] Pollinations exception: {e}", flush=True)
    return None


def upload_to_cloudinary(source) -> str | None:
    """ファイルパス(str/Path) または bytes を Cloudinary にアップロードして URL を返す。"""
    try:
        configure_cloudinary()
        if isinstance(source, (str, Path)):
            result = cloudinary.uploader.upload(str(source), folder="lumen-ig")
        else:
            result = cloudinary.uploader.upload(source, folder="lumen-ig",
                                                resource_type="image")
        url = result["secure_url"]
        print(f"[OK] Cloudinary: {url}", flush=True)
        return url
    except Exception as e:
        print(f"[WARN] Cloudinary upload failed: {e}", flush=True)
        return None


# ---------------------------------------------------------------------------
# Instagram Graph API
# ---------------------------------------------------------------------------
def ig_create_container(image_url: str, caption: str) -> str | None:
    """メディアコンテナを作成して creation_id を返す。"""
    url = f"{IG_GRAPH_BASE}/{IG_USER_ID}/media"
    params = {
        "image_url": image_url,
        "caption": caption,
        "access_token": IG_ACCESS_TOKEN,
    }
    try:
        resp = requests.post(url, params=params, timeout=30)
        data = resp.json()
        cid = data.get("id")
        if cid:
            print(f"[OK] IG container created: {cid}", flush=True)
            return cid
        else:
            print(f"[FAIL] IG container error: {data}", flush=True)
            return None
    except Exception as e:
        print(f"[FAIL] IG container exception: {e}", flush=True)
        return None


def ig_wait_for_container(creation_id: str, max_wait: int = 60) -> bool:
    """コンテナのステータスが FINISHED になるまで待つ。"""
    url = f"{IG_GRAPH_BASE}/{creation_id}"
    params = {"fields": "status_code", "access_token": IG_ACCESS_TOKEN}
    for _ in range(max_wait // 5):
        time.sleep(5)
        try:
            resp = requests.get(url, params=params, timeout=15)
            status = resp.json().get("status_code", "")
            print(f"[INFO] Container status: {status}", flush=True)
            if status == "FINISHED":
                return True
            if status == "ERROR":
                return False
        except Exception as e:
            print(f"[WARN] Status check: {e}", flush=True)
    return False


def ig_publish(creation_id: str) -> dict | None:
    """メディアコンテナを公開して投稿情報を返す。"""
    url = f"{IG_GRAPH_BASE}/{IG_USER_ID}/media_publish"
    params = {"creation_id": creation_id, "access_token": IG_ACCESS_TOKEN}
    try:
        resp = requests.post(url, params=params, timeout=30)
        data = resp.json()
        post_id = data.get("id")
        if post_id:
            print(f"[OK] IG published: {post_id}", flush=True)
            return {"id": post_id}
        else:
            print(f"[FAIL] IG publish error: {data}", flush=True)
            return None
    except Exception as e:
        print(f"[FAIL] IG publish exception: {e}", flush=True)
        return None


def ig_get_permalink(post_id: str) -> str:
    """投稿の permalink を取得する。"""
    url = f"{IG_GRAPH_BASE}/{post_id}"
    params = {"fields": "permalink", "access_token": IG_ACCESS_TOKEN}
    try:
        resp = requests.get(url, params=params, timeout=15)
        permalink = resp.json().get("permalink", "")
        return permalink
    except Exception:
        return f"https://www.instagram.com/p/{post_id}/"


# ---------------------------------------------------------------------------
# ログ
# ---------------------------------------------------------------------------
def load_today_log(log_file: Path) -> dict | None:
    """今日の成功ログを返す。なければ None。"""
    today = datetime.date.today().isoformat()
    if not log_file.exists():
        return None
    for line in reversed(log_file.read_text(encoding="utf-8").strip().split("\n")):
        line = line.strip()
        if not line:
            continue
        try:
            entry = json.loads(line)
            if entry.get("date") == today and entry.get("status") == "ok":
                return entry
        except Exception:
            pass
    return None


def append_log(log_file: Path, entry: dict):
    log_file.parent.mkdir(parents=True, exist_ok=True)
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


# ---------------------------------------------------------------------------
# メイン
# ---------------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(description="Lumen IG daily post")
    parser.add_argument("--caption-file", required=True, help="キャプションテキストファイルのパス")
    parser.add_argument("--concept-note", default="", help="今日のコンセプト（1行）")
    args = parser.parse_args()

    today = datetime.date.today().isoformat()
    script_dir = Path(__file__).parent
    lumen_dir  = script_dir.parent
    queue_dir  = lumen_dir / "images" / "queue"
    log_file   = lumen_dir / "logs" / "daily_post.jsonl"

    # --- 認証情報チェック ---
    for var in ("IG_USER_ID", "IG_ACCESS_TOKEN", "CLOUDINARY_CLOUD_NAME",
                "CLOUDINARY_API_KEY", "CLOUDINARY_API_SECRET"):
        if not os.environ.get(var):
            print(f"[FATAL] {var} is not set", flush=True)
            sys.exit(1)

    # --- 重複チェック ---
    existing = load_today_log(log_file)
    if existing:
        print(f"[SKIP] Already posted today ({today}): {existing.get('permalink')}", flush=True)
        sys.exit(0)

    # --- キャプション読み込み ---
    caption_path = Path(args.caption_file)
    if not caption_path.exists():
        print(f"[FATAL] Caption file not found: {caption_path}", flush=True)
        sys.exit(1)
    caption = caption_path.read_text(encoding="utf-8").strip()
    concept = args.concept_note or "abstract light"
    print(f"[INFO] Caption ({len(caption)}chars), concept={concept}", flush=True)

    # --- 画像取得 ---
    image_source = None
    cloudinary_url = None

    # 1) キューから
    queue_dir.mkdir(parents=True, exist_ok=True)
    queue_image = get_image_from_queue(queue_dir)
    if queue_image:
        cloudinary_url = upload_to_cloudinary(queue_image)
        if cloudinary_url:
            image_source = "queue"
            queue_image.unlink()  # 使用済みを削除

    # 2) HF FLUX
    if not cloudinary_url:
        img_bytes = generate_with_hf(concept)
        if img_bytes:
            cloudinary_url = upload_to_cloudinary(img_bytes)
            if cloudinary_url:
                image_source = "HF FLUX"

    # 3) Pollinations
    if not cloudinary_url:
        img_bytes = generate_with_pollinations(concept)
        if img_bytes:
            cloudinary_url = upload_to_cloudinary(img_bytes)
            if cloudinary_url:
                image_source = "Pollinations"

    if not cloudinary_url:
        entry = {
            "date": today, "status": "error",
            "error": "No image obtained from any source",
            "timestamp": datetime.datetime.now().isoformat(),
        }
        append_log(log_file, entry)
        print("[FAIL] Could not obtain image", flush=True)
        sys.exit(1)

    # --- IG 投稿 ---
    creation_id = ig_create_container(cloudinary_url, caption)
    if not creation_id:
        entry = {
            "date": today, "status": "error",
            "error": "IG container creation failed",
            "image_url": cloudinary_url,
            "timestamp": datetime.datetime.now().isoformat(),
        }
        append_log(log_file, entry)
        sys.exit(1)

    # コンテナ完成待ち
    ig_wait_for_container(creation_id, max_wait=60)

    publish_result = ig_publish(creation_id)
    if not publish_result:
        entry = {
            "date": today, "status": "error",
            "error": "IG publish failed",
            "creation_id": creation_id,
            "timestamp": datetime.datetime.now().isoformat(),
        }
        append_log(log_file, entry)
        sys.exit(1)

    post_id   = publish_result["id"]
    permalink = ig_get_permalink(post_id)

    # --- キュー残数チェック ---
    queue_count = len(list(queue_dir.glob("*.[jpJP][pnPN][gGgG]*")))

    # --- 成功ログ ---
    entry = {
        "date": today, "status": "ok",
        "media_id": post_id,
        "permalink": permalink,
        "image_source": image_source,
        "concept": concept,
        "queue_remaining": queue_count,
        "timestamp": datetime.datetime.now().isoformat(),
    }
    append_log(log_file, entry)

    print(f"[SUCCESS] {permalink}", flush=True)
    print(f"[INFO] source={image_source} queue_remaining={queue_count}", flush=True)


if __name__ == "__main__":
    main()
