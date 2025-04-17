import pytest
from unittest.mock import AsyncMock, patch
from django.core.cache import cache
from api.utils import (
    haversine_distance,
    fetch_coordinate,
    get_fuel_stations,
    get_route,
    format_city_name,
    calculate_gallons_needed,
    calculate_total_distance,
    get_nearby_stations,
    get_all_stations,
)
from api.models import CityCoordinates, FuelStation, RouteData
from asgiref.sync import sync_to_async
from scripts.mock_data import MOCK_ROUTE_POINTS, MOCK_FUEL_STATIONS  # Import mock data generated from database

# Constants for test data (based on database)
TEST_CITIES = {
    "big-cabin": MOCK_ROUTE_POINTS[0],  # First point from mock data (Big Cabin)
    "laurel": MOCK_ROUTE_POINTS[-1],    # Last point from mock data (Laurel)
}

# Sample fuel station data for testing (using a subset of MOCK_FUEL_STATIONS)
SAMPLE_STATION = MOCK_FUEL_STATIONS[0] if MOCK_FUEL_STATIONS else (
    "1", "Sample Station", 3.5, TEST_CITIES["big-cabin"][0], TEST_CITIES["big-cabin"][1]
)

# Fixtures for automatic cleanup
@pytest.fixture
async def clean_city_coordinates():
    """Clean up all CityCoordinates objects before each test."""
    await sync_to_async(CityCoordinates.objects.all().delete)()
    yield

@pytest.fixture
async def clean_fuel_stations():
    """Clean up all FuelStation objects before each test."""
    await sync_to_async(FuelStation.objects.all().delete)()
    yield

@pytest.fixture
async def clean_route_data():
    """Clean up all RouteData objects before each test."""
    await sync_to_async(RouteData.objects.all().delete)()
    yield

@pytest.fixture
async def setup_test_data(clean_city_coordinates, clean_fuel_stations):
    """Set up test data in the database."""
    # Add test city coordinates for Big Cabin and Laurel
    await sync_to_async(CityCoordinates.objects.create)(
        city="Big Cabin", latitude=TEST_CITIES["big-cabin"][0], longitude=TEST_CITIES["big-cabin"][1]
    )
    await sync_to_async(CityCoordinates.objects.create)(
        city="Laurel", latitude=TEST_CITIES["laurel"][0], longitude=TEST_CITIES["laurel"][1]
    )

    # Add test fuel stations using SAMPLE_STATION
    await sync_to_async(FuelStation.objects.create)(
        opis_truckstop_id=SAMPLE_STATION[0],
        name=SAMPLE_STATION[1],
        city="Big Cabin",
        state="OK",  # Assuming Big Cabin is in Oklahoma
        address="123 Main St",
        price_per_gallon=SAMPLE_STATION[2],
        latitude=TEST_CITIES["big-cabin"][0],
        longitude=TEST_CITIES["big-cabin"][1]
    )
    # Add a second fuel station near Laurel
    await sync_to_async(FuelStation.objects.create)(
        opis_truckstop_id="2",
        name="Station B",
        city="Laurel",
        state="MS",  # Assuming Laurel is in Mississippi
        address="456 Oak St",
        price_per_gallon=4.0,
        latitude=TEST_CITIES["laurel"][0],
        longitude=TEST_CITIES["laurel"][1]
    )
    yield

# Basic Function Tests
def test_haversine_distance():
    """Test the Haversine distance calculation between two points."""
    dist = haversine_distance(
        TEST_CITIES["big-cabin"][0], TEST_CITIES["big-cabin"][1],
        TEST_CITIES["laurel"][0], TEST_CITIES["laurel"][1]
    )
    assert 600 < dist < 620  # Direct distance between Big Cabin and Laurel (not the route distance)

def test_format_city_name():
    """Test the city name formatting function."""
    assert format_city_name("big-cabin") == "Big Cabin"
    assert format_city_name("laurel") == "Laurel"

def test_calculate_gallons_needed():
    """Test the gallons needed calculation."""
    assert calculate_gallons_needed(1000) == 100  # Default miles_per_gallon=10
    assert calculate_gallons_needed(500, miles_per_gallon=5) == 100

def test_calculate_total_distance():
    """Test the total distance calculation for a route."""
    total_dist = calculate_total_distance(MOCK_ROUTE_POINTS)
    assert 730 < total_dist < 770  # Approximate distance in miles for the route (matches API response)

# Async Function Tests
@pytest.mark.django_db
@pytest.mark.asyncio
async def test_fetch_coordinate_from_db(setup_test_data):
    """Test fetching coordinates from the database."""
    city_name = "Big Cabin"
    latitude, longitude = TEST_CITIES["big-cabin"]
    coords = await fetch_coordinate(city_name)
    assert coords == (latitude, longitude)

