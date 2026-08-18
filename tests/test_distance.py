"""
Real unit tests for distance.py's calculate_distance. No API, no
network, no env vars needed, just checking the real math against
real, known distances.
"""
import sys
from pathlib import Path

import pytest

# distance.py lives in agent/, not tests/, this adds that real folder
# to Python's search path so "import distance" below can find it.
sys.path.insert(0, str(Path(__file__).parent.parent / "agent"))

from distance import calculate_distance


def test_same_point_is_zero_distance():
    # A real point compared to itself, the distance must be exactly 0.
    result = calculate_distance(41.8781, -87.6298, 41.8781, -87.6298)
    assert result == 0.0


def test_known_real_distance_chicago_to_new_york():
    # Chicago (41.8781, -87.6298) to New York (40.7128, -74.0060), a
    # real, well-known distance, roughly 712-716 miles as the crow
    # flies. We check a real range, not one exact decimal, since two
    # different real sources round this slightly differently.
    result = calculate_distance(41.8781, -87.6298, 40.7128, -74.0060)
    assert 700 <= result <= 720


def test_distance_is_symmetric():
    # A real distance from A to B must equal B to A, direction should
    # never change the real result.
    a_to_b = calculate_distance(36.1627, -86.7816, 35.1495, -90.0490)
    b_to_a = calculate_distance(35.1495, -90.0490, 36.1627, -86.7816)
    assert a_to_b == b_to_a


# Real gap, not yet fixed as of writing this test: calculate_distance
# has no real bounds check on its inputs. A real latitude can only ever
# be -90 to 90, a real longitude only -180 to 180, anything outside
# that isn't a real point on Earth at all. These coordinates can come
# from an LLM's own tool call, the same real reason this project
# already guards against calling coordinate tools before a real
# geocode_city call, so a bad value should fail loudly, not silently
# compute a meaningless number. Written first, on purpose, before the
# real fix exists, to genuinely fail now and genuinely pass once
# distance.py adds the check.
def test_invalid_latitude_raises():
    with pytest.raises(ValueError):
        calculate_distance(999, -86.7816, 35.1495, -90.0490)


def test_invalid_longitude_raises():
    with pytest.raises(ValueError):
        calculate_distance(36.1627, -200, 35.1495, -90.0490)
