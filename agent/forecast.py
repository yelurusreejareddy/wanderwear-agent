"""
forecast.py -- third tool, practice, written by Sreeja.
Takes a latitude, longitude, and a date range, returns one weather summary
per day. Unlike weather.py's "current", this can answer future questions
like "what's the weather next weekend."
"""
import requests

OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"


def get_forecast(lat, lon, start_date, end_date):
    """Look up the daily forecast between start_date and end_date.
    Dates must be text in "YYYY-MM-DD" form, e.g. "2026-08-08"."""

    params = {
        "latitude": lat,
        "longitude": lon,
        "daily": "temperature_2m_max,temperature_2m_min,weather_code",
        "start_date": start_date,
        "end_date": end_date,
        "timezone": "America/Chicago",
    }

    response = requests.get(OPEN_METEO_URL, params=params)
    data = response.json()

    ## TO-DO: pull the "daily" dictionary out of data into its own variable,
    ## same idea as pulling "current" out in weather.py.
    daily = data["daily"]

    ## TO-DO: we want to return a LIST of dictionaries, one per day, like:
    ## [{"date": "2026-08-08", "high_c": 33.1, "low_c": 24.1, "weather_code": 51}, ...]
    ##
    ## Start with an empty list to fill in as we go.
    days = []

    ## TO-DO: loop over each day's position. daily["time"] is a list of
    ## dates, so len(daily["time"]) tells you how many days there are.
    ## For each position i, read daily["time"][i], daily["temperature_2m_max"][i],
    ## daily["temperature_2m_min"][i], and daily["weather_code"][i], build
    ## one small dictionary from those four values, and add it to "days"
    ## using days.append(...).
    for i in range(len(daily["time"])):
        day = {"date":daily["time"][i], "high_c":daily["temperature_2m_max"][i], "low_c":daily["temperature_2m_min"][i], "weather_code":daily["weather_code"][i]}# replace this line with your code
        days.append(day)
    return days


if __name__ == "__main__":
    result = get_forecast(36.1622767, -86.7742984, "2026-08-08", "2026-08-09")
    print(result)
