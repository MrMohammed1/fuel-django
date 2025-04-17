import aiohttp
from math import radians, sin, cos, sqrt, atan2
from django.core.cache import cache
from .models import FuelStation, RouteData, CityCoordinates
from asgiref.sync import sync_to_async
from channels.db import database_sync_to_async
from functools import lru_cache
from decouple import config


# Load API keys from environment variables
API_KEY = config("GRAPH_HOPPER_API_KEY")
OPENROUTE_API_KEY = config("OPENROUTE_API_KEY")
HERE_API_KEY = config("HERE_API_KEY")

# Helper functions
@lru_cache(maxsize=1024)
def haversine_distance(lat1, lon1, lat2, lon2):
    if not all(isinstance(coord, (int, float)) for coord in [lat1, lon1, lat2, lon2]):
        raise ValueError("Invalid coordinates")
    R = 3958.8
    lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
    dlon, dlat = lon2 - lon1, lat2 - lat1
    a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
    return 2 * R * atan2(sqrt(a), sqrt(1 - a))

def format_city_name(city_name):
    return city_name.replace("-", " ").title()

def calculate_gallons_needed(total_distance, miles_per_gallon=10):
    return total_distance / miles_per_gallon

def calculate_total_distance(route_points):
    return sum(haversine_distance(*route_points[i], *route_points[i + 1]) 
               for i in range(len(route_points) - 1))

# Database operations
@database_sync_to_async
def get_city_coordinates(city):
    return CityCoordinates.objects.filter(city=city).values("latitude", "longitude").first()

@database_sync_to_async
def get_nearby_stations(min_lat, max_lat, min_lon, max_lon):
    return list(FuelStation.objects.filter(
        latitude__range=(min_lat - 0.1, max_lat + 0.1),
        longitude__range=(min_lon - 0.1, max_lon + 0.1)
    ).only("opis_truckstop_id", "address", "price_per_gallon", "latitude", "longitude").values_list(
        "opis_truckstop_id", "address", "price_per_gallon", "latitude", "longitude"
    ))

@database_sync_to_async
def get_all_stations():
    return list(FuelStation.objects.all().only("opis_truckstop_id", "address", "price_per_gallon", "latitude", "longitude").values_list(
        "opis_truckstop_id", "address", "price_per_gallon", "latitude", "longitude"
    ))

@database_sync_to_async
def get_cached_route(route_key):
    return RouteData.objects.filter(route_key=route_key).values_list("data", flat=True).first()

# Async utility functions
async def fetch_coordinate(city):
    cache_key = city.replace(" ", "_")
    cached_coords = cache.get(cache_key)
    if cached_coords:
        return cached_coords
    coordinates = await get_city_coordinates(city)
    if not coordinates:
        return None
    coords = (coordinates["latitude"], coordinates["longitude"])
    cache.set(cache_key, coords, timeout=None)
    return coords

async def fetch_route_from_api(session, url, success_key):
    async with session.get(url) as response:
        route_data = await response.json()
        return route_data if response.status == 200 and success_key in route_data else None

async def get_fuel_stations(route_points):
    if not route_points:
        return await get_all_stations()
    min_lat, max_lat = min(c[0] for c in route_points), max(c[0] for c in route_points)
    min_lon, max_lon = min(c[1] for c in route_points), max(c[1] for c in route_points)
    stations = await get_nearby_stations(min_lat, max_lat, min_lon, max_lon)
    return stations if stations else await get_all_stations()

async def get_route(start, finish):
    if not all(isinstance(coord, (int, float)) for coord in start + finish):
        return {"error": "Invalid coordinates provided"}
    
    route_key = f"route_{start[0]}_{start[1]}_{finish[0]}_{finish[1]}"
    cached_route = cache.get(route_key)
    if cached_route:
        return cached_route

    route_data = await get_cached_route(route_key)
    if route_data:
        cache.set(route_key, route_data, timeout=86400)
        return route_data

    async with aiohttp.ClientSession() as session:
        # GraphHopper
        url = f"https://graphhopper.com/api/1/route?point={start[0]},{start[1]}&point={finish[0]},{finish[1]}&profile=car&locale=en&calc_points=true&key={API_KEY}"
        route_data = await fetch_route_from_api(session, url, "paths")
        if route_data:
            cache.set(route_key, route_data, timeout=86400)
            await sync_to_async(RouteData.objects.create)(route_key=route_key, data=route_data)
            return route_data

        # OpenRouteService
        url = f"https://api.openrouteservice.org/v2/directions/driving-car?api_key={OPENROUTE_API_KEY}&start={start[1]},{start[0]}&end={finish[1]},{finish[0]}"
        route_data = await fetch_route_from_api(session, url, "routes")
        if route_data:
            cache.set(route_key, route_data, timeout=86400)
            await sync_to_async(RouteData.objects.create)(route_key=route_key, data=route_data)
            return route_data

        # OSRM
        url = f"http://router.project-osrm.org/route/v1/driving/{start[1]},{start[0]};{finish[1]},{finish[0]}?overview=full&geometries=geojson"
        route_data = await fetch_route_from_api(session, url, "routes")
        if route_data:
            cache.set(route_key, route_data, timeout=86400)
            await sync_to_async(RouteData.objects.create)(route_key=route_key, data=route_data)
            return route_data

        # HERE Maps
        url = f"https://router.hereapi.com/v8/routes?transportMode=car&origin={start[0]},{start[1]}&destination={finish[0]},{finish[1]}&return=polyline&apikey={HERE_API_KEY}"
        route_data = await fetch_route_from_api(session, url, "routes")
        if route_data:
            cache.set(route_key, route_data, timeout=86400)
            await sync_to_async(RouteData.objects.create)(route_key=route_key, data=route_data)
            return route_data

    return {"error": "Failed to retrieve route from all APIs"}