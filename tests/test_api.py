"""
Real tests for api.py, using FastAPI's own TestClient (built on
httpx), which calls our real app in-process, no real server, no real
network, no real port needed.

These tests deliberately never call the real Groq or Supabase APIs.
/plan-trip and /style-me would need real, working API keys, spend real
tokens, and be genuinely slow and flaky to run in CI on every push, so
instead we test the real, honest things that don't need any of that:
that the server is alive, and that FastAPI's own request validation
(built straight from the Pydantic models in api.py) actually rejects a
bad request instead of silently accepting it.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "agent"))

from fastapi.testclient import TestClient

from api import app

# raise_server_exceptions=False: without this, TestClient re-raises any
# real exception from inside an endpoint instead of turning it into a
# real 500 response. We want that here, test_style_me_accepts_valid_shape
# below expects the fake test Supabase URL to genuinely fail to
# connect, and needs that surfaced as a real response to check, not an
# uncaught exception that fails the test for the wrong reason.
client = TestClient(app, raise_server_exceptions=False)


def test_health_returns_ok():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_plan_trip_rejects_missing_question():
    # No "question" field at all, real Pydantic validation should
    # catch this before our own agent code ever runs.
    response = client.post("/plan-trip", json={})
    assert response.status_code == 422


def test_plan_trip_rejects_wrong_type():
    # "question" must be a real string, not a number.
    response = client.post("/plan-trip", json={"question": 12345})
    assert response.status_code == 422


def test_style_me_rejects_missing_request():
    response = client.post("/style-me", json={})
    assert response.status_code == 422


def test_style_me_rejects_negative_rejected_id():
    # Real gap, not yet fixed as of writing this test: rejected_ids has
    # no real constraint on it, so a negative number is currently
    # accepted by validation and passed straight downstream, even
    # though a real Supabase row id always starts at 1 and can never be
    # negative or zero. Written first, on purpose, to genuinely fail
    # now (currently NOT a 422) and genuinely pass once api.py adds a
    # real constraint to the StyleRequest model.
    response = client.post("/style-me", json={"request": "something to wear", "rejected_ids": [-1]})
    assert response.status_code == 422


def test_style_me_accepts_valid_shape_without_calling_the_real_model():
    # rejected_ids has a real default ([]), so a request with only
    # "request" filled in must pass validation, this only confirms the
    # real request SHAPE is accepted, not that a full outfit comes
    # back, that would need a real, live model call.
    response = client.post("/style-me", json={"request": "something to wear"})
    # Either it truly ran (200) or it failed downstream reaching the
    # real, fake test API key (500), both prove validation passed,
    # only a real 422 would mean the request shape itself was rejected.
    assert response.status_code != 422
