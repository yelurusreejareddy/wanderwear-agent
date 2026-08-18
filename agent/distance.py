"""
distance.py -- fifth tool: real distance between two points on Earth.
Given two latitude/longitude pairs, returns the real distance between them
in miles. No API, no internet, pure math, called the Haversine formula.
"""
import math

EARTH_RADIUS_MILES = 3958.8


def calculate_distance(lat1, lon1, lat2, lon2):
    """Return the real distance in miles between two lat/lon points,
    following the curve of the Earth, not a flat straight line."""

    # These coordinates can come from an LLM's own tool call, the same
    # real reason this project already guards against calling
    # coordinate tools before a real geocode_city call. A real latitude
    # is only ever -90 to 90, a real longitude only -180 to 180,
    # anything outside that isn't a real point on Earth, fail loudly
    # instead of silently returning a meaningless number.
    for lat in (lat1, lat2):
        if not -90 <= lat <= 90:
            raise ValueError(f"{lat} is not a real latitude, must be between -90 and 90")
    for lon in (lon1, lon2):
        if not -180 <= lon <= 180:
            raise ValueError(f"{lon} is not a real longitude, must be between -180 and 180")

    # The Haversine formula needs angles in radians, not the degrees
    # latitude and longitude are normally given in, so we convert first.
    lat1_rad = math.radians(lat1)
    lon1_rad = math.radians(lon1)
    lat2_rad = math.radians(lat2)
    lon2_rad = math.radians(lon2)

    # How far apart the two points are, in radians, along each axis.
    delta_lat = lat2_rad - lat1_rad
    delta_lon = lon2_rad - lon1_rad

    # This is the Haversine formula itself. It accounts for the Earth
    # being a sphere, not a flat grid, so it stays accurate even for
    # points far apart, unlike simple Pythagorean distance would be.
    a = (
        math.sin(delta_lat / 2) ** 2
        + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(delta_lon / 2) ** 2
    )
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    miles = EARTH_RADIUS_MILES * c
    return round(miles, 1)


if __name__ == "__main__":
    # Real test: Nashville's Hard Rock Cafe to Nashville's Pancake Pantry,
    # two real places from our own earlier test runs.
    result = calculate_distance(36.1623537, -86.7749578, 36.1589312, -86.7741267)
    print(f"{result} miles")
