import streamlit as st
import routing
print(f"DEBUG: routing module file: {routing.__file__}")
import weather
from datetime import datetime, timedelta
import pandas as pd
import time
import pydeck as pdk

st.set_page_config(page_title="Route Weather App", layout="wide")

st.title("🚗 Driving Route Weather Forecast")

with st.sidebar:
    st.header("Route Settings")

    # Use session state to manage suggestions and selection
    if 'start_options' not in st.session_state:
        st.session_state.start_options = ["New York, NY"]
    if 'end_options' not in st.session_state:
        st.session_state.end_options = ["Philadelphia, PA"]

    start_loc_input = st.text_input("Start Location Search", "")
    if start_loc_input:
        suggestions = routing.get_suggestions(start_loc_input)
        if suggestions:
            st.session_state.start_options = suggestions

    start_loc = st.selectbox("Select Start Location", st.session_state.start_options)

    end_loc_input = st.text_input("Destination Search", "")
    if end_loc_input:
        suggestions = routing.get_suggestions(end_loc_input)
        if suggestions:
            st.session_state.end_options = suggestions

    end_loc = st.selectbox("Select Destination", st.session_state.end_options)

    col1, col2 = st.columns(2)
    with col1:
        departure_date = st.date_input("Departure Date", datetime.now().date())
    with col2:
        departure_time = st.time_input("Departure Time", datetime.now().time())

    st.header("Vehicle & Trip Settings")

    fuel_type = st.selectbox("Fuel Type", options=["Diesel", "Gasoline (E5/E10)", "LPG"], index=0)
    fuel_consumption = st.number_input("Average Fuel Consumption (L/100km)", min_value=1.0, max_value=30.0, value=7.5, step=0.1)
    tank_size = st.number_input("Fuel Tank Size (L)", min_value=10.0, max_value=200.0, value=50.0, step=1.0)
    fuel_at_start = st.number_input("Fuel at Start (L)", min_value=0.0, max_value=200.0, value=50.0, step=1.0)
    rest_interval = st.number_input("Rest Interval (hours)", min_value=1.0, max_value=8.0, value=2.0, step=0.5)

    optimize_cost = st.checkbox("Optimize for lowest fuel cost", value=True)
    max_detour_km = st.slider("Max detour for cheaper fuel (km)", min_value=0, max_value=20, value=5, step=1)

    search_button = st.button("Get Weather for Route")

