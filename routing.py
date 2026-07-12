import requests
import polyline
import random
from math import radians, cos, sin, sqrt, atan2

def get_route(start_coords, end_coords):
    """
    Fetches route from OSRM API.
    start_coords: (lat, lon)
    end_coords: (lat, lon)
    Returns: List of (lat, lon) points and duration in seconds.
    """
    url = f"http://router.project-osrm.org/route/v1/driving/{start_coords[1]},{start_coords[0]};{end_coords[1]},{end_coords[0]}?overview=full&geometries=polyline"
    response = requests.get(url)
    if response.status_code != 200:
        raise Exception(f"Error fetching route: {response.text}")
    
    data = response.json()
    if data['code'] != 'Ok':
        raise Exception(f"OSRM Error: {data['code']}")
    
    route = data['routes'][0]
    geometry = route['geometry']
    duration = route['duration']
    
    points = polyline.decode(geometry)
    return points, duration

def geocode(address):
    """
    Simple geocoding using Nominatim (OSM).
    Returns (lat, lon, display_name)
    """
    url = f"https://nominatim.openstreetmap.org/search?q={address}&format=json&limit=1"
    headers = {'User-Agent': 'WeatherRouteApp/1.0'}
    response = requests.get(url, headers=headers)
    if response.status_code != 200:
        raise Exception(f"Error geocoding: {response.text}")
    
    data = response.json()
    if not data:
        raise Exception(f"Address not found: {address}")
    
    return float(data[0]['lat']), float(data[0]['lon']), data[0]['display_name']

def get_suggestions(query):
    """
    Fetches location suggestions from Nominatim.
    """
    if not query or len(query) < 3:
        return []

    url = f"https://nominatim.openstreetmap.org/search?q={query}&format=json&limit=5"
    headers = {'User-Agent': 'WeatherRouteApp/1.0'}
    try:
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            data = response.json()
            return [item['display_name'] for item in data]
    except Exception:
        pass
    return []

def calculate_stops(distance_km, duration_seconds, fuel_consumption, tank_size, rest_interval_hours, optimize_cost=True, fuel_at_start=None):
    """
    Calculate optimal stops for fuel and rest along the route.

    Args:
        distance_km: Total route distance in km
        duration_seconds: Total route duration in seconds
        fuel_consumption: L/100km
        tank_size: Tank size in liters
        rest_interval_hours: Desired rest interval in hours
        optimize_cost: Whether to optimize for fuel cost
        fuel_at_start: Fuel in tank at start (defaults to full tank)

    Returns:
        List of stop dictionaries with distance, time, type, and fuel info
    """
    stops = []

    # Calculate max distance per tank (with 10% safety buffer)
    max_distance_per_tank = (tank_size / fuel_consumption * 100) * 0.9

    # Calculate rest interval in seconds
    rest_interval_seconds = rest_interval_hours * 3600

    # Track current state
    current_distance = 0
    current_time = 0
    fuel_in_tank = fuel_at_start if fuel_at_start is not None else tank_size
    last_rest_time = 0

    avg_speed_kmh = (distance_km / duration_seconds) * 3600 if duration_seconds > 0 else 80

    # Pre-generate fuel prices along route for look-ahead optimization
    num_segments = max(int(distance_km / 50), 10)  # Price segment every ~50km
    segment_prices = []
    for i in range(num_segments):
        # Simulate varying prices along route (in reality, would query real prices per location)
        if optimize_cost:
            price = random.uniform(1.35, 1.75)
        else:
            price = random.uniform(1.50, 1.70)
        segment_prices.append(price)

    while current_distance < distance_km:
        # Calculate distances to next required stops
        distance_to_empty = (fuel_in_tank / fuel_consumption * 100) * 0.9
        distance_to_rest = (rest_interval_seconds - (current_time - last_rest_time)) / 3600 * avg_speed_kmh
        distance_remaining = distance_km - current_distance

        # Determine next stop type and distance
        next_stop_distance = min(distance_to_empty, distance_to_rest, distance_remaining)

        if next_stop_distance >= distance_remaining:
            # Reached destination
            break

        current_distance += next_stop_distance
        current_time += (next_stop_distance / avg_speed_kmh) * 3600

        # Update fuel
        fuel_used = next_stop_distance * fuel_consumption / 100
        fuel_in_tank -= fuel_used

        need_fuel = fuel_in_tank < tank_size * 0.3  # Refuel when below 30%
        need_rest = (current_time - last_rest_time) >= rest_interval_seconds * 0.9

        # Get current location's fuel price
        current_segment = min(int(current_distance / distance_km * num_segments), num_segments - 1)
        current_price = segment_prices[current_segment]

        # If optimizing cost, look ahead for better prices
        suggest_early_fuel = False
        early_fuel_reason = ""

        if optimize_cost and not need_fuel:
            # Calculate how far we can go with current fuel
            distance_we_can_reach = (fuel_in_tank / fuel_consumption * 100) * 0.9

            # Look ahead at prices we'll encounter
            segments_ahead_start = current_segment + 1
            segments_ahead_end = min(int((current_distance + distance_we_can_reach) / distance_km * num_segments), num_segments - 1)

            if segments_ahead_end > segments_ahead_start:
                future_prices = segment_prices[segments_ahead_start:segments_ahead_end + 1]
                avg_future_price = sum(future_prices) / len(future_prices) if future_prices else current_price
                min_future_price = min(future_prices) if future_prices else current_price

                # If current price is significantly cheaper than average future prices, fuel up now
                price_difference = avg_future_price - current_price
                if price_difference > 0.08 and fuel_in_tank < tank_size * 0.7:  # More than 8 cents cheaper
                    suggest_early_fuel = True
                    savings_per_liter = round(price_difference * 100, 1)
                    early_fuel_reason = f"💰 Fuel cheaper here! Save ~€{savings_per_liter}¢/L vs. upcoming stations"
                # Also suggest if resting and might need fuel before next rest
                elif need_rest:
                    time_until_next_rest = rest_interval_seconds
                    distance_until_next_rest = time_until_next_rest / 3600 * avg_speed_kmh
                    fuel_needed_until_next_rest = distance_until_next_rest * fuel_consumption / 100

                    if fuel_in_tank < fuel_needed_until_next_rest + (tank_size * 0.3):
                        suggest_early_fuel = True
                        early_fuel_reason = "Recommended to fuel now during rest to avoid extra stop later"

        if need_fuel or need_rest or suggest_early_fuel:
            fuel_to_add = tank_size - fuel_in_tank if (need_fuel or suggest_early_fuel) else 0

            stop_type = 'Fuel & Rest' if (need_fuel or suggest_early_fuel) and need_rest else ('Fuel' if need_fuel or suggest_early_fuel else 'Rest')

            stop = {
                'distance_km': round(current_distance, 1),
                'time_hours': round(current_time / 3600, 2),
                'type': stop_type,
                'fuel_to_add': round(fuel_to_add, 1),
                'fuel_price_per_liter': round(current_price, 3),
                'fuel_cost': round(fuel_to_add * current_price, 2),
                'fuel_remaining_before': round(fuel_in_tank, 1),
                'optimize_cost': optimize_cost,
                'suggestion': early_fuel_reason if suggest_early_fuel else ""
            }
            stops.append(stop)

            if need_fuel or suggest_early_fuel:
                fuel_in_tank = tank_size
            if need_rest:
                last_rest_time = current_time

    # Calculate totals
    total_fuel_cost = sum(s['fuel_cost'] for s in stops)
    total_fuel_needed = sum(s['fuel_to_add'] for s in stops)

    return stops, total_fuel_cost, total_fuel_needed

