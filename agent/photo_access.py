"""
photo_access.py -- the real, privileged half of Supabase access. Only
this file (and anything that imports from it) ever touches
SUPABASE_SERVICE_KEY. Everything else in this project keeps using the
regular public key. This is the real, correct split: a service-role
key can bypass privacy rules entirely, so it only ever belongs in
trusted server-side code, never in review.html, never in a browser,
never in anything a client could read.
"""
import os
from urllib.parse import urlparse

from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

# The real, privileged client. Used only to generate short-lived signed
# URLs and to upload real new photos from our own trusted local
# scripts, never handed to anything outside this project's own code.
service_client = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_SERVICE_KEY"))

SIGNED_URL_EXPIRY_SECONDS = 3600  # 1 real hour, then the link stops working.


def sign_photo_url(stored_url, expires_in=SIGNED_URL_EXPIRY_SECONDS):
    """Real photos were originally saved with a permanent-looking
    public URL, back when the buckets were public. Those buckets are
    now private, so that old stored string no longer works as a real
    link, but it still tells us exactly which bucket and which file to
    ask for. This pulls the real bucket name and real file path back
    out of that old URL, and asks Supabase, using the privileged
    service key, for a real, temporary, signed link instead. Returns
    None if the stored value doesn't look like a real photo URL, an
    honest signal to the caller rather than a broken link."""
    if not stored_url:
        return None

    path = urlparse(stored_url).path
    marker = "/storage/v1/object/public/"
    if marker not in path:
        return stored_url  # Already something else, don't touch it.

    bucket_and_key = path.split(marker, 1)[1]
    bucket, _, object_key = bucket_and_key.partition("/")

    response = service_client.storage.from_(bucket).create_signed_url(object_key, expires_in)
    return response.get("signedURL") or response.get("signedUrl")
