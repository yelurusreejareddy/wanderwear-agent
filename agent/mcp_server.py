"""
mcp_server.py -- our own MCP server, wrapping a tool we already built.
Run this file directly and it becomes a real MCP server, speaking the
standard protocol, that any MCP client could plug into, not just our own
loop.py. We are not writing new tool logic here, geocode_city already
exists and already works, we are only wrapping it.
"""
from mcp.server import MCPServer

from geocode import geocode_city
from weather import get_weather
from forecast import get_forecast
from places import find_places
from distance import calculate_distance

# This is the actual MCP server object. "personal-agent-tools" is just its
# name, what a client sees when it asks "who am I talking to".
server = MCPServer(name="personal-agent-tools")


# @server.tool() is the decorator from our last lesson. It reads this
# function's own name, docstring, and parameter types, and automatically
# builds the same kind of JSON description we hand-wrote for Groq's TOOLS
# list. We never write that JSON ourselves here, it is generated from
# exactly what is already true about geocode_city.
@server.tool()
def geocode(city_name: str) -> dict:
    """Turn a city name into its latitude and longitude."""
    return geocode_city(city_name)


# Same pattern for both weather tools, no new logic, just wrapping what
# already works. Two separate tools on purpose, current weather and a
# dated forecast answer genuinely different questions, see forecast.py.
@server.tool()
def weather(lat: float, lon: float) -> dict:
    """Get the current temperature and weather code for a latitude and
    longitude, right now only, cannot answer about a future date."""
    return get_weather(lat, lon)


@server.tool()
def forecast(lat: float, lon: float, start_date: str, end_date: str) -> list:
    """Get the daily high, low, and weather code for a latitude and
    longitude, for a future date range, format YYYY-MM-DD."""
    return get_forecast(lat, lon, start_date, end_date)


# Same pattern again, no new tool logic, find_places already works, this
# just gives it the same standard MCP "plug shape" as geocode above.
@server.tool()
def places(lat: float, lon: float, category: str) -> list:
    """Find real nearby places of a given category, restaurant, cafe,
    beach, park, museum, viewpoint, attraction, or hotel."""
    return find_places(lat, lon, category=category)


# calculate_distance needs no API at all, real math, so this tool never
# even leaves your own computer, no external call happens here.
@server.tool()
def distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Get the real distance in miles between two latitude/longitude points."""
    return calculate_distance(lat1, lon1, lat2, lon2)


if __name__ == "__main__":
    # "stdio" means this program will talk over stdin and stdout, the
    # same channel we drew in the diagram, not over the real internet.
    server.run(transport="stdio")
