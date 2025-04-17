from django.db import models
import pandas as pd
import aiohttp
from django.core.cache import cache
import logging
from asgiref.sync import sync_to_async, async_to_sync
from datetime import datetime
from decouple import config

# Logger settings
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
handler = logging.FileHandler('fuel_data_loading.log')
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)

file_path_csv = r"D:\\fuel-prices-for-be-assessment.csv"
API_KEY = config('OPENCAGE_API_KEY')

class RouteData(models.Model):
    route_key = models.CharField(max_length=255, unique=True, db_index=True)
    data = models.JSONField()
    
    def __str__(self):
        return self.route_key

class CityCoordinates(models.Model):
    city = models.CharField(max_length=255, unique=True)
    latitude = models.FloatField(default=0.0)
    longitude = models.FloatField(default=0.0)

    def __str__(self):
        return self.city

    class Meta:
        indexes = [
            models.Index(fields=['city']),
            models.Index(fields=['latitude', 'longitude']),
        ]

    @staticmethod
    async def fetch_coordinates(session, city):
        try:
            cache_key = city.replace(" ", "_")
            cached_coords = cache.get(cache_key)
            if cached_coords:
                return cached_coords

            city_obj = await sync_to_async(CityCoordinates.objects.get_or_create, thread_sensitive=False)(
                city=city, defaults={"latitude": 0.0, "longitude": 0.0}
            )

            if city_obj[1] is False:  # City already exists
                coords = (city_obj[0].latitude, city_obj[0].longitude)
                cache.set(cache_key, coords, 604800)  # Cache for 7 days
                return coords

            url = f"https://api.opencagedata.com/geocode/v1/json?q={city}&key={API_KEY}"

            async with session.get(url) as response:
                if response.status == 402 or response.status == 429:  # Daily limit exceeded
                    reset_time = response.headers.get("X-RateLimit-Reset")
                    if reset_time:
                        reset_timestamp = int(reset_time)
                        reset_datetime = datetime.utcfromtimestamp(reset_timestamp)
                        print(f"[❌] Daily limit exceeded! Will reset at: {reset_datetime} UTC")
                    else:
                        print("[❌] Daily limit exceeded! Please try again later.")
                    return None, None

                if response.status == 200:
                    data = await response.json()
                    if data and data.get("results"):
                        lat = data["results"][0]["geometry"]["lat"]
                        lon = data["results"][0]["geometry"]["lng"]
                        coords = (lat, lon)

                        await sync_to_async(lambda: CityCoordinates.objects.filter(city=city).update(
                            latitude=lat, longitude=lon
                        ))()
                        updated_city = await sync_to_async(CityCoordinates.objects.get, thread_sensitive=False)(city=city)

                        cache.set(cache_key, coords, timeout=None)
                        return coords

            return None, None
        except Exception as e:
            logger.error(f"Failed to fetch coordinates for city {city}: {str(e)}", exc_info=True)
            return None, None

