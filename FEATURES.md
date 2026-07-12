# WeatherApp Route Planner - Features Summary

## Recent Updates

### 0. Rate Limiting & Caching (NEW)
The app now handles Nominatim API rate limits gracefully:

- **Automatic Rate Limiting** - Enforces 1.1s minimum between geocoding requests (respects free tier limits)
- **Intelligent Caching** - Lookup results cached to avoid repeated API calls for same locations
- **Retry Logic** - Automatic retry with exponential backoff (2s, 4s, 8s) on 429 errors
- **User-Friendly Error Messages** - Clear guidance when rate limits are hit
- **Cache Management** - "Clear Location Cache" button in sidebar to reset if needed

**Benefits:**
- Prevents "429 Too Many Requests" errors
- Faster repeated lookups (cache hits are instant)
- Graceful recovery from temporary API issues
- Users can continue work while experiencing transient issues

### 1. Routing Preferences & Options
The app now allows users to select a variety of routing preferences:

- **Avoid Toll Roads** - Routes around toll highways where possible
- **Avoid Highways/Motorways** - Prefers smaller roads for a scenic route
- **Avoid Ferries** - Skips routes requiring ferry crossings
- **Prefer Fuel-Economical Route** - Selects the shortest distance option among alternatives for better fuel efficiency

**Location**: Sidebar → Routing Options (below vehicle settings)

### 2. Visual Routing Indicator
When a route is calculated, the app now displays which preferences were applied:

Example: 
```
Route found! Distance: 245.3 km | Travel time: 3h 22m | Applied: 🚫 No tolls • ⛽ Fuel economical
```

Applied indicators include:
- 🚫 No tolls
- 🚫 No highways
- 🚫 No ferries
- ⛽ Fuel economical

### 3. European Vignette Detection & Management
The app automatically detects when your route passes through countries requiring vignettes (toll stickers):

**Supported Countries (16 total):**
- Austria (AT)
- Bulgaria (BG)
- Croatia (HR)
- Czechia (CZ)
- Denmark (DK)
- Estonia (EE)
- Hungary (HU)
- Latvia (LV)
- Lithuania (LT)
- Luxembourg (LU)
- Poland (PL)
- Romania (RO)
- Slovakia (SK)
- Slovenia (SI)
- Sweden (SE)
- Switzerland (CH)

**Workflow:**
1. Calculate route
2. App checks all countries along the route
3. If vignettes required: displays list and asks which ones you own
4. If missing vignettes: offers to re-route avoiding tolls/highways
5. Click "Attempt re-route" to find alternate path requiring fewer vignettes

### 4. Live Traffic Support (Optional)
The app can use live traffic data when a TomTom API key is provided:

**To Enable:**
```powershell
$env:TOMTOM_API_KEY = 'your_tomtom_api_key_here'
streamlit run app.py
```

When enabled, traffic multiplier uses real-time speed data near your starting point. Falls back to time-of-day heuristic if API key not available or unavailable.

## Implementation Details

### Backend Changes

#### `routing.py`
- **`get_route()`** - NEW parameters:
  - `avoid_tolls=False` - Excludes toll roads from OSRM
  - `avoid_highways=False` - Excludes motorways from OSRM
  - `avoid_ferries=False` - Excludes ferries from OSRM
  - `fuel_economical=False` - Requests alternatives and picks shortest distance

- **`get_traffic_multiplier()`** - ENHANCED:
  - Now accepts optional `start_coords` parameter
  - Attempts TomTom Flow API query if `TOMTOM_API_KEY` env var is set
  - Falls back to time-of-day heuristic if API unavailable

#### `app.py`
- Added sidebar routing preferences controls
- Route calculation passes user preferences to `get_route()`
- Visual indicator logic shows applied routing options
- Vignette detection samples 20 points along route
- Multiselect UI for owned vignettes
- Re-route button with automatic toll/highway avoidance
- Distance recalculation after re-routing

### Frontend Changes
- New "Routing Options" section in sidebar with 4 checkboxes
- Enhanced route result display with applied options indicator
- Vignette warning section (appears when needed)
- Vignette selection widget and re-route button

## Testing

All changes have been tested and verified:

✅ `test_routing_functions.py` - Traffic multiplier logic
✅ `test_ui_changes.py` - Visual indicator and vignette list
✅ `test_route_signature.py` - Function signatures and defaults
✅ `test_app.py` - Original API integration tests still pass

## Usage Examples

### Basic Route (No Preferences)
1. Enter start and end locations
2. Click "Get Weather for Route"
3. View results

### Economical Route
1. Enter locations
2. Check "Prefer fuel-economical route"
3. Optionally check "Avoid toll roads"
4. Click "Get Weather for Route"
5. See route with visual indicators

### European Route with Vignettes
1. Enter European locations (e.g., Munich to Vienna)
2. Click "Get Weather for Route"
3. If route passes through vignette countries:
   - You'll see warning: "This route passes through countries that may require vignettes: Austria (AT), Czechia (CZ)"
   - Select which vignettes you own
   - If missing: Click "Attempt re-route" to avoid toll roads/highways
4. New route calculated without tolls

### With Live Traffic (Advanced)
1. Set environment variable: `$env:TOMTOM_API_KEY = 'your_key'`
2. Start app: `streamlit run app.py`
3. Route calculations will use real-time traffic from TomTom API
4. Traffic delays shown in warning if heavy traffic detected

## Technical Notes

- OSRM (Open Source Routing Machine) used for routing - free, keyless
- Nominatim API used for geocoding and reverse geocoding
  - **Rate Limiting**: 1.1 second minimum between requests (free tier: max 1 req/sec)
  - **Caching**: Geocoding results cached in memory to avoid repeated API calls
  - **Retry Logic**: Automatic exponential backoff (2s, 4s, 8s) on rate limit errors
  - **Cache Management**: Users can clear cache via sidebar button
- Live traffic (TomTom) is optional - app works without API key
- Vignette country list is in-code and can be easily updated
- All routing logic is backward compatible
- Fuel economical routing doesn't increase costs, only considers distance

## Rate Limiting & Caching (Details)

### How It Works
1. **Request Throttling**: Each Nominatim geocoding request enforces 1.1 second minimum delay
2. **Smart Cache**: Successful geocoding results stored in memory (persists within session)
3. **Automatic Retry**: On 429 errors, retries with increasing delays (2s → 4s → 8s)
4. **Cache Clearing**: Users can reset cache anytime via sidebar button

### Benefits
- **No More 429 Errors**: Rate limiting prevents hitting API limits
- **Faster Performance**: Repeated location lookups are instant (cache hits)
- **Better Reliability**: Auto-retry recovers from temporary issues
- **User Control**: Manual cache clear available when needed

### Error Handling
When rate limit errors occur, users see:
- Clear explanation of the issue
- 4 suggested solutions:
  1. Wait a moment and try again
  2. Click "Clear Location Cache" button
  3. Try different location names
  4. Refresh the page
- Helpful tips for other error types (address not found, no routes, etc.)

## Future Enhancements

Potential improvements:
- ~~Add rate limiting for Nominatim API~~ ✅ DONE
- ~~Add geocoding cache to reduce API calls~~ ✅ DONE
- Add more vignette countries (e.g., Norway toll roads)
- Integrate OpenRouteService or GraphHopper for more granular avoid options
- Cache vignette preferences in session state
- Add real-time vignette pricing lookup
- Support for other traffic APIs (HERE, Mapbox)
- Persistent session cache (LocalStorage) to cache across browser sessions

