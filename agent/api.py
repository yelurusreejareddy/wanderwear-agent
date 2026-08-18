"""
api.py -- phase 9: wraps the real agents in a real web server, so a
website (or curl, or the browser's own /docs page FastAPI builds for
free) can talk to them over HTTP instead of only running them from a
terminal. This file adds zero new agent logic, it only exposes what
loop_langgraph.py and stylist.py already do.
"""
from typing import Annotated, Optional

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

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


@app.post("/plan-trip", response_model=TripResponse)
def plan_trip(payload: TripRequest):
    """The full real travel agent, same one tested end to end in phase
    8, weather, places, the critic loop, and it may call the stylist
    agent internally too if it decides the trip needs outfit advice."""
    answer = run_agent(payload.question)
    return TripResponse(answer=answer)


@app.post("/style-me", response_model=StyleResponse)
def style_me(payload: StyleRequest):
    """The stylist agent on its own, no travel context at all, for a
    real "what should I wear tonight" question with no trip involved.
    rejected_ids lets a real caller say "not that one" and get a
    genuinely different real combination for the same request."""
    result, tokens_used = get_outfit_suggestion_for_trip(payload.request, payload.rejected_ids)
    return StyleResponse(**result)


@app.get("/wardrobe")
def get_wardrobe():
    """Real, phase 10 security fix: review.html used to read
    wardrobe_items straight from Supabase using the public anon key,
    which worked fine for the real text fields but can no longer serve
    real photos now that the bucket is private. This endpoint uses the
    real, privileged service_client instead, only ever running here on
    the real backend, and hands back a fresh, real, temporary signed
    URL for every real photo."""
    rows = service_client.table("wardrobe_items").select("*").order("category").execute().data
    for row in rows:
        row["photo_url"] = sign_photo_url(row["photo_url"])
    return rows


@app.get("/inspiration")
def get_inspiration():
    """Same real fix as /wardrobe, for the saved style inspiration
    photos instead of owned wardrobe items."""
    rows = service_client.table("style_inspiration").select("*").execute().data
    for row in rows:
        row["photo_url"] = sign_photo_url(row["photo_url"])
    return rows
