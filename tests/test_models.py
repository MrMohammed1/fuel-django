import pytest
from unittest.mock import AsyncMock, patch
from django.core.cache import cache
from api.models import CityCoordinates, FuelStation, RouteData
from asgiref.sync import sync_to_async
from scripts.mock_data import MOCK_ROUTE_POINTS, MOCK_FUEL_STATIONS  

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

# Basic Model Tests
@pytest.mark.django_db
def test_route_data_creation():
    """Test the creation of a RouteData object with specified route_key and data."""
    route = RouteData.objects.create(route_key="big-cabin_laurel", data={"path": "big-cabin to laurel"})
    assert route.route_key == "big-cabin_laurel"
    assert route.data == {"path": "big-cabin to laurel"}

@pytest.mark.django_db
def test_city_coordinates_creation(clean_city_coordinates):
    """Test the creation of a CityCoordinates object with specified city and coordinates."""
    city_name = "Big Cabin"
    latitude, longitude = TEST_CITIES["big-cabin"]
    city = CityCoordinates.objects.create(city=city_name, latitude=latitude, longitude=longitude)
    assert city.city == city_name
    assert city.latitude == latitude
    assert city.longitude == longitude

@pytest.mark.django_db
def test_fuel_station_creation(clean_fuel_stations):
    """Test the creation of a FuelStation object with specified fuel station details."""
    station = FuelStation.objects.create(
        opis_truckstop_id=SAMPLE_STATION[0],
        name=SAMPLE_STATION[1],
        city="Big Cabin",
        state="OK",  
        address="123 Main St",
        price_per_gallon=SAMPLE_STATION[2],
        latitude=TEST_CITIES["big-cabin"][0],
        longitude=TEST_CITIES["big-cabin"][1]
    )
    assert station.opis_truckstop_id == SAMPLE_STATION[0]
    assert station.name == SAMPLE_STATION[1]
    assert station.city == "Big Cabin"
    assert station.state == "OK"
    assert station.price_per_gallon == SAMPLE_STATION[2]

# Coordinates and API Tests
@pytest.mark.django_db
@pytest.mark.asyncio
async def test_fetch_coordinates_from_db(aiohttp_session, clean_city_coordinates):
    """Test fetching coordinates from the database."""
    city_name = "Big Cabin"
    latitude, longitude = TEST_CITIES["big-cabin"]
    await sync_to_async(CityCoordinates.objects.create)(
        city=city_name, latitude=latitude, longitude=longitude
    )
    coords = await CityCoordinates.fetch_coordinates(aiohttp_session, city_name)
    assert coords == (latitude, longitude)

@pytest.mark.django_db
@pytest.mark.asyncio
async def test_fetch_coordinates_cache(aiohttp_session, clean_city_coordinates):
    """Test fetching coordinates from the cache."""
    city_name = "Laurel"
    cache_key = city_name.replace(" ", "_")
    latitude, longitude = TEST_CITIES["laurel"]
    cache.set(cache_key, (latitude, longitude))
    coords = await CityCoordinates.fetch_coordinates(aiohttp_session, city_name)
    assert abs(coords[0] - latitude) < 0.01 and abs(coords[1] - longitude) < 0.01

@pytest.mark.django_db
@pytest.mark.asyncio
async def test_fetch_coordinates_api(aiohttp_session, clean_city_coordinates):
    """Test fetching coordinates from an external API."""
    city_name = "Laurel"
    latitude, longitude = TEST_CITIES["laurel"]
    mock_response = {
        "results": [{"geometry": {"lat": latitude, "lng": longitude}}]
    }
    
    # Create a mock response object with async context manager support
    mock_response_obj = AsyncMock()
    mock_response_obj.status = 200
    mock_response_obj.json = AsyncMock(return_value=mock_response)
    mock_response_obj.__aenter__ = AsyncMock(return_value=mock_response_obj)
    mock_response_obj.__aexit__ = AsyncMock(return_value=None)

    # Define a regular function to return the mock response object
    def mock_get(*args, **kwargs):
        return mock_response_obj

    with patch("aiohttp.ClientSession.get", mock_get):
        coords = await CityCoordinates.fetch_coordinates(aiohttp_session, city_name)
        assert coords == (latitude, longitude)

        city = await sync_to_async(CityCoordinates.objects.get)(city=city_name)
        assert city.latitude == latitude
        assert city.longitude == longitude

@pytest.mark.django_db
@pytest.mark.asyncio
async def test_fetch_coordinates_api_failure(aiohttp_session, clean_city_coordinates):
    """Test fetch_coordinates when the API returns an empty response."""
    city_name = "Big Cabin"
    mock_response = {"results": []}  # Empty response to simulate failure
    
    # Create a mock response object with async context manager support
    mock_response_obj = AsyncMock()
    mock_response_obj.status = 200
    mock_response_obj.json = AsyncMock(return_value=mock_response)
    mock_response_obj.__aenter__ = AsyncMock(return_value=mock_response_obj)
    mock_response_obj.__aexit__ = AsyncMock(return_value=None)

    def mock_get(*args, **kwargs):
        return mock_response_obj

    with patch("aiohttp.ClientSession.get", mock_get):
        coords = await CityCoordinates.fetch_coordinates(aiohttp_session, city_name)
        assert coords == (None, None)  # Should return None on failure

@pytest.mark.django_db
@pytest.mark.asyncio
async def test_load_fuel_data(tmpdir, aiohttp_session, clean_city_coordinates, clean_fuel_stations):
    """Test loading fuel station data from a CSV file."""
    async def create_test_csv_file():
        """Helper function to create a test CSV file with sample data."""
        csv_file = tmpdir.join("fuel_data.csv")
        csv_file.write(
            "OPIS Truckstop ID;Truckstop Name;City;State;Retail Price;Address\n"
            f"{SAMPLE_STATION[0]};{SAMPLE_STATION[1]};Big Cabin;OK;{SAMPLE_STATION[2]};123 Main St\n"
            f"2;Station B;Laurel;MS;4.1;456 Oak St\n"
        )
        return str(csv_file)

    csv_path = await create_test_csv_file()
    with patch("api.models.CityCoordinates.fetch_coordinates", new_callable=AsyncMock) as mock_fetch:
        mock_fetch.side_effect = [
            TEST_CITIES["big-cabin"],  # Coordinates for Big Cabin
            TEST_CITIES["laurel"]      # Coordinates for Laurel
        ]

        await FuelStation.load_fuel_data(csv_path)

    stations = await sync_to_async(list)(FuelStation.objects.all())
    assert len(stations) == 2
    assert stations[0].opis_truckstop_id == SAMPLE_STATION[0]
    assert stations[0].city == "Big Cabin"
    assert stations[0].price_per_gallon == SAMPLE_STATION[2]
    assert stations[1].city == "Laurel"
    assert stations[1].price_per_gallon == 4.1