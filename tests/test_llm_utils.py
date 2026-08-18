"""
Real unit tests for llm_utils.py's extract_json, the exact function
that fixed the real IMG_2652.PNG bug (extra text around the model's
real JSON breaking a naive parse). No API, no network, no env vars
needed, this only tests real string parsing.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "agent"))

from llm_utils import extract_json


def test_clean_json_parses_directly():
    raw = '{"category": "top", "color": "blue"}'
    result = extract_json(raw, fallback_key="raw")
    assert result == {"category": "top", "color": "blue"}


def test_json_with_surrounding_text_still_parses():
    # The real bug: a model wraps real JSON in a sentence and a
    # markdown fence instead of returning only the JSON.
    raw = 'Here is the real result:\n```json\n{"fits_request": true}\n```\nHope that helps!'
    result = extract_json(raw, fallback_key="raw")
    assert result == {"fits_request": True}


def test_invalid_json_falls_back_honestly():
    # No real JSON at all, must fall back to the raw text under the
    # given key, never silently invent structured data.
    raw = "I could not find a matching outfit."
    result = extract_json(raw, fallback_key="gap_note")
    assert result == {"gap_note": raw}


def test_malformed_braces_falls_back_instead_of_crashing():
    # Real braces exist but the real content between them isn't valid
    # JSON, this must fall back, not raise.
    raw = "{not real json at all}"
    result = extract_json(raw, fallback_key="raw")
    assert result == {"raw": raw}
