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