@pytest.mark.django_db
@pytest.mark.asyncio
async def test_fetch_coordinate_cache(setup_test_data):
    """Test fetching coordinates from the cache."""
    city_name = "Laurel"
    cache_key = city_name.replace(" ", "_")
    latitude, longitude = TEST_CITIES["laurel"]
    cache.set(cache_key, (latitude, longitude))
    coords = await fetch_coordinate(city_name)
    assert coords == (latitude, longitude)

@pytest.mark.django_db
@pytest.mark.asyncio
async def test_fetch_coordinate_not_found(clean_city_coordinates):
    """Test fetching coordinates when city is not found."""
    coords = await fetch_coordinate("Unknown City")
    assert coords is None

@pytest.mark.django_db
@pytest.mark.asyncio
async def test_get_fuel_stations(setup_test_data):
    """Test retrieving fuel stations along a route."""
    stations = await get_fuel_stations(MOCK_ROUTE_POINTS)
    assert len(stations) == 2
    assert (SAMPLE_STATION[0], "123 Main St", SAMPLE_STATION[2], TEST_CITIES["big-cabin"][0], TEST_CITIES["big-cabin"][1]) in stations
    assert ("2", "456 Oak St", 4.0, TEST_CITIES["laurel"][0], TEST_CITIES["laurel"][1]) in stations

@pytest.mark.django_db
@pytest.mark.asyncio
async def test_get_route_success(aiohttp_session, setup_test_data, clean_route_data):
    """Test fetching a route successfully with OpenRouteService."""
    start = TEST_CITIES["big-cabin"]
    finish = TEST_CITIES["laurel"]
    mock_response = {
        "routes": [{
            "geometry": {"coordinates": MOCK_ROUTE_POINTS}
        }]
    }
    mock_response_obj = AsyncMock()
    mock_response_obj.status = 200
    mock_response_obj.json = AsyncMock(return_value=mock_response)
    mock_response_obj.__aenter__ = AsyncMock(return_value=mock_response_obj)
    mock_response_obj.__aexit__ = AsyncMock(return_value=None)

    with patch("aiohttp.ClientSession.get", return_value=mock_response_obj):
        route_data = await get_route(start, finish)
        assert "routes" in route_data
        assert len(route_data["routes"][0]["geometry"]["coordinates"]) == len(MOCK_ROUTE_POINTS)

@pytest.mark.django_db
@pytest.mark.asyncio
async def test_get_route_failure(aiohttp_session, clean_city_coordinates, clean_route_data):
    """Test fetching a route when all APIs fail."""
    start = TEST_CITIES["big-cabin"]
    finish = TEST_CITIES["laurel"]
    mock_response_obj = AsyncMock()
    mock_response_obj.status = 404
    mock_response_obj.json = AsyncMock(return_value={})
    mock_response_obj.__aenter__ = AsyncMock(return_value=mock_response_obj)
    mock_response_obj.__aexit__ = AsyncMock(return_value=None)

    with patch("aiohttp.ClientSession.get", return_value=mock_response_obj):
        route_data = await get_route(start, finish)
        assert "error" in route_data
        assert route_data["error"] == "Failed to retrieve route from all APIs"

@pytest.mark.django_db
@pytest.mark.asyncio
async def test_get_nearby_stations(setup_test_data):
    """Test retrieving nearby fuel stations."""
    # Define a bounding box around Big Cabin
    stations = await get_nearby_stations(
        TEST_CITIES["big-cabin"][0] - 0.5,
        TEST_CITIES["big-cabin"][0] + 0.5,
        TEST_CITIES["big-cabin"][1] - 0.5,
        TEST_CITIES["big-cabin"][1] + 0.5
    )
    assert len(stations) == 1  # Should find Station A in Big Cabin
    assert (SAMPLE_STATION[0], "123 Main St", SAMPLE_STATION[2], TEST_CITIES["big-cabin"][0], TEST_CITIES["big-cabin"][1]) in stations

@pytest.mark.django_db
@pytest.mark.asyncio
async def test_get_all_stations(setup_test_data):
    """Test retrieving all fuel stations."""
    stations = await get_all_stations()
    assert len(stations) == 2
    assert (SAMPLE_STATION[0], "123 Main St", SAMPLE_STATION[2], TEST_CITIES["big-cabin"][0], TEST_CITIES["big-cabin"][1]) in stations
    assert ("2", "456 Oak St", 4.0, TEST_CITIES["laurel"][0], TEST_CITIES["laurel"][1]) in stations