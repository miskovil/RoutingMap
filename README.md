# Route Weather App

An application that provides weather forecasts along a driving route.

## Features
- Enter start and destination locations.
- Select departure date and time in the future.
- Displays route on a map.
- Provides weather conditions (temperature, wind, description) at multiple points along the route based on estimated arrival time at each point.

## Technologies Used
- **Streamlit**: Web interface.
- **OSRM (OpenStreetMap)**: Routing and travel time calculation.
- **Nominatim (OpenStreetMap)**: Geocoding.
- **Open-Meteo**: Weather forecast data (Free, no API key required).

## How to Run
1. Install dependencies:
   ```bash
   pip install requests polyline streamlit pandas
   ```
2. Run the application:
   ```bash
   python -m streamlit run app.py
   ```
   Or use the provided `run.bat` file on Windows.

## Project Structure
- `app.py`: Main Streamlit application.
- `routing.py`: Module for geocoding and fetching routes.
- `weather.py`: Module for fetching weather data.
- `test_app.py`: Simple test script for core functionality.