def calculate_distance(lat1, lon1, lat2, lon2):
    """
    Calculate distance between two points using Haversine formula.

    Returns: Distance in km
    """
    R = 6371  # Earth radius in km
    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)
    a = sin(dlat/2)**2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon/2)**2
    c = 2 * atan2(sqrt(a), sqrt(1-a))
    return R * c

def get_country_from_coords(lat, lon):
    """
    Reverse geocode to get country code from coordinates.

    Returns:
        Country code (e.g., 'DE', 'FR') or None
    """
    try:
        url = f"https://nominatim.openstreetmap.org/reverse?lat={lat}&lon={lon}&format=json&zoom=3"
        headers = {'User-Agent': 'WeatherRouteApp/1.0'}
        response = requests.get(url, headers=headers, timeout=5)
        if response.status_code == 200:
            data = response.json()
            country_code = data.get('address', {}).get('country_code', '').upper()
            return country_code
    except Exception:
        pass
    return None

def get_openvan_fuel_prices():
    """
    Get real fuel prices from OpenVan.camp API (free, no API key required).
    Covers 134 countries including all of Europe.

    Returns:
        Dict mapping country codes to fuel prices, or None if failed
    """
    try:
        url = "https://openvan.camp/api/fuel/prices"
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            data = response.json()
            if data.get('success'):
                prices_by_country = {}
                for country_code, country_data in data.get('data', {}).items():
                    prices = country_data.get('prices', {})
                    if prices.get('diesel') or prices.get('gasoline'):
                        prices_by_country[country_code] = {
                            'country_name': country_data.get('country_name'),
                            'diesel': prices.get('diesel'),
                            'gasoline': prices.get('gasoline'),
                            'lpg': prices.get('lpg'),
                            'currency': country_data.get('currency'),
                            'unit': country_data.get('unit', 'liter')
                        }
                return prices_by_country
    except Exception as e:
        print(f"OpenVan API error: {e}")
        pass

    return None

