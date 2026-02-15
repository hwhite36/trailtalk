from google.genai import types
import requests

# Define the get_weather tool so Gemini knows how to use it
get_weather_declaration = {
    "name": "get_weather",
    "description": "Fetch the weather for a specific location defined via coordinates",
    "parameters": {
        "type": "object",
        "properties": {
            "latitude": {
                "type": "number",
                "description": "Latitude coordinate of the location for which to fetch the weather",
            },
            "longitude": {
                "type": "number",
                "description": "Longitude coordinate of the location for which to fetch the weather",
            },
        },
        "required": ["latitude", "longitude"],
    },
}

weather_tool = types.Tool(function_declarations=[types.FunctionDeclaration(**get_weather_declaration)])

def get_weather(latitude: float, longitude: float):
    pass
