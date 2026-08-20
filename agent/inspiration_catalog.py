"""
inspiration_catalog.py -- phase 7.5: the real batch job for saved style
photos. Walks every real photo in closet/inspos/, uploads each one to
the real 'inspiration' Storage bucket, asks the vision model to draft a
description (and real brand/product name when visible), and saves a
real row in style_inspiration. Same safe-to-rerun pattern as
wardrobe_catalog.py: skips anything already cataloged.
"""
import mimetypes
import os
import re
import time

from dotenv import load_dotenv

from inspiration_vision import draft_inspiration_label
from photo_access import service_client
from auth_context import get_user_id

load_dotenv()

# Phase 12: same real reason as wardrobe_catalog.py, an admin-only
# batch script, real writes go through the privileged service_client,
# tagged with the real, logged-in owner id.
supabase = service_client

INSPOS_DIR = "/Users/boo/Documents/personal-agent/closet/inspos"

SECONDS_BETWEEN_VISION_CALLS = 2.5


def _already_cataloged():
    # Filtered to the real, current user's own rows, same real reason
    # as wardrobe_catalog.py's own version of this function.
    response = (
        supabase.table("style_inspiration")
        .select("file_name")
        .eq("user_id", get_user_id())
        .execute()
    )
    return {row["file_name"] for row in response.data}


def _storage_key(file_name):
    return re.sub(r"[^A-Za-z0-9._-]", "_", file_name)


def _upload_photo(file_name, full_path):
    # Real, live security fix (phase 10): same reason as
    # wardrobe_catalog.py, the bucket is now private, real uploads
    # need the real service role key, never the anon key.
    content_type, _ = mimetypes.guess_type(full_path)
    with open(full_path, "rb") as file:
        file_bytes = file.read()

    storage_key = _storage_key(file_name)
    service_client.storage.from_("inspiration").upload(
        storage_key,
        file_bytes,
        {"content-type": content_type or "application/octet-stream", "upsert": "true"},
    )
    return service_client.storage.from_("inspiration").get_public_url(storage_key)


def catalog_all_inspiration():
    already_done = _already_cataloged()

    all_files = sorted(os.listdir(INSPOS_DIR))
    image_files = [
        name for name in all_files
        if name.lower().endswith((".jpeg", ".jpg", ".png"))
    ]

    to_process = [name for name in image_files if name not in already_done]
    print(f"{len(image_files)} real photos found, {len(already_done)} already "
          f"cataloged, {len(to_process)} left to process.")

    total_tokens = 0
    cataloged = 0

    for file_name in to_process:
        full_path = os.path.join(INSPOS_DIR, file_name)
        try:
            photo_url = _upload_photo(file_name, full_path)
            label, tokens = draft_inspiration_label(full_path)
            total_tokens += tokens

            supabase.table("style_inspiration").insert({
                "file_name": file_name,
                "photo_url": photo_url,
                "description": label.get("description"),
                "source_brand": label.get("source_brand"),
                "source_product_name": label.get("source_product_name"),
                "user_id": get_user_id(),
            }).execute()

            cataloged += 1
            print(f"[{cataloged}/{len(to_process)}] {file_name}: "
                  f"{label.get('description')}")
            if label.get("source_brand"):
                print(f"    real source: {label.get('source_brand')} - "
                      f"{label.get('source_product_name')}")
        except Exception as error:
            print(f"FAILED on {file_name}: {error}")

        time.sleep(SECONDS_BETWEEN_VISION_CALLS)

    return cataloged, total_tokens


if __name__ == "__main__":
    cataloged, total_tokens = catalog_all_inspiration()
    print(f"\nreal photos cataloged this run: {cataloged}")
    print(f"real total cost: {total_tokens} tokens")