class FuelStation(models.Model):
    opis_truckstop_id = models.CharField(max_length=50, unique=True, null=True, blank=True)  # OPIS Truckstop ID
    name = models.CharField(max_length=255)
    city = models.CharField(max_length=255)
    state = models.CharField(max_length=255)
    address = models.CharField(max_length=255, blank=True)
    price_per_gallon = models.FloatField()
    latitude = models.FloatField(default=0.0, db_index=True)
    longitude = models.FloatField(default=0.0, db_index=True)

    def __str__(self):
        return self.name if self.name else self.opis_truckstop_id

    class Meta:
        indexes = [
            models.Index(fields=['opis_truckstop_id']),
            models.Index(fields=['latitude', 'longitude'])
        ]

    @classmethod
    async def process_chunk(cls, chunk, existing_stations_dict, session):
        stations_to_update = []
        stations_to_create = []
        city_coords_cache = {}
        existing_station_keys = set(existing_stations_dict.keys())

        unique_cities = set(chunk['City'])
        existing_cities_data = await sync_to_async(
            lambda: list(CityCoordinates.objects.filter(city__in=unique_cities).values_list('city', 'latitude', 'longitude'))
        )()
        existing_cities_dict = {city: (lat, lon) for city, lat, lon in existing_cities_data}
        new_cities = []

        for _, row in chunk.iterrows():
            cleaned_city = str(row['City'])
            station_key = str(row['OPIS Truckstop ID'])
            price = float(row['Retail Price'])
            address = row['Address']

            if station_key in existing_station_keys:
                station_id, old_price, old_address = existing_stations_dict[station_key]
                if price is not None and address is not None:
                    if old_price != price or old_address != address:
                        stations_to_update.append(FuelStation(id=station_id, price_per_gallon=price, address=address))
            else:
                if cleaned_city in city_coords_cache:
                    latitude, longitude = city_coords_cache[cleaned_city]
                elif cleaned_city in existing_cities_dict:
                    latitude, longitude = existing_cities_dict[cleaned_city]
                else:
                    latitude, longitude = await CityCoordinates.fetch_coordinates(session, cleaned_city)
                    if latitude is None or longitude is None:
                        continue
                    city_coords_cache[cleaned_city] = (latitude, longitude)
                    new_cities.append(CityCoordinates(city=cleaned_city, latitude=latitude, longitude=longitude))

                new_station = cls(
                    opis_truckstop_id=station_key,
                    name=row['Truckstop Name'].strip(),
                    state=str(row['State']).strip() if pd.notna(row['State']) else '',
                    city=cleaned_city,
                    address=address,
                    price_per_gallon=price,
                    latitude=latitude,
                    longitude=longitude
                )
                stations_to_create.append(new_station)

        if new_cities:
            await sync_to_async(lambda: CityCoordinates.objects.bulk_create(new_cities, batch_size=1000))()
        if stations_to_update:
            await sync_to_async(lambda: FuelStation.objects.bulk_update(stations_to_update, ['price_per_gallon', 'address']))()
        if stations_to_create:
            await sync_to_async(lambda: FuelStation.objects.bulk_create(stations_to_create, batch_size=1000))()

    @classmethod
    async def load_fuel_data(cls, file_path):
        try:
            df = pd.read_csv(
                file_path,
                encoding='ISO-8859-1',
                dtype={'Truckstop Name': str, 'City': str, 'State': str, 'Retail Price': str},
                delimiter=';',
                quotechar='"',
                engine='c'
            )

            df.columns = df.columns.str.strip().str.replace('"', '')
            df = df.apply(lambda x: x.str.strip() if x.dtype == "object" else x)
            df.dropna(subset=['OPIS Truckstop ID'], inplace=True)
            df = df[df['City'].str.contains(r"^[a-zA-Z\s\-.']+$", na=False)]
            df.drop_duplicates(subset=['OPIS Truckstop ID'], keep='last', inplace=True)
            df['Retail Price'] = df['Retail Price'].astype(str).str.replace(r'[;,]', '', regex=True)
            df['Retail Price'] = pd.to_numeric(df['Retail Price'], errors='coerce')
            df['Retail Price'].fillna(df['Retail Price'].mean(), inplace=True)
            df['Address'] = df['Address'].fillna("").astype(str).str.strip()

            existing_stations_list = await sync_to_async(
                lambda: list(FuelStation.objects.values_list('opis_truckstop_id', 'id', 'price_per_gallon', 'address')),
                thread_sensitive=False
            )()
            existing_stations_dict = {station_id: (id, price, address) for station_id, id, price, address in existing_stations_list}

            async with aiohttp.ClientSession() as session:
                await cls.process_chunk(df, existing_stations_dict, session)
        except Exception as e:
            logger.error(f"Error loading fuel data: {str(e)}", exc_info=True)

async def main():
    await FuelStation.load_fuel_data(file_path_csv)

async_to_sync(main)()
