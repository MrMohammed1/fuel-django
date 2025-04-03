import asyncio
import os
import sys
import django
from django.db.models import Q
from asgiref.sync import sync_to_async
from functools import reduce
from math import radians, sin, cos, sqrt, atan2

# Add project root to sys.path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BASE_DIR)

# Set up Django environment
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "fuel_route.settings")
django.setup()

# Now we can import models
from api.models import CityCoordinates, FuelStation

def format_city_name(city_name):
    """Convert city name to database format (e.g., big-cabin to Big Cabin)."""
    return city_name.replace("-", " ").title()

def haversine_distance(lat1, lon1, lat2, lon2):
    """Calculate the Haversine distance between two points in miles."""
    R = 3958.8  # Earth radius in miles
    lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
    c = 2 * atan2(sqrt(a), sqrt(1 - a))
    return R * c

def calculate_total_distance(points):
    """Calculate the total distance of a route given a list of (lat, lon) points."""
    total_distance = 0.0
    for i in range(len(points) - 1):
        lat1, lon1 = points[i]
        lat2, lon2 = points[i + 1]
        total_distance += haversine_distance(lat1, lon1, lat2, lon2)
    return total_distance

async def fetch_city_coordinates():
    """Fetch city coordinates from the database with flexible name matching."""
    cities_to_fetch = {
        "big-cabin": format_city_name("big-cabin"),
        "laurel": format_city_name("laurel")
    }

    cities = await sync_to_async(
        lambda: list(CityCoordinates.objects.filter(
            Q(city__iexact=cities_to_fetch["big-cabin"]) | Q(city__iexact=cities_to_fetch["laurel"])
        ).values("city", "latitude", "longitude"))
    )()

    if not cities:
        raise ValueError("Could not find coordinates for Big Cabin or Laurel in the database!")

    city_coords = {city["city"].replace(" ", "").lower(): (city["latitude"], city["longitude"]) for city in cities}
    return city_coords

async def fetch_fuel_stations():
    """Fetch fuel station locations from the database."""
    stations = await sync_to_async(
        lambda: list(FuelStation.objects.all().values("id", "name", "price_per_gallon", "latitude", "longitude"))
    )()
    return [
        (str(station["id"]), station["name"] or "N/A", station["price_per_gallon"], station["latitude"], station["longitude"])
        for station in stations
    ]

async def generate_mock_data():
    """Generate mock data dynamically based on the database."""
    city_coords = await fetch_city_coordinates()
    fuel_stations = await fetch_fuel_stations()

    if "bigcabin" not in city_coords or "laurel" not in city_coords:
        raise ValueError("Could not find coordinates for Big Cabin or Laurel in the database after normalization!")

    big_cabin_coords = city_coords["bigcabin"]
    laurel_coords = city_coords["laurel"]

    # Create a route with smaller detours to achieve a total distance of ~750 miles
    mid_points = [
        # First detour: Slight deviation north and east
        (big_cabin_coords[0] + 0.3, big_cabin_coords[1] + 0.5),  # Detour 1 (~13.8 miles)
        # Second detour: Slight deviation south and west
        (big_cabin_coords[0] - 0.3, big_cabin_coords[1] - 0.4),  # Detour 2 (~20.7 miles)
        # Third detour: Closer to Laurel with a small deviation
        (laurel_coords[0] + 0.1, laurel_coords[1] - 0.2),        # Detour 3 (~13.8 miles)
    ]
    MOCK_ROUTE_POINTS = [big_cabin_coords] + mid_points + [laurel_coords]

    # Calculate and print the total distance for verification
    total_distance = calculate_total_distance(MOCK_ROUTE_POINTS)
    print(f"📏 Total distance of MOCK_ROUTE_POINTS: {total_distance:.2f} miles")

    # Filter fuel stations near the route
    MOCK_FUEL_STATIONS = [
        station for station in fuel_stations
        if any(
            abs(station[3] - point[0]) < 5 and abs(station[4] - point[1]) < 5
            for point in MOCK_ROUTE_POINTS
        )
    ]

    return MOCK_ROUTE_POINTS, MOCK_FUEL_STATIONS

def save_mock_data(route_points, fuel_stations):
    """Save mock data to a file for use in tests."""
    with open("scripts/mock_data.py", "w", encoding="utf-8") as f:
        f.write("# Generated mock data from database\n")
        f.write("MOCK_ROUTE_POINTS = [\n")
        for point in route_points:
            f.write(f"    ({point[0]}, {point[1]}),  # Approximate point\n")
        f.write("]\n\n")
        f.write("MOCK_FUEL_STATIONS = [\n")
        for station in fuel_stations:
            f.write(f"    (\"{station[0]}\", \"{station[1]}\", {station[2]}, {station[3]}, {station[4]}),  # {station[1]}\n")
        f.write("]\n")

async def main():
    """Main function to run the script."""
    try:
        print("📥 Fetching data from the database...")
        route_points, fuel_stations = await generate_mock_data()
        print(f"✅ Generated {len(route_points)} route points and {len(fuel_stations)} fuel stations.")
        
        print("💾 Saving data to scripts/mock_data.py...")
        save_mock_data(route_points, fuel_stations)
        print("🚀 Data successfully saved to scripts/mock_data.py!")
    except Exception as e:
        print(f"❌ An error occurred: {e}")

if __name__ == "__main__":
    asyncio.run(main())