def find_nearby_stations(lat, lon, radius_km=5, optimize_cost=True, max_detour_km=5, fuel_type="Diesel"):
    """
    Find nearby gas stations with real or simulated prices.

    Args:
        lat: Latitude
        lon: Longitude
        radius_km: Search radius in km
        optimize_cost: If True, prioritize cheapest stations
        max_detour_km: Maximum detour distance to consider
        fuel_type: Type of fuel (Diesel, Gasoline (E5/E10), or LPG)

    Returns:
        List of gas station dictionaries with name, coordinates, price, and distance
    """
    # Get country code for this location
    country_code = get_country_from_coords(lat, lon)

    # Try to get real prices from OpenVan.camp API
    openvan_prices = get_openvan_fuel_prices()
    real_price = None
    country_name = None

    # Map fuel type to API field
    fuel_field_map = {
        "Diesel": "diesel",
        "Gasoline (E5/E10)": "gasoline",
        "LPG": "lpg"
    }
    fuel_field = fuel_field_map.get(fuel_type, "diesel")

    if openvan_prices and country_code and country_code in openvan_prices:
        country_data = openvan_prices[country_code]
        # Get price for selected fuel type
        real_price = country_data.get(fuel_field)
        country_name = country_data.get('country_name')
        currency = country_data.get('currency', 'EUR')

    radius_m = radius_km * 1000
    overpass_url = "http://overpass-api.de/api/interpreter"

    query = f"""
    [out:json][timeout:25];
    (
      node["amenity"="fuel"](around:{radius_m},{lat},{lon});
      way["amenity"="fuel"](around:{radius_m},{lat},{lon});
    );
    out center 20;
    """

    try:
        response = requests.get(overpass_url, params={'data': query}, timeout=10)
        if response.status_code == 200:
            data = response.json()
            stations = []
            for element in data.get('elements', []):
                tags = element.get('tags', {})
                name = tags.get('name', 'Gas Station')
                brand = tags.get('brand', '')
                if brand:
                    name = f"{brand}" if name == 'Gas Station' else f"{brand} - {name}"

                # Get address information
                street = tags.get('addr:street', '')
                housenumber = tags.get('addr:housenumber', '')
                city = tags.get('addr:city', '')
                postcode = tags.get('addr:postcode', '')

                # Build address string
                address_parts = []
                if street:
                    addr = f"{street} {housenumber}".strip() if housenumber else street
                    address_parts.append(addr)
                if postcode or city:
                    city_part = f"{postcode} {city}".strip() if postcode and city else (postcode or city)
                    address_parts.append(city_part)
                address = ", ".join(address_parts) if address_parts else "Address not available"

                # Get coordinates
                if element['type'] == 'node':
                    station_lat = element['lat']
                    station_lon = element['lon']
                    osm_id = element.get('id')
                    osm_type = 'node'
                else:  # way
                    station_lat = element.get('center', {}).get('lat', lat)
                    station_lon = element.get('center', {}).get('lon', lon)
                    osm_id = element.get('id')
                    osm_type = 'way'

                # Create OpenStreetMap link
                osm_link = f"https://www.openstreetmap.org/{osm_type}/{osm_id}"
                google_maps_link = f"https://www.google.com/maps?q={station_lat},{station_lon}"

                # Calculate distance from stop point
                distance = calculate_distance(lat, lon, station_lat, station_lon)

                # Filter by max detour distance
                if distance > max_detour_km:
                    continue

                # Use real price if available, otherwise simulate
                if real_price:
                    # Add small variation to account for station-specific pricing
                    price_variation = random.uniform(-0.05, 0.05) if optimize_cost else random.uniform(-0.02, 0.02)
                    price = real_price + price_variation
                    price_source = "OpenVan"
                else:
                    # Fallback to simulated prices
                    if optimize_cost:
                        price = random.uniform(1.35, 1.65)
                    else:
                        price = random.uniform(1.50, 1.70)
                    price_source = "Estimated"

                stations.append({
                    'name': name,
                    'address': address,
                    'lat': station_lat,
                    'lon': station_lon,
                    'price_per_liter': round(price, 3),
                    'distance_km': round(distance, 1),
                    'price_source': price_source,
                    'country': country_name if country_name else 'Unknown',
                    'osm_link': osm_link,
                    'google_maps_link': google_maps_link
                })

            # Sort by price (cheapest first), then by distance
            stations.sort(key=lambda x: (x['price_per_liter'], x['distance_km']))

            # Return top 5 cheapest within detour range
            return stations[:5]
    except Exception as e:
        print(f"Station search error: {e}")
        pass

    # Fallback: return generic station
    fallback_price = real_price if real_price else random.uniform(1.50, 1.70)
    google_maps_link = f"https://www.google.com/maps?q={lat},{lon}"
    return [
        {
            'name': 'Gas Station (nearby)',
            'address': 'Address not available',
            'lat': lat,
            'lon': lon,
            'price_per_liter': round(fallback_price, 2),
            'distance_km': 0,
            'price_source': 'OpenVan' if real_price else 'Estimated',
            'country': country_name if country_name else 'Unknown',
            'osm_link': google_maps_link,
            'google_maps_link': google_maps_link
        }
    ]
