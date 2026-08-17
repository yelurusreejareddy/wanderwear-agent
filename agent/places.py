"""
places.py -- fourth tool, practice, written by Sreeja.
Takes a latitude, longitude, and a category (like "restaurant"), returns a
clean list of real nearby places from OpenStreetMap's Overpass API.
"""
import time

import requests

OVERPASS_URL = "https://overpass-api.de/api/interpreter"
HEADERS = {"User-Agent": "personal-agent-learning-project"}

# The free public Overpass server flakes out often, confirmed many times
# across this whole project, sometimes a 406, sometimes a 504, sometimes
# just an empty non-JSON response. Before this fix, that failure went all
# the way back to Groq, which then had to GUESS whether to retry, and we
# watched it guess wrong twice in a row, retrying a different category
# instead of the one that actually failed. A plain retry loop here, no
# LLM involved, no extra tokens spent, fixes the real, common case for
# free, before the failure is ever reported as real.
MAX_HTTP_RETRIES = 3
RETRY_DELAY_SECONDS = 1


def _query_overpass(query):
    """POST a query to Overpass, retrying a few times on real, transient
    failures before giving up. Returns the parsed JSON, or raises the
    last real error if every attempt failed."""
    last_error = None
    for attempt in range(MAX_HTTP_RETRIES):
        try:
            response = requests.post(OVERPASS_URL, data={"data": query}, headers=HEADERS, timeout=30)
            return response.json()
        except requests.exceptions.JSONDecodeError as error:
            last_error = error
            print(f"Overpass attempt {attempt + 1} failed, retrying: {error}")
            time.sleep(RETRY_DELAY_SECONDS)

    raise last_error

# OpenStreetMap does not put every kind of place under one shared key. Real
# example that exposed this: asking for "beach" using amenity= returned
# ZERO results, silently, because beaches are tagged natural=beach, not an
# amenity at all. This maps our plain category names to the (key, value)
# pair OSM actually uses. Anything not listed here falls back to amenity=,
# which still covers most everyday categories like restaurant, cafe, bar.
CATEGORY_TAGS = {
    "beach": ("natural", "beach"),
    "park": ("leisure", "park"),
    "viewpoint": ("tourism", "viewpoint"),
    "museum": ("tourism", "museum"),
    "attraction": ("tourism", "attraction"),
    "hotel": ("tourism", "hotel"),
}

# Real example that exposed this: "Miami" geocodes to downtown Miami, but
# the famous beaches, Miami Beach, South Pointe Beach, sit on a separate
# island several miles away across the bay. 800m, fine for walking to a
# restaurant, found nothing. 15km genuinely reaches the real beaches.
# Restaurants and cafes stay walkable on purpose, city-scale things like
# beaches and attractions need a much wider net by default.
CATEGORY_RADIUS = {
    "restaurant": 800,
    "cafe": 800,
    "bar": 800,
    "beach": 15000,
    "attraction": 8000,
    "viewpoint": 8000,
    "museum": 8000,
    "park": 5000,
    "hotel": 5000,
}
DEFAULT_RADIUS = 800


