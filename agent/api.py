"""
api.py -- phase 9: wraps the real agents in a real web server, so a
website (or curl, or the browser's own /docs page FastAPI builds for
free) can talk to them over HTTP instead of only running them from a
terminal. This file adds zero new agent logic, it only exposes what
loop_langgraph.py and stylist.py already do.
"""
import os
from typing import Annotated, Optional

from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from supabase import create_client

from auth_context import set_request_identity
from loop_langgraph import run_agent
from stylist import get_outfit_suggestion_for_trip
from photo_access import service_client, sign_photo_url

app = FastAPI(title="Personal Agent API")

# review.html is a plain static file, opened straight in a browser, not
# served BY this app, so a browser normally blocks it from calling a
# different real origin (this server). This is real, deliberately
# permissive only because review.html is a local, personal review tool,
# never deployed publicly, real production CORS would name exact real
# origins instead of allowing all of them.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET"],
)


# Pydantic models: real, typed shapes for what a request/response must
# look like. FastAPI reads these to validate incoming JSON automatically
# (a bad request gets a real 422 error, not a crash deep in our code),
# and to generate the real, live /docs page below, both for free, just
# from writing the shape once.
class LoginRequest(BaseModel):
    email: str
    password: str


class LoginResponse(BaseModel):
    access_token: str
    user_id: str


class TripRequest(BaseModel):
    question: str


class TripResponse(BaseModel):
    answer: str


class StyleRequest(BaseModel):
    request: str
    # A real Supabase row id is a serial primary key, it always starts
    # at 1, it can never be zero or negative. Field(gt=0) makes that a
    # real, enforced constraint, so a bad id is rejected here, as a
    # real 422, instead of being silently passed downstream.
    rejected_ids: list[Annotated[int, Field(gt=0)]] = []


class OutfitItem(BaseModel):
    id: int
    category: str
    color: str
    style_notes: str
    photo_url: str


class InspiredBy(BaseModel):
    description: str
    photo_url: str
    product_url: Optional[str] = None


class StyleResponse(BaseModel):
    fits_request: bool
    reasoning: Optional[str] = None
    gap_note: Optional[str] = None
    shopping_suggestion: Optional[str] = None
    outfit: list[OutfitItem]
    inspired_by_saved_look: Optional[InspiredBy] = None


@app.get("/health")
def health():
    """A plain, real check that the server is actually up, no agent
    logic involved, useful once this is deployed (phase 10) and
    something needs to ask "is it alive" without spending real tokens."""
    return {"status": "ok"}


@app.post("/login", response_model=LoginResponse)
def login(payload: LoginRequest):
    """Phase 12: real login. A plain anon-key client, not the
    privileged service_client, real sign-in should only ever run with
    the same real, limited key any client-side code would use. Returns
    a real access token, every other endpoint below needs it in a real
    'Authorization: Bearer <token>' header."""
    anon_client = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))
    try:
        session = anon_client.auth.sign_in_with_password(
            {"email": payload.email, "password": payload.password}
        )
    except Exception:
        raise HTTPException(status_code=401, detail="Real login failed, check email/password")
    return LoginResponse(access_token=session.session.access_token, user_id=session.user.id)


def require_user(authorization: Annotated[str | None, Header()] = None):
    """Phase 12: the real gatekeeper every other endpoint below runs
    through. service_client.auth.get_user(token) asks Supabase itself
    to verify the real token, not something this code trusts blindly.
    On success, set_request_identity stores a real, freshly-built,
    per-request client (this exact user's own token, never the shared
    anon key) in the ContextVar auth_context.py defines, so memory.py
    and stylist.py automatically see the real, correct identity for
    the rest of this one real request, with no change needed to their
    own function signatures."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Real login required, send a Bearer token")

    token = authorization.removeprefix("Bearer ").strip()
    try:
        user = service_client.auth.get_user(token).user
    except Exception:
        raise HTTPException(status_code=401, detail="Real token is invalid or expired")

    request_client = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))
    request_client.postgrest.auth(token)
    set_request_identity(request_client, user.id)
    return user.id


@app.post("/plan-trip", response_model=TripResponse)
def plan_trip(payload: TripRequest, user_id: Annotated[str, Depends(require_user)]):
    """The full real travel agent, same one tested end to end in phase
    8, weather, places, the critic loop, and it may call the stylist
    agent internally too if it decides the trip needs outfit advice."""
    answer = run_agent(payload.question)
    return TripResponse(answer=answer)


@app.post("/style-me", response_model=StyleResponse)
def style_me(payload: StyleRequest, user_id: Annotated[str, Depends(require_user)]):
    """The stylist agent on its own, no travel context at all, for a
    real "what should I wear tonight" question with no trip involved.
    rejected_ids lets a real caller say "not that one" and get a
    genuinely different real combination for the same request."""
    result, tokens_used = get_outfit_suggestion_for_trip(payload.request, payload.rejected_ids)
    return StyleResponse(**result)


@app.get("/wardrobe")
def get_wardrobe(user_id: Annotated[str, Depends(require_user)]):
    """Real, phase 10 security fix: review.html used to read
    wardrobe_items straight from Supabase using the public anon key,
    which worked fine for the real text fields but can no longer serve
    real photos now that the bucket is private. This endpoint uses the
    real, privileged service_client instead, only ever running here on
    the real backend, and hands back a fresh, real, temporary signed
    URL for every real photo.

    Phase 12: service_client bypasses RLS by design, the real per-user
    policies from migration 0010 do nothing for it, so this now
    filters by the real, logged-in user's own id explicitly, the same
    real "two gates" lesson as every other service_client use in this
    project."""
    rows = (
        service_client.table("wardrobe_items")
        .select("*")
        .eq("user_id", user_id)
        .order("category")
        .execute()
        .data
    )
    for row in rows:
        row["photo_url"] = sign_photo_url(row["photo_url"])
    return rows


@app.get("/inspiration")
def get_inspiration(user_id: Annotated[str, Depends(require_user)]):
    """Same real fix as /wardrobe, for the saved style inspiration
    photos instead of owned wardrobe items."""
    rows = (
        service_client.table("style_inspiration")
        .select("*")
        .eq("user_id", user_id)
        .execute()
        .data
    )
    for row in rows:
        row["photo_url"] = sign_photo_url(row["photo_url"])
    return rows