if search_button:
    try:
        with st.spinner("Geocoding locations..."):
            start_coords_data = routing.geocode(start_loc)
            end_coords_data = routing.geocode(end_loc)
            start_coords = (start_coords_data[0], start_coords_data[1])
            end_coords = (end_coords_data[0], end_coords_data[1])
            
        with st.spinner("Calculating route..."):
            points, total_duration = routing.get_route(start_coords, end_coords)

        # Calculate route distance in km
        total_distance_km = 0
        for i in range(len(points) - 1):
            lat1, lon1 = points[i]
            lat2, lon2 = points[i + 1]
            # Haversine formula for distance
            from math import radians, cos, sin, sqrt, atan2
            R = 6371  # Earth radius in km
            dlat = radians(lat2 - lat1)
            dlon = radians(lon2 - lon1)
            a = sin(dlat/2)**2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon/2)**2
            c = 2 * atan2(sqrt(a), sqrt(1-a))
            total_distance_km += R * c

        st.success(f"Route found! Distance: {total_distance_km:.1f} km | Travel time: {int(total_duration // 3600)}h {int((total_duration % 3600) // 60)}m")

        # Calculate fuel stops and rest stops
        with st.spinner("Calculating optimal stops..."):
            stops, total_fuel_cost, total_fuel_needed = routing.calculate_stops(
                total_distance_km,
                total_duration,
                fuel_consumption,
                tank_size,
                rest_interval,
                optimize_cost,
                fuel_at_start
            )
        
        # Departure timestamp
        departure_dt = datetime.combine(departure_date, departure_time)
        departure_ts = departure_dt.timestamp()
        
        # Sample points along the route (every 30 mins or max 10 points)
        num_points = len(points)
        num_samples = min(10, num_points)
        sample_indices = [int(i * (num_points - 1) / (num_samples - 1)) for i in range(num_samples)]
        
        weather_data = []
        
        progress_bar = st.progress(0)
        for i, idx in enumerate(sample_indices):
            point = points[idx]
            
            # Estimate time at this point
            # For simplicity, we assume constant speed. 
            # In a real app, OSRM provides duration between legs.
            fraction = i / (num_samples - 1)
            point_time = departure_ts + (total_duration * fraction)
            
            with st.spinner(f"Fetching weather for point {i+1}..."):
                w = weather.get_weather(point[0], point[1], point_time)
                w['lat'] = point[0]
                w['lon'] = point[1]
                w['time'] = datetime.fromtimestamp(point_time).strftime('%H:%M')
                weather_data.append(w)
            
            progress_bar.progress((i + 1) / num_samples)
            time.sleep(0.1) # Be nice to the API

        # Display results
        df = pd.DataFrame(weather_data)

        # Collect all gas stations for map markers
        all_stations = []

        # Fuel & Rest Stops Summary
        if stops:
            st.subheader("⛽ Fuel & Rest Stops Plan")

            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Total Stops", len(stops))
            with col2:
                st.metric("Total Fuel Cost", f"€{total_fuel_cost:.2f}")
            with col3:
                st.metric("Total Fuel Needed", f"{total_fuel_needed:.1f} L")

            if optimize_cost:
                st.info("✅ Cost optimization enabled - showing cheapest stations first")

            # Display stops in expandable sections
            for i, stop in enumerate(stops, 1):
                with st.expander(f"Stop #{i} - {stop['type']} (at {stop['distance_km']} km, {stop['time_hours']} hrs)", expanded=True):
                    # Calculate position along route
                    stop_fraction = stop['distance_km'] / total_distance_km
                    stop_point_idx = int(stop_fraction * len(points))
                    stop_point_idx = min(stop_point_idx, len(points) - 1)
                    stop_lat, stop_lon = points[stop_point_idx]

                    col_a, col_b = st.columns(2)
                    with col_a:
                        st.write(f"**Distance:** {stop['distance_km']} km")
                        st.write(f"**Estimated Time:** {stop['time_hours']:.2f} hours from start")
                        if stop['fuel_to_add'] > 0:
                            st.write(f"**Fuel Remaining:** {stop['fuel_remaining_before']} L")
                            st.write(f"**Fuel to Add:** {stop['fuel_to_add']} L")

                            # Show suggestion if it's an early fuel stop
                            if stop.get('suggestion'):
                                st.info(f"💡 {stop['suggestion']}")

                    with col_b:
                        # Find nearby gas stations
                        if 'Fuel' in stop['type']:
                            with st.spinner("Finding nearby stations..."):
                                stations = routing.find_nearby_stations(
                                    stop_lat,
                                    stop_lon,
                                    optimize_cost=optimize_cost,
                                    max_detour_km=max_detour_km,
                                    fuel_type=fuel_type
                                )
                                if stations:
                                    st.write(f"**⛽ Cheapest {fuel_type} Stations Nearby:**")

                                    # Show data source indicator
                                    if stations[0].get('price_source') == 'OpenVan':
                                        country = stations[0].get('country', 'Unknown')
                                        st.caption(f"✅ Real {fuel_type.lower()} prices from OpenVan.camp API ({country})")
                                    else:
                                        st.caption(f"⚠️ Estimated {fuel_type.lower()} prices (real prices available for European countries)")

                                    for idx, station in enumerate(stations, 1):
                                        # Add to all_stations for map display
                                        station_info = station.copy()
                                        station_info['stop_number'] = i
                                        all_stations.append(station_info)

                                        # Display with price
                                        price_color = "🟢" if idx == 1 else "🟡" if idx <= 3 else "⚪"
                                        distance_info = f" ({station['distance_km']} km detour)" if station.get('distance_km', 0) > 0.5 else ""

                                        # Station name and price
                                        st.write(f"{price_color} **€{station['price_per_liter']}/L** - **{station['name']}**{distance_info}")

                                        # Address
                                        if station.get('address') and station['address'] != 'Address not available':
                                            st.caption(f"📍 {station['address']}")

                                        # Links
                                        col_link1, col_link2 = st.columns(2)
                                        with col_link1:
                                            st.markdown(f"[🗺️ OpenStreetMap]({station['osm_link']})")
                                        with col_link2:
                                            st.markdown(f"[📍 Google Maps]({station['google_maps_link']})")

                                        if idx < len(stations):
                                            st.divider()

                                    # Calculate cost at cheapest station
                                    cheapest_price = stations[0]['price_per_liter']
                                    cheapest_cost = stop['fuel_to_add'] * cheapest_price
                                    st.success(f"💰 Best price: €{cheapest_cost:.2f} ({stop['fuel_to_add']}L × €{cheapest_price}/L)")

        # Map with gas station markers and color-coded segments
        st.subheader("Route Map with Gas Stations")

        # Create color-coded route segments
        segment_colors = [
            [255, 0, 0, 200],      # Red
            [0, 255, 0, 200],      # Green
            [0, 0, 255, 200],      # Blue
            [255, 165, 0, 200],    # Orange
            [128, 0, 128, 200],    # Purple
            [255, 192, 203, 200],  # Pink
            [0, 255, 255, 200],    # Cyan
            [255, 255, 0, 200],    # Yellow
        ]

        # Calculate stop positions along route
        stop_indices = []
        if stops:
            for stop in stops:
                stop_fraction = stop['distance_km'] / total_distance_km
                stop_idx = int(stop_fraction * len(points))
                stop_idx = min(stop_idx, len(points) - 1)
                stop_indices.append(stop_idx)

        # Create segments between stops
        route_segments = []
        prev_idx = 0

        if stop_indices:
            for i, stop_idx in enumerate(stop_indices):
                segment_path = [[points[j][1], points[j][0]] for j in range(prev_idx, stop_idx + 1)]
                route_segments.append({
                    "path": segment_path,
                    "color": segment_colors[i % len(segment_colors)],
                    "segment": i + 1
                })
                prev_idx = stop_idx

            # Add final segment to destination
            if prev_idx < len(points) - 1:
                segment_path = [[points[j][1], points[j][0]] for j in range(prev_idx, len(points))]
                route_segments.append({
                    "path": segment_path,
                    "color": segment_colors[len(stop_indices) % len(segment_colors)],
                    "segment": len(stop_indices) + 1
                })
        else:
            # No stops, show entire route in one color
            route_segments.append({
                "path": [[p[1], p[0]] for p in points],
                "color": [0, 100, 255, 200],
                "segment": 1
            })

        # Create route layers (one per segment)
        route_layers = []
        for segment in route_segments:
            layer = pdk.Layer(
                "PathLayer",
                data=[segment],
                get_path="path",
                get_color="color",
                width_min_pixels=4,
                pickable=False
            )
            route_layers.append(layer)

        # Set view centered on route
        avg_lat = sum(p[0] for p in points) / len(points)
        avg_lon = sum(p[1] for p in points) / len(points)

        view_state = pdk.ViewState(
            latitude=avg_lat,
            longitude=avg_lon,
            zoom=6,
            pitch=0
        )

        # Create gas station markers layer if stations exist
        layers = route_layers.copy()

        if all_stations:
            stations_df = pd.DataFrame(all_stations)
            stations_layer = pdk.Layer(
                "ScatterplotLayer",
                data=stations_df,
                get_position=["lon", "lat"],
                get_color=[255, 50, 50, 220],
                get_radius=500,
                pickable=True,
                auto_highlight=True
            )
            layers.append(stations_layer)

        # Try to render map with PyDeck, fallback to simple map if it fails
        try:
            r = pdk.Deck(
                layers=layers,
                initial_view_state=view_state,
                tooltip={"text": "⛽ {name}\n€{price_per_liter}/L\nStop #{stop_number}"} if all_stations else None,
                map_style=None  # Use default OpenStreetMap style
            )
            st.pydeck_chart(r)
        except Exception as e:
            st.warning(f"Advanced map rendering unavailable, using simple map. ({str(e)})")
            # Fallback to simple map
            map_data = pd.DataFrame(points, columns=['lat', 'lon'])
            if all_stations:
                # Add stations to map
                stations_map_data = pd.DataFrame(all_stations)[['lat', 'lon']]
                combined_map = pd.concat([map_data, stations_map_data], ignore_index=True)
                st.map(combined_map)
            else:
                st.map(map_data)

        # Legend
        legend_text = "**Map Legend:**\n"
        if stops:
            legend_text += "- **Colored segments** = Route sections between stops\n"
            for i in range(min(len(stops) + 1, 8)):
                color_name = ["Red", "Green", "Blue", "Orange", "Purple", "Pink", "Cyan", "Yellow"][i]
                if i < len(stops):
                    legend_text += f"  - {color_name}: Start → Stop #{i+1}\n"
                else:
                    legend_text += f"  - {color_name}: Stop #{i} → Destination\n"
        else:
            legend_text += "- Blue line = Your route\n"

        if all_stations:
            legend_text += "- 🔴 **Red markers** = Gas stations (hover for details)"

        st.markdown(legend_text)

        # Weather Table
        st.subheader("Weather Along the Route")
        st.dataframe(df[['time', 'description', 'temperature', 'wind_speed', 'humidity']])

        # Detailed cards
        st.subheader("Detailed Forecast")
        cols = st.columns(5)
        for i, w in enumerate(weather_data):
            col_idx = i % 5
            with cols[col_idx]:
                st.metric(label=f"At {w['time']}", value=f"{w['temperature']}°C")
                st.write(f"**{w['description']}**")
                st.write(f"💨 {w['wind_speed']} km/h")

    except Exception as e:
        st.error(f"Error: {str(e)}")
