"""
Publishes a post to your LinkedIn profile using the saved token.
Respects config.json's "use_images" setting — if false, posts text-only
even when a hook line is present.

USAGE
  python post_to_linkedin.py "Your post text" "Short hook line for the graphic"

  or, to post the next item from a queue file (see queue.json):
  python post_to_linkedin.py --from-queue
"""

import json
import os
import sys
from datetime import date, timedelta
import requests
from generate_image import generate as generate_image

POSTS_URL = "https://api.linkedin.com/rest/posts"
IMAGES_URL = "https://api.linkedin.com/rest/images"

DEFAULT_CONFIG = {"use_images": True}


def load_config():
    if os.path.exists("config.json"):
        with open("config.json") as f:
            return {**DEFAULT_CONFIG, **json.load(f)}
    return DEFAULT_CONFIG


def load_tokens():
    with open("tokens.json") as f:
        return json.load(f)


def _linkedin_version_candidates():
    """LinkedIn's REST API is versioned by monthly release train (YYYYMM),
    and only roughly the last 12 months stay active — a version hardcoded
    today will eventually start rejecting requests with a 426. Try the
    current month first, falling back to earlier months."""
    month = date.today().replace(day=1)
    candidates = []
    for _ in range(13):
        candidates.append(month.strftime("%Y%m"))
        month = (month - timedelta(days=1)).replace(day=1)
    return candidates


def linkedin_request(method: str, url: str, headers: dict, **kwargs) -> requests.Response:
    """Like requests.request, but retries with older LinkedIn-Version values
    if the newest one isn't active yet (426 NONEXISTENT_VERSION)."""
    resp = None
    for version in _linkedin_version_candidates():
        resp = requests.request(method, url, headers={**headers, "LinkedIn-Version": version}, **kwargs)
        if resp.status_code != 426:
            return resp
    return resp


def upload_image(access_token: str, author_urn: str, image_path: str) -> str:
    """Uploads an image to LinkedIn and returns its image URN."""
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
        "X-Restli-Protocol-Version": "2.0.0",
    }

    init_resp = linkedin_request(
        "POST",
        f"{IMAGES_URL}?action=initializeUpload",
        headers=headers,
        json={"initializeUploadRequest": {"owner": author_urn}},
    )
    init_resp.raise_for_status()
    value = init_resp.json()["value"]
    upload_url = value["uploadUrl"]
    image_urn = value["image"]

    with open(image_path, "rb") as f:
        image_bytes = f.read()

    upload_resp = requests.put(
        upload_url,
        headers={"Authorization": f"Bearer {access_token}"},
        data=image_bytes,
    )
    upload_resp.raise_for_status()

    return image_urn


def publish_post(text: str, hook: str = None):
    config = load_config()
    tokens = load_tokens()
    access_token = tokens["access_token"]
    author_urn = tokens["author_urn"]

    body = {
        "author": author_urn,
        "commentary": text,
        "visibility": "PUBLIC",
        "distribution": {
            "feedDistribution": "MAIN_FEED",
            "targetEntities": [],
            "thirdPartyDistributionChannels": [],
        },
        "lifecycleState": "PUBLISHED",
        "isReshareDisabledByAuthor": False,
    }

    if hook and config.get("use_images", True):
        image_path = generate_image(hook, "post_image.png")
        image_urn = upload_image(access_token, author_urn, image_path)
        body["content"] = {"media": {"id": image_urn}}

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
        "X-Restli-Protocol-Version": "2.0.0",
    }

    resp = linkedin_request("POST", POSTS_URL, headers=headers, json=body)

    if resp.status_code == 201:
        post_urn = resp.headers.get("x-restli-id", "(id not returned)")
        print(f"Posted successfully! Post URN: {post_urn}")
    else:
        print(f"Failed ({resp.status_code}): {resp.text}")
        resp.raise_for_status()


def post_from_queue():
    try:
        with open("queue.json") as f:
            queue = json.load(f)
    except FileNotFoundError:
        print("queue.json not found. Create it with a list of post objects.")
        return

    if not queue:
        print("Queue is empty. Nothing to post.")
        return

    next_post = queue.pop(0)
    # Supports both old format (plain string) and new format (object with text + hook)
    if isinstance(next_post, str):
        publish_post(next_post)
    else:
        publish_post(next_post["text"], next_post.get("hook"))

    with open("queue.json", "w") as f:
        json.dump(queue, f, indent=2)


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--from-queue":
        post_from_queue()
    elif len(sys.argv) > 1:
        hook = sys.argv[2] if len(sys.argv) > 2 else None
        publish_post(sys.argv[1], hook)
    else:
        print('Usage: python post_to_linkedin.py "Your post text" "Optional hook for graphic"')
        print("   or: python post_to_linkedin.py --from-queue")
