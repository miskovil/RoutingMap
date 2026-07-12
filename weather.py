import requests
from datetime import datetime

def get_weather(lat, lon, timestamp):
    """
    Fetches weather for given lat, lon and timestamp using Open-Meteo.
    Open-Meteo is free and doesn't require an API key for non-commercial use.
    timestamp: Unix timestamp
    """
    dt = datetime.fromtimestamp(timestamp)
    date_str = dt.strftime('%Y-%m-%d')
    hour = dt.hour
    
    # Open-Meteo Forecast API
    url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&hourly=temperature_2m,weathercode,relative_humidity_2m,wind_speed_10m&start_date={date_str}&end_date={date_str}"
    
    response = requests.get(url)
    if response.status_code != 200:
        return {"error": f"Weather API error: {response.status_code}"}
    
    data = response.json()
    if 'hourly' not in data:
        return {"error": "No hourly data in response"}
    
    # Get the data for the specific hour
    temp = data['hourly']['temperature_2m'][hour]
    code = data['hourly']['weathercode'][hour]
    humidity = data['hourly']['relative_humidity_2m'][hour]
    wind = data['hourly']['wind_speed_10m'][hour]
    
    return {
        "temperature": temp,
        "weather_code": code,
        "humidity": humidity,
        "wind_speed": wind,
        "description": get_weather_description(code)
    }

def get_weather_description(code):
    """
    Translates WMO weather codes to readable descriptions.
    """
    codes = {
        0: "Clear sky",
        1: "Mainly clear", 2: "Partly cloudy", 3: "Overcast",
        45: "Fog", 48: "Depositing rime fog",
        51: "Light drizzle", 53: "Moderate drizzle", 55: "Dense drizzle",
        56: "Light freezing drizzle", 57: "Dense freezing drizzle",
        61: "Slight rain", 63: "Moderate rain", 65: "Heavy rain",
        66: "Light freezing rain", 67: "Heavy freezing rain",
        71: "Slight snow fall", 73: "Moderate snow fall", 75: "Heavy snow fall",
        77: "Snow grains",
        80: "Slight rain showers", 81: "Moderate rain showers", 82: "Violent rain showers",
        85: "Slight snow showers", 86: "Heavy snow showers",
        95: "Thunderstorm", 96: "Thunderstorm with slight hail", 99: "Thunderstorm with heavy hail"
    }
    return codes.get(code, f"Unknown code {code}")
