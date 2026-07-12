# Route Weather App

An application that provides weather forecasts along a driving route.

## Features
- Enter start and destination locations.
- **Rate-Limited & Cached Geocoding**: Automatic rate limiting and caching prevents "429 Too Many Requests" errors
- Select departure date and time in the future.
- **Routing Preferences**: Avoid toll roads, highways, ferries, or prefer fuel-economical routes.
- **Vignette Detection**: Automatically detects if route passes through European countries requiring vignettes (toll stickers). Offers re-routing if you lack required vignettes.
- **Visual Routing Indicator**: Shows which routing preferences were applied to your route.
- Displays route on a map with gas stations and fuel stops.
- Predicts travel time variations based on traffic patterns (uses live traffic via TomTom if API key provided, otherwise time-of-day heuristic).
- Provides weather conditions (temperature, wind, description) at multiple points along the route based on estimated arrival time at each point.
- Fuel stop planning with real or estimated prices from OpenVan.camp API.

## Technologies Used
- **Streamlit**: Web interface.
- **OSRM (OpenStreetMap)**: Routing and travel time calculation.
- **Nominatim (OpenStreetMap)**: Geocoding.
- **Open-Meteo**: Weather forecast data (Free, no API key required).

## How to Run
1. Install dependencies:
   ```bash
   pip install -r requirements.txt
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

## Troubleshooting

### "429 Too Many Requests" Error
If you encounter this error from the geocoding service:

1. **The app now handles this automatically** - It includes:
   - Rate limiting (1 request per second)
   - Intelligent caching of results
   - Automatic retry with exponential backoff

2. **If errors persist**:
   - Click the **"🗑️ Clear Location Cache"** button in the sidebar
   - Try searching for locations with more specific names (e.g., "Paris, France" instead of "Paris")
   - Wait a few moments before trying again
   - Refresh the page to start fresh

3. **How the system prevents rate limits**:
   - All geocoding requests are spaced 1.1+ seconds apart
   - Location results are cached - the same location won't hit the API twice
   - Automatic retry with delays (2s → 4s → 8s) for transient errors
