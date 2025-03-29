import time
import polyline
import logging
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from asgiref.sync import async_to_sync
from scipy.spatial import KDTree
from scripts.average_fuel_price import AVERAGE_FUEL_PRICE
from .utils import (
    haversine_distance,
    fetch_coordinate,
    calculate_total_distance,
    get_fuel_stations,
    get_route,
    format_city_name,
    calculate_gallons_needed,
)

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
handler = logging.FileHandler('TripPlanner.log')
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)

class TripPlanner(APIView):
    """API endpoint to calculate the optimal fuel stations along a route."""
    # AVERAGE_FUEL_PRICE = 3.43 

    def __init__(self, fuel_capacity=500, miles_per_gallon=10, safety_margin=50, max_distance=100):
        """
        Initializes the TripPlanner with fuel and search parameters.

        Args:
            fuel_capacity (float): Maximum fuel capacity in miles.
            miles_per_gallon (float): Fuel efficiency in miles per gallon.
            safety_margin (float): Minimum fuel reserve before refueling.
            max_distance (float): Maximum search radius for fuel stations.
        """
        self.fuel_capacity = fuel_capacity
        self.miles_per_gallon = miles_per_gallon
        self.safety_margin = safety_margin
        self.max_distance = max_distance  # Max search radius for fuel stations

    @async_to_sync
    async def get(self, request, start_city, finish_city):
        """
        Handles GET request for trip planning.
        
        Args:
            request (Request): HTTP request object.
            start_city (str): Starting city name.
            finish_city (str): Destination city name.

        Returns:
            Response: JSON response with route and fuel station details.
        """
        return await self.process_request(request, start_city, finish_city)

    async def process_request(self, request, start_city, finish_city):
        """
        Processes the request to fetch route details and calculate fuel costs.

        Args:
            request (Request): HTTP request object.
            start_city (str): Start city name.
            finish_city (str): Destination city name.

        Returns:
            Response: JSON response containing the route, fuel stations, and estimated fuel cost.
        """
        start_time = time.time()

        # Validate city name format (must be lowercase with hyphens)
        if not start_city.islower() or not finish_city.islower() or " " in start_city or " " in finish_city:
            logger.warning("Invalid city name format detected.")
            return Response(
                {"error": "Invalid city name format. Use lowercase with hyphens between words (e.g., gila-bend)."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        formatted_start_city = format_city_name(start_city)
        formatted_finish_city = format_city_name(finish_city)

        # Ensure start and finish cities are not the same
        if formatted_start_city == formatted_finish_city:
            logger.warning("Start and finish cities are the same.")
            return Response(
                {"error": "The starting city and the destination city cannot be the same."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Fetch coordinates for both cities
        start_coords = await fetch_coordinate(formatted_start_city)
        finish_coords = await fetch_coordinate(formatted_finish_city)

        if not start_coords or not finish_coords:
            logger.error("Failed to fetch coordinates for one or both cities.")
            return Response(
                {"error": "Only cities within the United States are available."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Get the route data from start to finish
        route_data = await get_route(start_coords, finish_coords)
        if "error" in route_data:
            logger.error(f"Route fetching failed: {route_data.get('error')}")
            return Response(
                route_data,
                status=route_data.get("status", status.HTTP_500_INTERNAL_SERVER_ERROR),
            )
        try:
            if "paths" in route_data and route_data["paths"]:
                encoded_points = route_data["paths"][0]["points"]
            elif "routes" in route_data and route_data["routes"]:
                encoded_points = polyline.encode(route_data["routes"][0]["geometry"]["coordinates"]) 
            else:
                logger.error("No valid route found in route_data.")
                return Response({"error": "No valid route found", "details": route_data}, status=400)

            route_points = polyline.decode(encoded_points)
            
        except (KeyError, IndexError, ValueError) as e:
            logger.error(f"Error processing route data: {str(e)}")
            return Response(
                {"error": "Error processing route data", "details": str(e), "raw_data": route_data},
                status=400
            )

        # Ensure the route is valid
        if len(route_points) < 2:
            logger.error("Invalid route: fewer than 2 points.")
            return Response(
                {
                    "error": "Could not calculate a valid route between these cities."
                    " They might be too far apart or not connected by roads."
                    " Please check the city names and try again."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Calculate total route distance and fuel needed
        total_distance = calculate_total_distance(route_points)
        gallons_needed = calculate_gallons_needed(total_distance)

        # Fetch fuel stations along the route
        max_distance = self.max_distance
        fueling_stations = await get_fuel_stations(route_points)

        # Determine the best fuel stations and total fuel cost
        if total_distance > 500:
            optimal_stations, total_fuel_cost = self.select_fuel_stations(
                route_points, fueling_stations, max_distance
            )
        else:
            optimal_stations = []
            total_fuel_cost = gallons_needed * AVERAGE_FUEL_PRICE

        execution_time = time.time() - start_time
        print(f"Execution time: {execution_time:.4f} seconds")  # يبقى print كما هو
        if "paths" in route_data and route_data["paths"]:
            route_data["paths"][0]["points"] = polyline.encode(route_points)
        elif "routes" in route_data and route_data["routes"]:
            route_data["routes"][0]["geometry"]["coordinates"] = polyline.encode(route_points)

        # Return final response with route and fuel details
        logger.info("Successfully processed trip request.")
        return Response(
            {
                "route_map": {
                    "coordinates": route_data,
                    "total_distance": total_distance,
                },
                "optimal_stations": (
                    [
                        {
                            "opis_truckstop_id": station[0],
                            "address": station[1],
                            "price_per_gallon": station[2],
                            "miles_from_start": station[3],
                        }
                        for station in optimal_stations
                    ]
                    if optimal_stations
                    else "no stations as distance less than 500 miles"
                ),
                "total_fuel_cost": total_fuel_cost,
            }
        )

    def can_complete_trip(self, route_points, fuel_stations, max_distance):
        """
        Simulates the trip in advance to determine if it can be completed 
        without running out of fuel at any point.

        Args:
            route_points (list of tuples): List of (latitude, longitude) points representing the route.
            fuel_stations (list of tuples): List of available fuel stations with their coordinates and prices.
            max_distance (float): Maximum distance to search for a fuel station.

        Returns:
            bool: True if the trip is feasible, False if refueling is impossible at any stage.
        """
        # Moved this check to the beginning to fix test_can_complete_trip_failure
        if not fuel_stations:
            logger.warning("No fuel stations available for trip simulation.")
            return False

        station_coords = [(s[3], s[4]) for s in fuel_stations]  # Extract station coordinates
        kdtree = KDTree(station_coords) if station_coords else None  # Create KDTree for fast nearest-neighbor search

        remaining_range = self.fuel_capacity  # Current fuel range
        total_distance = calculate_total_distance(route_points)  # Total trip distance
        remaining_distance_to_end = total_distance  # Distance left to reach the destination

        for i in range(len(route_points) - 1):
            # Calculate distance between consecutive route points
            distance_segment = haversine_distance(
                route_points[i][0], route_points[i][1],
                route_points[i + 1][0], route_points[i + 1][1]
            )

            remaining_range -= distance_segment  # Reduce fuel range
            remaining_distance_to_end -= distance_segment  # Update remaining distance

            # Check if fuel is running low and the trip is not close to completion
            if remaining_range < self.safety_margin and remaining_distance_to_end > self.safety_margin:
                best_station = self.find_cheapest_station(kdtree, route_points[i], fuel_stations, set())
                if not best_station:
                    logger.warning("No fuel station found when needed during trip simulation.")
                    return False  # No fuel station nearby when needed -> Trip is not possible

                remaining_range = self.fuel_capacity  # Assume refueling to full tank

        return True  # Trip can be completed successfully
  
    def select_fuel_stations(self, route_points, fuel_stations, max_distance):
        """
        Selects the optimal fuel stations along a route to minimize cost while ensuring 
        the vehicle never runs out of fuel.

        Args:
            route_points (list): List of (latitude, longitude) tuples representing the route.
            fuel_stations (list): List of fuel stations with their details.
            max_distance (float): Maximum search radius for fuel stations.

        Returns:
            tuple: A list of selected fuel stations and the total estimated fuel cost.
        """
        if not route_points or len(route_points) < 2:
            logger.error("Route must have at least two points.")
            return [], 0.0

        # Prepare KDTree for fast fuel station lookup
        station_coords = [(s[3], s[4]) for s in fuel_stations]
        kdtree = KDTree(station_coords) if station_coords else None
        total_distance = calculate_total_distance(route_points)
        optimal_stations = []
        visited_station_ids = set()
        total_fuel_cost = 0.0
        remaining_range = self.fuel_capacity
        remaining_distance_to_end = total_distance

        # Check if the trip is feasible before starting
        if not self.can_complete_trip(route_points, fuel_stations, max_distance):
            logger.info("Trip requires staged refueling.")
            # Modified to handle staged refueling result to fix test_select_fuel_stations_success
            stages, _ = self.split_route_into_stages(route_points, fuel_stations)
            current_position = 0.0
            for stage_point, station in stages:
                current_position += haversine_distance(
                    route_points[0][0], route_points[0][1],
                    stage_point[0], stage_point[1]
                )
                fuel_needed = self.fuel_capacity - remaining_range
                cost = (fuel_needed / self.miles_per_gallon) * station[2]
                total_fuel_cost += cost
                optimal_stations.append((
                    station[0],
                    station[1] if station[1] else 'not specified',
                    station[2],
                    round(current_position, 2),
                    round(cost, 2)
                ))
                remaining_range = self.fuel_capacity
            return optimal_stations, round(total_fuel_cost, 2)

        # Find the cheapest station near the starting point
        start_location = route_points[0]
        # Added to handle empty fuel_stations case to fix test_select_fuel_stations_no_stations
        if not fuel_stations:
            logger.warning("No fuel stations available near the starting point.")
            return [], 0.0
        cheapest_start_station = self.find_cheapest_station(kdtree, start_location, fuel_stations, visited_station_ids)

        if not cheapest_start_station:
            logger.warning("No fuel stations available near the starting point.")
            return [], 0.0

        # Initial refueling cost
        initial_fuel_cost = (self.fuel_capacity / self.miles_per_gallon) * cheapest_start_station[2]
        total_fuel_cost += initial_fuel_cost
        remaining_range = self.fuel_capacity

        current_position = 0.0  # Tracks distance covered along the route

        # Iterate over the route and refuel when needed
        for i in range(len(route_points) - 1):
            distance_segment = haversine_distance(
                route_points[i][0], route_points[i][1], 
                route_points[i + 1][0], route_points[i + 1][1]
            )

            current_position += distance_segment
            remaining_range -= distance_segment
            remaining_distance_to_end -= distance_segment

            # Refuel if running low on fuel and still far from destination
            if remaining_range < self.safety_margin and remaining_distance_to_end > self.safety_margin:
                best_station = self.find_cheapest_station(kdtree, route_points[i], fuel_stations, visited_station_ids)
                if not best_station:
                    logger.warning("No available fuel stations for refueling.")
                    return [], total_fuel_cost

                visited_station_ids.add(best_station[0])

                # Calculate the fuel needed for the next leg of the journey
                fuel_needed = min(self.fuel_capacity, remaining_distance_to_end) - remaining_range
                if fuel_needed > 0:
                    cost = (fuel_needed / self.miles_per_gallon) * best_station[2]
                    total_fuel_cost += cost
                    remaining_range += fuel_needed

                    optimal_stations.append((
                        best_station[0],  # Station ID
                        best_station[1] if best_station[1] else 'not specified',  # Address
                        best_station[2],  # Price per gallon
                        round(current_position, 2),  # Distance from start
                        round(cost, 2)  # Fuel cost at this station
                    ))

        # Sort stations by distance from the start
        optimal_stations.sort(key=lambda x: x[3])
        return optimal_stations, round(total_fuel_cost, 2)

    def split_route_into_stages(self, route_points, fuel_stations):
        """
        Splits a long route into stages based on fuel constraints, ensuring refueling 
        at optimal stations along the way.

        Args:
            route_points (list): List of (latitude, longitude) tuples representing the route.
            fuel_stations (list): List of available fuel stations with their details.

        Returns:
            tuple: A list of stages where refueling is needed and a message indicating staged refueling.
        """
        stages = []
        current_position = 0.0
        remaining_range = self.fuel_capacity
        total_distance = calculate_total_distance(route_points)
        remaining_distance_to_end = total_distance

        # Prepare KDTree for fast nearest station lookup
        station_coords = [(s[3], s[4]) for s in fuel_stations]
        kdtree = KDTree(station_coords) if station_coords else None

        for i in range(len(route_points) - 1):
            # Calculate distance between consecutive route points
            distance_segment = haversine_distance(
                route_points[i][0], route_points[i][1],
                route_points[i + 1][0], route_points[i + 1][1]
            )

            current_position += distance_segment
            remaining_range -= distance_segment
            remaining_distance_to_end -= distance_segment

            # Check if refueling is needed
            if remaining_range < self.safety_margin:
                best_station = self.find_cheapest_station(kdtree, route_points[i], fuel_stations, set())

                # If no station found, expand search radius gradually
                search_radius = self.max_distance * 3
                while not best_station and search_radius <= self.max_distance * 5:
                    best_station = self.find_cheapest_station(kdtree, route_points[i], fuel_stations, set())
                    search_radius += self.max_distance
                
                # If a suitable station is found, record it as a refueling stage
                if best_station:
                    stages.append((route_points[i], best_station))
                    remaining_range = self.fuel_capacity  # Refuel to full capacity

        logger.info("Route split into stages for refueling.")
        return stages, "Trip requires staged refueling"

    def find_cheapest_station(self, kdtree, search_point, fuel_stations, visited_station_ids):
        """
        Finds the cheapest nearby fuel station within a dynamically expanding search radius.

        Args:
            kdtree (KDTree): KDTree containing fuel station coordinates for fast lookup.
            search_point (tuple): (latitude, longitude) of the current location.
            fuel_stations (list): List of available fuel stations.
            visited_station_ids (set): Set of station IDs already visited.

        Returns:
            tuple or None: The best fuel station (ID, address, price, lat, lon) or None if no station is found.
        """
        # Added to handle None case to fix test_select_fuel_stations_no_stations and test_find_cheapest_station_none
        if kdtree is None:
            return None

        max_possible_distance = self.fuel_capacity * self.miles_per_gallon  # Maximum possible travel distance
        search_radius = min(self.max_distance, max_possible_distance)
        while search_radius <= max_possible_distance:
            # Find stations within the current search radius
            nearby_indices = kdtree.query_ball_point(search_point, search_radius)
            available_stations = [
                fuel_stations[idx] for idx in nearby_indices if fuel_stations[idx][0] not in visited_station_ids
            ]

            # If stations are found, choose the cheapest one based on price and distance
            if available_stations:
                return min(
                    available_stations,
                    key=lambda s: (s[2], haversine_distance(search_point[0], search_point[1], s[3], s[4]))
                )

            # Expand search radius: Initially double it for speed, then switch to linear growth
            if search_radius * 2 <= max_possible_distance / 2:
                search_radius *= 2
            else:
                search_radius = min(search_radius + self.max_distance, max_possible_distance)

        return None  # Return None if no suitable station is found