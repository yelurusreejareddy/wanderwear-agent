"""
weather.py -- second tool, practice, written by Sreeja.
Takes a latitude and longitude, returns the current temperature.
"""
import requests

OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"


def get_weather(lat, lon):
    """Look up the current weather for a latitude and longitude."""

    # Same idea as geocode.py's params dict, just different fields,
    # because Open-Meteo expects different search terms than Nominatim did.
    params = {
        "latitude": lat,
        "longitude": lon,
        "current": "temperature_2m,weather_code",
    }

    response = requests.get(OPEN_METEO_URL, params=params)
    data = response.json()

    ## TO-DO: look at the raw JSON we printed above. The temperature and
    ## weather code are not at the top level of "data", they are one level
    ## deeper, inside a dictionary stored under the key "current".
    ## First, pull that inner dictionary out into its own variable.
    current = data["current"]
    ## TO-DO: from that inner dictionary, pull out the value stored under
    ## "temperature_2m" and the value stored under "weather_code".
    temp,weather = current["temperature_2m"],current["weather_code"]
    ## TO-DO: build and return a new, clean dictionary, same idea as the
    ## one at the bottom of geocode_city, with just two keys of your
    ## choice, holding the temperature and the weather code.
    result = {"temperature_2m":temp, "weather_code":weather}
    return result

if __name__ == "__main__":
    result = get_weather(36.1622767, -86.7742984)
    print(result)