def find_places(lat, lon, category="restaurant", radius=None, limit=10):
    """Find real places of a given category near a latitude and longitude.
    category is a plain name like "restaurant", "cafe", "beach", or "park",
    see CATEGORY_TAGS for the ones that need special handling. If radius
    is not given, a sensible default is picked automatically based on
    category, see CATEGORY_RADIUS, since a walk to a restaurant and a trip
    to a beach are not the same distance. Returns at most `limit` places,
    the most completely documented ones first, see _completeness_score
    below for why "most complete" is not the same thing as "highest
    rated"."""

    if radius is None:
        radius = CATEGORY_RADIUS.get(category, DEFAULT_RADIUS)

    osm_key, osm_value = CATEGORY_TAGS.get(category, ("amenity", category))

    # Real example that exposed this too: a restaurant is a single point on
    # the map, a "node". A beach is usually drawn as a whole shape, a
    # "way". "nwr" means node, way, OR relation, so we stop silently
    # missing anything that isn't a simple point. "out center;" instead of
    # plain "out;" is needed because a way has no single lat/lon of its
    # own, only a list of corner points, "center" asks Overpass to compute
    # one representative point for it, same as a node already has.
    query = (
        f'[out:json][timeout:25];'
        f'nwr["{osm_key}"="{osm_value}"](around:{radius},{lat},{lon});'
        f'out center;'
    )

    data = _query_overpass(query)

    places = []
    for item in data["elements"]:
        tags = item["tags"]
        name = tags.get("name", "Unnamed place")

        # A node has "lat"/"lon" directly. A way or relation has neither,
        # only "center": {"lat": ..., "lon": ...}, from the "out center;"
        # above. .get() with a fallback lets one line handle both shapes.
        lat_value = item.get("lat", item.get("center", {}).get("lat"))
        lon_value = item.get("lon", item.get("center", {}).get("lon"))

        places.append({
            "name": name,
            "lat": lat_value,
            "lon": lon_value,
            "_score": _completeness_score(tags, name),
        })

    # Most complete listings first, this is what actually controls which
    # ones survive the trim below, then real ratings become available.
    places.sort(key=lambda place: place["_score"], reverse=True)

    # Trim to `limit` BEFORE removing the score, and remove the score here,
    # not in the raw dict above, so it never accidentally reaches Groq or
    # gets summarized to the user as if it were a real rating, it's just
    # our own internal sorting logic, nothing more.
    trimmed = places[:limit]
    for place in trimmed:
        del place["_score"]

    return trimmed


def find_place_by_name(lat, lon, name, category="restaurant", radius=None):
    """Look up one specific real place by name, for when a user names an
    exact restaurant instead of asking for general suggestions. Returns a
    dict with the real name, lat, and lon if found, or None if not.

    Real, tested finding: searching by name ALONE, no category, made
    Overpass genuinely unreliable, timing out on 3 of 4 real attempts,
    a different, worse failure than the usual quick flakiness. Combining
    name with a category cut that down to normal flakiness levels and cut
    the response time from 10-30+ seconds to 1-4 seconds, confirmed with
    repeated real tests, not a guess. So category is required here, not
    optional the way it is in find_places."""

    if radius is None:
        radius = CATEGORY_RADIUS.get(category, DEFAULT_RADIUS)

    osm_key, osm_value = CATEGORY_TAGS.get(category, ("amenity", category))

    # The ",i" makes the name match case-insensitive, and "~" means
    # "contains this text", not "is exactly equal to", so "oscar" still
    # finds "Oscar's Taco Shop".
    query = (
        f'[out:json][timeout:25];'
        f'nwr["{osm_key}"="{osm_value}"]["name"~"{name}",i](around:{radius},{lat},{lon});'
        f'out center;'
    )

    data = _query_overpass(query)

    if len(data["elements"]) == 0:
        return None

    best_match = data["elements"][0]
    tags = best_match["tags"]
    real_name = tags.get("name", "Unnamed place")
    lat_value = best_match.get("lat", best_match.get("center", {}).get("lat"))
    lon_value = best_match.get("lon", best_match.get("center", {}).get("lon"))

    return {"name": real_name, "lat": lat_value, "lon": lon_value}


def _completeness_score(tags, name):
    """This does NOT measure quality. It cannot know if the food is good or
    if people like this place, real ratings and review counts are not
    available for free from any provider, OpenStreetMap, Yelp, or
    Foursquare, see the docs. All this measures is how many contact fields
    someone filled in on OpenStreetMap, name, website, phone, hours. That
    only tells us "this looks like a real, currently maintained listing,"
    not "this is a good place." A beloved local spot with a sparse listing
    can score low here, and a mediocre chain with a fully filled-in profile
    can score high. Use this only to filter out likely-abandoned or junk
    entries, never present it to a user as any kind of quality signal."""
    score = 0
    if name != "Unnamed place":
        score += 1
    if tags.get("website"):
        score += 1
    if tags.get("phone"):
        score += 1
    if tags.get("opening_hours"):
        score += 1
    return score


if __name__ == "__main__":
    result = find_places(36.1622767, -86.7742984, category="restaurant")
    print(f"found {len(result)} places")
    for place in result[:5]:
        print(place)
