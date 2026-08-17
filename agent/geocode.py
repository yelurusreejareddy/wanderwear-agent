"""
geocode.py -- our first real tool.
Turns a city name, like "Nashville", into a latitude and longitude.
This is Phase 1: one tool, written by hand, no agent and no framework yet.
We just want to see a real tool work on its own before wiring it to Groq.
"""
import requests

# Nominatim is the free geocoding service that OpenStreetMap runs.
# It requires every request to include a "User-Agent" identifying who is
# calling, otherwise it blocks the request. This is Nominatim's own rule,
# not a Python rule, so we just follow it.
NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
HEADERS = {"User-Agent": "personal-agent-learning-project"}


def geocode_city(city_name):
    """Look up a city name and return its latitude and longitude.
    Returns None if the city was not found."""

    # These are the search terms Nominatim expects.
    # q is the thing we're searching for, format asks for JSON back,
    # limit=1 means only give us the single best match.
    params = {"q": city_name, "format": "json", "limit": 1}

    response = requests.get(NOMINATIM_URL, params=params, headers=HEADERS)
    results = response.json()

    # If nothing matched, results comes back as an empty list.
    if len(results) == 0:
        return None

    # Take the first (best) match and pull out the fields we care about.
    best_match = results[0]
    return {
        "city": city_name,
        "lat": float(best_match["lat"]),
        "lon": float(best_match["lon"]),
        "display_name": best_match["display_name"],
    }


# This block only runs when we run this file directly, like
# python geocode.py, not when some other file imports the function.
# It lets us test the tool on its own before anything else depends on it.
if __name__ == "__main__":
    result = geocode_city("Nashville")
    print(result)
