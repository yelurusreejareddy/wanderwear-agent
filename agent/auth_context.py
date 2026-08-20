"""
auth_context.py -- phase 12: the real answer to "how does memory.py or
stylist.py know WHICH real logged-in user is asking", without changing
their own function signatures, and without touching loop.py at all.

Real problem: save_trip(question, answer) and suggest_outfit(request)
are called from real HTTP requests (through api.py, a different real
user's token every time) AND from direct CLI use (python loop.py,
python stylist.py, no HTTP request at all). A single shared client
object, mutated per call, is a real, genuine bug waiting to happen the
moment two real HTTP requests from two real users land close together,
request A's identity could leak into request B's query.

contextvars.ContextVar is Python's own real, standard answer to this:
each real async request (FastAPI/uvicorn) gets its own isolated copy,
set once by api.py's real login check, read anywhere deeper in the
call stack, safe under real concurrency, unlike a plain module-level
variable would be.
"""
import os
from contextvars import ContextVar
from typing import Optional

from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

_request_client: ContextVar[Optional["Client"]] = ContextVar("request_client", default=None)
_request_user_id: ContextVar[Optional[str]] = ContextVar("request_user_id", default=None)

# Real fallback for direct CLI use (python loop.py, python stylist.py),
# where there is no real HTTP request to set the ContextVar above at
# all. Logs in once, as Sreeja's own real account, using real
# credentials from .env, never committed, never pasted in chat. Built
# lazily, only the first time it's actually needed, and cached, a real
# CLI run is single-user, single-threaded, safe to reuse.
_cli_client = None
_cli_user_id = None


def _build_cli_client():
    global _cli_client, _cli_user_id
    if _cli_client is not None:
        return _cli_client, _cli_user_id

    email = os.getenv("CLI_EMAIL")
    password = os.getenv("CLI_PASSWORD")
    if not email or not password:
        raise RuntimeError(
            "CLI_EMAIL and CLI_PASSWORD must be set in .env for direct "
            "CLI use (python loop.py, python stylist.py, etc), phase 12's "
            "real per-user RLS policies reject any request with no real, "
            "logged-in identity."
        )

    client = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))
    session = client.auth.sign_in_with_password({"email": email, "password": password})
    _cli_client = client
    _cli_user_id = session.user.id
    return _cli_client, _cli_user_id


def set_request_identity(client, user_id):
    """Called once per real HTTP request, by api.py's own real login
    check, right after it verifies a real, valid token. Everything
    deeper in that same request (memory.py, stylist.py) reading
    get_client()/get_user_id() sees this exact real identity, and only
    for the duration of this one real request."""
    _request_client.set(client)
    _request_user_id.set(user_id)


def get_client():
    """The real, correct Supabase client to use for the CURRENT real
    caller, an HTTP request's own real authenticated client if one is
    set, otherwise the real CLI fallback above."""
    client = _request_client.get()
    if client is not None:
        return client
    client, _ = _build_cli_client()
    return client


def get_user_id():
    """Same real fallback logic as get_client(), for callers that need
    the real user id itself, not just an authenticated client, real,
    live need: /wardrobe and /inspiration use the privileged
    service_client, which bypasses RLS by design, so they must filter
    by this real id themselves, RLS cannot do it for them."""
    user_id = _request_user_id.get()
    if user_id is not None:
        return user_id
    _, user_id = _build_cli_client()
    return user_id
