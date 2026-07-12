import routing
import weather
from datetime import datetime

def test_routing():
    print("Testing geocoding...")
    start_lat, start_lon, start_name = routing.geocode("New York, NY")
    end_lat, end_lon, end_name = routing.geocode("Philadelphia, PA")
    start = (start_lat, start_lon)
    end = (end_lat, end_lon)
    print(f"Start: {start} ({start_name}), End: {end} ({end_name})")
    
    print("Testing suggestions...")
    suggestions = routing.get_suggestions("New York")
    print(f"Suggestions: {suggestions}")
    assert len(suggestions) > 0

    print("Testing routing...")
    points, duration = routing.get_route(start, end)
    print(f"Number of points: {len(points)}, Duration: {duration}s")
    assert len(points) > 0
    assert duration > 0

def test_weather():
    print("Testing weather...")
    # New York coordinates
    lat, lon = 40.7128, -74.0060
    now = datetime.now().timestamp()
    w = weather.get_weather(lat, lon, now)
    print(f"Weather: {w}")
    assert "temperature" in w
    assert "description" in w

if __name__ == "__main__":
    try:
        test_routing()
        test_weather()
        print("All tests passed!")
    except Exception as e:
        print(f"Test failed: {e}")
