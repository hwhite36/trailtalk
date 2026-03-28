from google.genai import types
import requests
import logging

# Define the get_weather tool so Gemini knows how to use it
get_weather_declaration = {
    "name": "get_weather",
    "description": "Fetch the hourly and week's weather forecast for a specific location defined via latitude and "
                   "longitude coordinates",
    "parameters": {
        "type": "object",
        "properties": {
            "latitude": {
                "type": "number",
                "description": "Latitude of the location for which to fetch the weather",
            },
            "longitude": {
                "type": "number",
                "description": "Longitude of the location for which to fetch the weather",
            },
        },
        "required": ["latitude", "longitude"],
    },
}

weather_tool = types.Tool(function_declarations=[types.FunctionDeclaration(**get_weather_declaration)])

ERROR_RESPONSE = {
        "status": "failed",
        "message": "The weather service is currently unavailable. Please apologize to the user."
    }

def get_weather(latitude: float, longitude: float):
    """
    Fetch the hourly and week's weather forecast from NOAA
    There are 3 API calls to the NOAA API:
    1. Fetch the forecast zone URLs from the coordinates endpoint, which gives us the other two endpoints to hit
    2. Fetch the general (week's) forecast
    3. Fetch the hourly forecast

    :param latitude: latitude coordinate of the location for which to fetch the weather
    :param longitude: longitude coordinate of the location for which to fetch the weather
    :return: a dictionary with the hourly and week's weather forecast
    """
    # NOAA API doesn't require any auth or API keys lol, but we'll include a User-Agent as a gesture of good faith
    headers = {"Accept": "application/geo+json", "User-Agent": "TrailTalk/1.0"}
    coords_metadata_url = f"https://api.weather.gov/points/{latitude},{longitude}"

    try:
        # First we have to get the 2.5km "zone" forecast link from the user's coords
        coords_metadata_resp = requests.get(coords_metadata_url, headers=headers)
        coords_metadata_resp.raise_for_status()
        coords_metadata_json = coords_metadata_resp.json()
        general_forecast_url = coords_metadata_json["properties"]["forecast"]
        hourly_forecast_url = coords_metadata_json["properties"]["forecastHourly"]
        if not general_forecast_url or not hourly_forecast_url:
            return {**ERROR_RESPONSE, "technical_details": "Unable to determine URL required for fetching forecast"}

        # Now we fetch the actual forecast data
        gen_forecast_resp = requests.get(general_forecast_url, headers=headers)
        gen_forecast_resp.raise_for_status()
        gen_forecast_json = gen_forecast_resp.json()
        hourly_forecast_resp = requests.get(hourly_forecast_url, headers=headers)
        hourly_forecast_resp.raise_for_status()
        hourly_forecast_json = hourly_forecast_resp.json()

        # only give 24 hrs of hourly data to the model
        hourly_forecast_24hrs: list = hourly_forecast_json["properties"]["periods"][:24]
        week_forecast: list = gen_forecast_json["properties"]["periods"]

        return {"Hourly forecast": hourly_forecast_24hrs, "Week's forecast": week_forecast}

    except requests.exceptions.HTTPError as e:
        logging.error(e)
        if e.response.status_code == 404:
            return {**ERROR_RESPONSE, "technical_details": "No NOAA weather forecast available for requested location"}
        return {**ERROR_RESPONSE, "technical_details": str(e)}
