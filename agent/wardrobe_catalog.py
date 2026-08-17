"""
wardrobe_catalog.py -- phase 7: the real batch job. Walks every real photo
in closet/, uploads each one to real Supabase Storage, asks the vision
model to draft a label for it, and saves a real row in wardrobe_items.

Skips any file already cataloged, so this script is safe to run more than
once, a second run only picks up new photos instead of duplicating rows
or re-spending real tokens on ones already done.
"""
import mimetypes
import os
import re
import time

from dotenv import load_dotenv
from supabase import create_client

from wardrobe_vision import draft_label
from photo_access import service_client

load_dotenv()

supabase = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))

CLOSET_DIR = "/Users/boo/Documents/personal-agent/closet"

# Real free-tier limit, confirmed on Groq's own rate-limits page: 30
# vision requests per minute. Waiting 2.5 seconds between calls keeps us
# under that with real margin, instead of guessing and risking a 429.
SECONDS_BETWEEN_VISION_CALLS = 2.5


def _already_cataloged():
    """Real file names already saved in wardrobe_items, so a second run of
    this script does not re-upload or re-tag the same real photo twice."""
    response = supabase.table("wardrobe_items").select("file_name").execute()
    return {row["file_name"] for row in response.data}


def _storage_key(file_name):
    """Real, live bug found on the first batch run: Supabase Storage
    rejected every real screenshot file with 'Invalid key', because their
    real names, like "Screenshot 2026-08-14 at 11.45.37 AM.png", contain
    spaces, which a storage object key cannot contain. This builds a safe
    key from the real file name, replacing anything that isn't a letter,
    digit, dot, dash, or underscore with an underscore. wardrobe_items
    still keeps the real, original, human-readable file_name, this
    sanitized version is only ever used as the storage path."""
    return re.sub(r"[^A-Za-z0-9._-]", "_", file_name)


def _upload_photo(file_name, full_path):
    """Upload one real photo file to the real 'wardrobe' Storage bucket.
    Real, live security fix (phase 10): the bucket is now private, real
    uploads need the real service role key, the anon key has zero
    storage rights anymore on purpose, see photo_access.py. Still
    returns get_public_url()'s string, that URL no longer actually
    resolves on its own, private buckets don't serve it, but it stays
    a real, stable way to record which bucket and which real file this
    is, sign_photo_url() in photo_access.py knows how to turn this
    same string back into a real, temporary, working link on demand."""
    content_type, _ = mimetypes.guess_type(full_path)
    with open(full_path, "rb") as file:
        file_bytes = file.read()

    storage_key = _storage_key(file_name)
    # Real bug hit on this batch: the upload can succeed and then the
    # vision call can still fail (hit the real daily token cap), which
    # left the real file sitting in storage with no matching row yet. A
    # retry then failed a SECOND time, "Duplicate, resource already
    # exists", since upload() refuses to overwrite by default. "upsert"
    # makes a retry safe either way, a fresh file uploads normally, an
    # already-there one from a previous partial failure gets overwritten
    # with the identical real bytes, not treated as an error.
    service_client.storage.from_("wardrobe").upload(
        storage_key,
        file_bytes,
        {"content-type": content_type or "application/octet-stream", "upsert": "true"},
    )
    return service_client.storage.from_("wardrobe").get_public_url(storage_key)


def catalog_all_photos():
    """The real batch job. Returns (real items cataloged, real total
    tokens spent), so the run can report honest numbers at the end."""
    already_done = _already_cataloged()

    # Only real image files, closet/ also has a .DS_Store from Finder,
    # which is not a photo and would break both upload and tagging.
    all_files = sorted(os.listdir(CLOSET_DIR))
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
        full_path = os.path.join(CLOSET_DIR, file_name)
        try:
            photo_url = _upload_photo(file_name, full_path)
            label, tokens = draft_label(full_path)
            total_tokens += tokens

            supabase.table("wardrobe_items").insert({
                "file_name": file_name,
                "photo_url": photo_url,
                "category": label.get("category"),
                "color": label.get("color"),
                "style_notes": label.get("style_notes"),
            }).execute()

            cataloged += 1
            print(f"[{cataloged}/{len(to_process)}] {file_name}: "
                  f"{label.get('category')}, {label.get('color')}")
        except Exception as error:
            # Same phase-4 rule as everywhere else: one real failure does
            # not stop the whole batch, report it honestly and continue,
            # since dozens of other real photos still need processing.
            print(f"FAILED on {file_name}: {error}")

        time.sleep(SECONDS_BETWEEN_VISION_CALLS)

    return cataloged, total_tokens


if __name__ == "__main__":
    cataloged, total_tokens = catalog_all_photos()
    print(f"\nreal photos cataloged this run: {cataloged}")
    print(f"real total cost: {total_tokens} tokens")
