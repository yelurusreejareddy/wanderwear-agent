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

from api import app, require_user

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


# Phase 12: /plan-trip, /style-me, /wardrobe, /inspiration now require a
# real, valid login token (require_user), checked against the real
# Supabase Auth service. app.dependency_overrides is FastAPI's own real,
# standard way to swap that check out in tests, without needing a real,
# live login in CI, real bug found writing this: it's a module-level
# dict, set once for the whole file, NOT "from this point in the file
# onward", so each test below explicitly sets or clears it itself
# rather than relying on where it's written.
FAKE_USER_ID = "fb26c600-bd56-4588-bf0e-563311d78f30"


def test_plan_trip_rejects_missing_login():
    app.dependency_overrides.pop(require_user, None)
    response = client.post("/plan-trip", json={"question": "a real question"})
    assert response.status_code == 401


def test_style_me_rejects_missing_login():
    app.dependency_overrides.pop(require_user, None)
    response = client.post("/style-me", json={"request": "something to wear"})
    assert response.status_code == 401


def test_wardrobe_rejects_missing_login():
    app.dependency_overrides.pop(require_user, None)
    response = client.get("/wardrobe")
    assert response.status_code == 401


def test_plan_trip_rejects_missing_question():
    # No "question" field at all, real Pydantic validation should
    # catch this before our own agent code ever runs.
    app.dependency_overrides[require_user] = lambda: FAKE_USER_ID
    response = client.post("/plan-trip", json={})
    assert response.status_code == 422


def test_plan_trip_rejects_wrong_type():
    # "question" must be a real string, not a number.
    app.dependency_overrides[require_user] = lambda: FAKE_USER_ID
    response = client.post("/plan-trip", json={"question": 12345})
    assert response.status_code == 422


def test_style_me_rejects_missing_request():
    app.dependency_overrides[require_user] = lambda: FAKE_USER_ID
    response = client.post("/style-me", json={})
    assert response.status_code == 422


def test_style_me_rejects_negative_rejected_id():
    # A negative id can never be a real Supabase row id, real ids
    # always start at 1, StyleRequest constrains rejected_ids to
    # positive ints, this confirms a bad one gets a real 422 instead
    # of being silently passed downstream.
    app.dependency_overrides[require_user] = lambda: FAKE_USER_ID
    response = client.post("/style-me", json={"request": "something to wear", "rejected_ids": [-1]})
    assert response.status_code == 422


def test_style_me_accepts_valid_shape_without_calling_the_real_model():
    # rejected_ids has a real default ([]), so a request with only
    # "request" filled in must pass validation, this only confirms the
    # real request SHAPE is accepted, not that a full outfit comes
    # back, that would need a real, live model call.
    app.dependency_overrides[require_user] = lambda: FAKE_USER_ID
    response = client.post("/style-me", json={"request": "something to wear"})
    # Either it truly ran (200) or it failed downstream reaching the
    # real, fake test Supabase URL (500), both prove validation passed,
    # only a real 422 would mean the request shape itself was rejected.
    assert response.status_code != 422
