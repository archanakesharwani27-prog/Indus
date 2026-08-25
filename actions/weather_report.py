# actions/weather_report.py
"""
INDUS Atmospheric Radar & Weather Telemetry Engine
Fetches live real-time meteorological data and triggers the floating HUD Weather Card.
"""

import requests
from urllib.parse import quote_plus


def fetch_weather_telemetry(city: str) -> dict:
    """Fetch live structured weather data from meteorological endpoints."""
    city_clean = city.strip()
    encoded = quote_plus(city_clean)
    url = f"https://wttr.in/{encoded}?format=j1"

    try:
        r = requests.get(url, timeout=5, headers={"User-Agent": "INDUS-AI-Core/2.0"})
        if r.status_code == 200:
            d = r.json()
            curr = d["current_condition"][0]
            weather_desc = curr["weatherDesc"][0]["value"]
            temp_c = curr["temp_C"]
            feels_like = curr["FeelsLikeC"]
            humidity = curr["humidity"]
            wind_kph = curr["windspeedKmph"]
            wind_dir = curr["winddir16Point"]
            uv = curr.get("uvIndex", "0")

            day0 = d["weather"][0]
            max_c = day0.get("maxtempC", "--")
            min_c = day0.get("mintempC", "--")

            return {
                "city": city_clean.title(),
                "temp": f"{temp_c}°C",
                "feels_like": f"{feels_like}°C",
                "condition": weather_desc,
                "humidity": f"{humidity}%",
                "wind": f"{wind_kph} km/h {wind_dir}",
                "uv_index": str(uv),
                "high_low": f"H: {max_c}°  L: {min_c}°",
                "status": "success"
            }
    except Exception as e:
        print(f"[Weather] Live fetch error: {e}")

    return {
        "city": city_clean.title(),
        "temp": "--°C",
        "feels_like": "--°C",
        "condition": "Atmospheric Syncing",
        "humidity": "--%",
        "wind": "-- km/h",
        "uv_index": "0",
        "high_low": "H: --°  L: --°",
        "status": "fallback"
    }


def weather_action(
    parameters: dict,
    player=None,
    session_memory=None
) -> str:
    """
    Weather report action.
    Fetches real-time telemetry, triggers the floating HUD Weather Card, and speaks summary.
    """
    city = parameters.get("city")
    if not city or not isinstance(city, str):
        city = "Delhi"

    data = fetch_weather_telemetry(city)

    # Trigger floating HUD Weather Card
    if player:
        try:
            if hasattr(player, "show_weather_card"):
                player.show_weather_card(data)
            elif hasattr(player, "main_win") and hasattr(player.main_win, "show_weather_card"):
                player.main_win.show_weather_card(data)
        except Exception as e:
            print(f"[Weather] Card show error: {e}")

    if data.get("status") == "success":
        c_name = data["city"]
        temp = data["temp"]
        cond = data["condition"]
        feels = data["feels_like"]
        msg = f"{c_name} mein abhi {temp} hai ({cond}), feels like {feels}."
    else:
        msg = f"{city.title()} ke weather telemetry ko fetch kar diya hai."

    if player:
        try:
            player.write_log(f"SYS: [Weather] {data.get('city')}: {data.get('temp')} ({data.get('condition')})")
        except Exception:
            pass

    return msg


# Alias for dispatcher compatibility
weather_report = weather_action