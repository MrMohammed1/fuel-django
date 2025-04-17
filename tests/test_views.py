import pytest
from unittest.mock import AsyncMock, patch, Mock
from asgiref.sync import sync_to_async
from rest_framework.test import APIRequestFactory
from rest_framework import status
from api.views import TripPlanner
from scipy.spatial import KDTree
from scripts.mock_data import MOCK_ROUTE_POINTS, MOCK_FUEL_STATIONS  # Import mock data generated from database
from api.utils import calculate_total_distance  # Import to calculate actual distance

# Constants for test data (based on database)
TEST_CITIES = {
    "big-cabin": MOCK_ROUTE_POINTS[0],  # First point from mock data (Big Cabin)
    "laurel": MOCK_ROUTE_POINTS[-1],    # Last point from mock data (Laurel)
}

# Fixtures
@pytest.fixture
def api_request():
    """Create a mock API request for testing."""
    factory = APIRequestFactory()
    return factory.get("/api/trip/big-cabin/laurel")

@pytest.fixture
def trip_planner():
    """Create an instance of TripPlanner with predefined parameters."""
    return TripPlanner(fuel_capacity=500, miles_per_gallon=10, safety_margin=50, max_distance=1000)

# Tests for TripPlanner methods
def test_can_complete_trip_success(trip_planner):
    """Test if a trip can be completed with available fuel stations."""
    with patch("api.views.calculate_total_distance", return_value=750.0) as mock_distance:
        assert trip_planner.can_complete_trip(MOCK_ROUTE_POINTS, MOCK_FUEL_STATIONS, 1000) is True

def test_can_complete_trip_failure(trip_planner):
    """Test if a trip fails when no fuel stations are available."""
    with patch("api.views.calculate_total_distance", return_value=750.0) as mock_distance:
        assert trip_planner.can_complete_trip(MOCK_ROUTE_POINTS, [], 1000) is False

def test_select_fuel_stations_success(trip_planner):
    """Test selecting fuel stations along a route."""
    with patch("api.views.calculate_total_distance", return_value=750.0) as mock_distance, \
         patch("api.views.haversine_distance", side_effect=lambda lat1, lon1, lat2, lon2: 187.5):  # Simulate 750 miles / 4 segments
        stations, cost = trip_planner.select_fuel_stations(MOCK_ROUTE_POINTS, MOCK_FUEL_STATIONS, 1000)
        assert len(stations) > 0  # Ensure some stations are selected
        assert cost > 0  # Ensure cost is positive
        assert any(station[0] in [s[0] for s in MOCK_FUEL_STATIONS] for station in stations)  # Check if station IDs are valid

def test_select_fuel_stations_no_stations(trip_planner):
    """Test selecting fuel stations when none are available."""
    with patch("api.views.calculate_total_distance", return_value=750.0) as mock_distance:
        stations, cost = trip_planner.select_fuel_stations(MOCK_ROUTE_POINTS, [], 1000)
        assert stations == []  # No stations should be selected
        assert cost == 0.0  # Cost should be zero

def test_split_route_into_stages(trip_planner):
    """Test splitting a route into stages for refueling."""
    with patch("api.views.calculate_total_distance", return_value=750.0) as mock_distance, \
         patch("api.views.haversine_distance", side_effect=lambda lat1, lon1, lat2, lon2: 187.5):  # Simulate 750 miles / 4 segments
        stages, message = trip_planner.split_route_into_stages(MOCK_ROUTE_POINTS, MOCK_FUEL_STATIONS)
        assert len(stages) > 0  # Ensure stages are created
        assert message == "Trip requires staged refueling"  # Check the message

def test_find_cheapest_station(trip_planner):
    """Test finding the cheapest nearby fuel station."""
    kdtree = KDTree([(s[3], s[4]) for s in MOCK_FUEL_STATIONS])
    station = trip_planner.find_cheapest_station(kdtree, MOCK_ROUTE_POINTS[0], MOCK_FUEL_STATIONS, set())
    assert station in MOCK_FUEL_STATIONS  # Ensure a valid station is returned

def test_find_cheapest_station_none(trip_planner):
    """Test finding no station when none are available."""
    station = trip_planner.find_cheapest_station(None, MOCK_ROUTE_POINTS[0], [], set())
    assert station is None  # Should return None if no stations are available

@pytest.mark.asyncio
async def test_process_request_success(api_request, trip_planner):
    """Test processing a successful trip request."""
    # Calculate the actual total distance from MOCK_ROUTE_POINTS
    actual_distance = calculate_total_distance(MOCK_ROUTE_POINTS)

    with patch("api.views.fetch_coordinate", new_callable=AsyncMock) as mock_fetch, \
         patch("api.views.get_route", new_callable=AsyncMock) as mock_route, \
         patch("api.views.get_fuel_stations", new_callable=AsyncMock) as mock_stations, \
         patch("api.views.calculate_total_distance", return_value=actual_distance) as mock_distance:

        # Mock the fetch_coordinate function to return coordinates from TEST_CITIES
        mock_fetch.side_effect = lambda x: TEST_CITIES.get(x.replace("-", ""), (None, None))
        # Mock the get_route function to return the mocked route points
        mock_route.return_value = {
            "routes": [{"geometry": {"coordinates": MOCK_ROUTE_POINTS}}],
            "bbox": [-95.224193, 36.537792, -84.103304, 38.632542]
        }
        # Mock the get_fuel_stations function to return the mocked fuel stations
        mock_stations.return_value = MOCK_FUEL_STATIONS

        response = await trip_planner.process_request(api_request, "big-cabin", "laurel")
        assert response.status_code == status.HTTP_200_OK
        assert "route_map" in response.data
        assert "total_distance" in response.data["route_map"]
        assert 740 < response.data["route_map"]["total_distance"] < 760  # Match the actual distance
        assert "optimal_stations" in response.data
        assert "total_fuel_cost" in response.data

@pytest.mark.asyncio
async def test_process_request_invalid_city(api_request, trip_planner):
    """Test processing a request with an invalid city format."""
    response = await trip_planner.process_request(api_request, "Big Cabin", "laurel")
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "error" in response.data
    assert "Invalid city name format" in response.data["error"]

@pytest.mark.asyncio
async def test_process_request_same_city(api_request, trip_planner):
    """Test processing a request with the same start and finish city."""
    response = await trip_planner.process_request(api_request, "big-cabin", "big-cabin")
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "error" in response.data
    assert "cannot be the same" in response.data["error"]