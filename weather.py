"""
Weather Tool using Open-Meteo (no API key required)
"""

import requests
from langchain_core.tools import tool

# WMO weather code → human-readable description
WMO_CODES = {
    0: "Clear sky", 1: "Mainly clear", 2: "Partly cloudy", 3: "Overcast",
    45: "Foggy", 48: "Icy fog",
    51: "Light drizzle", 53: "Drizzle", 55: "Heavy drizzle",
    61: "Light rain", 63: "Rain", 65: "Heavy rain",
    71: "Light snow", 73: "Snow", 75: "Heavy snow", 77: "Snow grains",
    80: "Light showers", 81: "Showers", 82: "Violent showers",
    85: "Snow showers", 86: "Heavy snow showers",
    95: "Thunderstorm", 96: "Thunderstorm with hail", 99: "Heavy thunderstorm with hail",
}


def _geocode(city: str) -> dict | None:
    """Resolve city name → lat/lon via Open-Meteo geocoding API."""
    try:
        resp = requests.get(
            "https://geocoding-api.open-meteo.com/v1/search",
            params={"name": city, "count": 1, "language": "en", "format": "json"},
            timeout=10,
        )
        resp.raise_for_status()
        results = resp.json().get("results")
        if not results:
            return None
        r = results[0]
        return {
            "name": r["name"],
            "country": r.get("country", ""),
            "lat": r["latitude"],
            "lon": r["longitude"],
        }
    except requests.RequestException:
        return None


@tool
def get_weather(city: str) -> str:
    """
    Get the current weather for any city worldwide.

    Args:
        city: City name, e.g. "London", "Karachi", "New York"

    Returns:
        A human-readable weather summary as plain text (no HTML or markdown).
    """
    location = _geocode(city)
    if not location:
        return f"Could not find location data for '{city}'. Please check the spelling."

    try:
        resp = requests.get(
            "https://api.open-meteo.com/v1/forecast",
            params={
                "latitude": location["lat"],
                "longitude": location["lon"],
                "current_weather": True,
                "hourly": "relative_humidity_2m",
                "forecast_days": 1,
            },
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()
    except requests.RequestException as e:
        return f"Weather service error: {e}"

    current = data.get("current_weather")
    if not current:
        return f"Weather data unavailable for '{city}'."

    temp_c    = current["temperature"]
    temp_f    = round(temp_c * 9 / 5 + 32, 1)
    wind_kph  = round(current["windspeed"], 1)
    wind_mph  = round(wind_kph * 0.621371, 1)
    condition = WMO_CODES.get(current.get("weathercode", -1), "Unknown")
    obs_time  = current.get("time", "N/A")

    # Best-effort humidity (first hourly value)
    humidity_list = data.get("hourly", {}).get("relative_humidity_2m", [])
    humidity_str  = f"\nHumidity:     {humidity_list[0]}%" if humidity_list else ""

    return (
        f"Location:     {location['name']}, {location['country']}\n"
        f"Condition:    {condition}\n"
        f"Temperature:  {temp_c}C / {temp_f}F\n"
        f"Wind Speed:   {wind_kph} km/h ({wind_mph} mph)"
        f"{humidity_str}\n"
        f"Observed at:  {obs_time}"
    )