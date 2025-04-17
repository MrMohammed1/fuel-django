# Fuel Django Project

> **Note:** The commands in this guide are tailored for **PowerShell** on Windows.  
> If you are using **Linux or macOS**, you can run the same commands in **Terminal**, ensuring compatibility with your system.

## Project Overview

 This project was to build a Django-based API that calculates the optimal route between two locations in the USA, identifies cost-effective fuel stops based on fuel prices, and computes the total fuel cost for the journey. The project showcases my expertise in backend development with Django, data science, database management, containerization with Docker, CI/CD practices, and performance optimization using caching techniques.

### Task Requirements
- Build an API that takes start and finish locations within the USA.
- Return the route map with optimal fuel stops (based on fuel prices), considering a vehicle range of 500 miles.
- Calculate the total fuel cost, assuming the vehicle achieves 10 miles per gallon.
- Use a provided list of fuel prices and a free map/routing API (e.g., OpenRouteService).
- Develop the app using Django 3.2.23.
- Ensure the API is fast, with minimal calls to the map/routing API (ideally one call per request).
- Deliver the project within 3 days, including a 5-minute Loom video demonstrating the API using Postman and providing a code overview.
- Share the code via GitHub.

### My Solution
I successfully built a Django-based API that meets all the requirements:
- **Route Calculation**: The API calculates the route between two cities using a free map/routing API (e.g., OpenRouteService) with a single API call per request.
- **Distance Calculation Approach**: For calculating distances between cities and along the route, I opted to use the **Great Circle Distance** (the shortest path between two points on the surface of a sphere, also known as the "as-the-crow-flies" distance) instead of the **Driving Distance** (actual road distance). This decision was made because most services providing accurate driving distances (e.g., Google Maps Distance Matrix API, HERE API) require payment information, which was not feasible to set up within the project timeline due to temporary constraints with my payment setup. To ensure timely delivery while maintaining accuracy, I used the Great Circle Distance as a reliable approximation, calculated via the Haversine formula. This approach provides a solid foundation for route planning and can be seamlessly upgraded to incorporate driving distances using a paid API in the future if needed.
- **Fuel Stops**: The API identifies optimal fuel stops based on fuel prices, ensuring the vehicle does not exceed its 500-mile range, using the Great Circle Distance for range calculations.
- **Fuel Cost**: It computes the total fuel cost based on the approximated distance traveled and the vehicle's fuel efficiency (10 miles per gallon).
- **Performance**: I implemented caching using Redis to store computed routes, minimizing external API calls and improving response time.
- **Deployment**: The project is containerized using Docker and Docker Compose, ensuring easy setup and deployment.
- **Data Management**: I migrated the initial data to a PostgreSQL database in Docker, resolving encoding and permission issues, and performed extensive data wrangling, cleaning, and transformation to prepare the dataset for use.

## Prerequisites
- Docker and Docker Compose installed on your system.
- Git installed for cloning the repository.
- A text editor (e.g., VS Code, Notepad++) to modify configuration files.
- API keys for the following services:
  - GraphHopper (for routing, optional if using another service)
  - OpenRouteService (for routing)
  - HERE API (for routing, optional)
  - OpenCage Geocoding API (for fetching city coordinates)

## Setup Instructions

### Step 1: Clone the Repository
Clone the repository to your local machine and navigate to the project directory:
```powershell
git clone https://github.com/MrMohammed1/fuel-django
```
```powershell
cd fuel-django
```
- **Note**: The directory name `fuel-django` is the name of this repository on GitHub.

### Step 2: Configure Environment Variables
Before running the project, you need to set up the environment variables by modifying the provided example files.

#### Configure `.env` File
1. Locate the file `.env.example` in the project root directory.
2. Rename it to `.env`:
   ```powershell
   ren .env.example .env
   ```
3. Open `.env` in a text editor and add your real API keys for the following services:
   ```
   GRAPH_HOPPER_API_KEY=your-graphhopper-api-key
   OPENROUTE_API_KEY=your-openroute-api-key
   HERE_API_KEY=your-here-api-key
   OPENCAGE_API_KEY=your-opencage-api-key
   REDIS_HOST=redis
   REDIS_PORT=6379
   ```
   - Replace `your-graphhopper-api-key`, `your-openroute-api-key`, `your-here-api-key`, and `your-opencage-api-key` with the actual API keys you obtained from the respective services.
   - The `REDIS_HOST` and `REDIS_PORT` variables are set to default values that match the Redis service defined in `docker-compose.yml`. Do not change these unless you have modified the Redis service configuration.
   - **Note**: The project requires these API keys to interact with external map/routing and geocoding APIs. Without valid keys, the API will not function properly.

#### Configure `.env.docker` File
1. Locate the file `.env.docker.example` in the project root directory.
2. You can either modify it or keep it as is, depending on your PostgreSQL setup. The default values are:
   ```
   POSTGRES_DB=fuel_django
   POSTGRES_USER=postgres
   POSTGRES_PASSWORD=postgres
   ```
   - If you wish to change the database name, user, or password, update these values accordingly.
3. Rename the file to `.env.docker`:
   ```powershell
   ren .env.docker.example .env.docker
   ```
   - **Note**: Renaming both `.env.example` to `.env` and `.env.docker.example` to `.env.docker` is mandatory for the project to run successfully, as Docker and the application rely on these files for configuration.

### Step 3: Start Docker and Build the Containers

Before building and running the containers, ensure that Docker is running on your system.

- **If Docker Desktop is installed** (e.g., on Windows or macOS):
  - Launch **Docker Desktop** from your desktop or application menu.
  - Verify that Docker is running by checking the Docker Desktop interface or running the following command in a terminal or PowerShell:
    ```powershell
    docker ps
    ```
    - If no errors appear and the command executes, Docker is running.

- **If Docker is installed via command line** (e.g., on Linux, or Windows using WSL):
  - **For Windows using WSL (Windows Subsystem for Linux)**:
    1. Open a terminal and start WSL:
       ```powershell
       wsl
       ```
    2. Start the Docker service:
       ```bash
       sudo service docker start
       ```
    3. Verify that Docker is running:
       ```bash
       docker ps
       ```
       - If the command runs without errors, Docker is active.
  - **For Linux or macOS**:
    - Start Docker using the appropriate command for your system. For example, on Ubuntu:
      ```bash
      sudo service docker start
      ```
      - Alternatively, use:
        ```bash
        sudo systemctl start docker
        ```
    - Verify Docker is running:
      ```bash
      docker ps
      ```
    - If you are using a different operating system, refer to your system's documentation for starting Docker.


Once Docker is running, proceed to build and start the Docker containers in detached mode:
```powershell
docker-compose up --build -d
```
- **Note**: This command builds the Docker images and starts the containers for the web application (`fuel-django-web-1`), PostgreSQL database (`fuel-django-db-1`), and Redis (`fuel-django-redis-1`). The `--build` flag ensures that any changes in your code or configuration are applied.

### Step 4: Verify Running Containers
After running the containers, verify that they are up and running:
```powershell
docker ps
```
- You should see three containers:
  ```
  CONTAINER ID   IMAGE         COMMAND                  CREATED             STATUS             PORTS                    NAMES
  <id>           fuel-django-web     "python manage.py ru…"   <time>              Up <time>          0.0.0.0:8000->8000/tcp   fuel-django-web-1
  <id>           postgres:13   "docker-entrypoint.s…"   <time>              Up <time>          0.0.0.0:5432->5432/tcp   fuel-django-db-1
  <id>           redis:6       "docker-entrypoint.s…"   <time>              Up <time>          0.0.0.0:6379->6379/tcp   fuel-django-redis-1
  ```

### Step 5: Create Database Migrations
Since the migration files are not included in the repository (to allow flexibility for schema changes), you need to generate them for the `api` application:
```powershell
docker exec -it fuel-django-web-1 python manage.py makemigrations api
```
- This command generates migration files for the `api` application based on the models defined in `api/models.py`. You should see output like:
  ```
  Migrations for 'api':
    api/migrations/0001_initial.py
      - Create model RouteData
      - Create model CityCoordinates
      # (or other models defined in api/models.py)
  ```

### Step 6: Apply Database Migrations
Apply the database migrations to set up the schema:
```powershell
docker exec -it fuel-django-web-1 python manage.py migrate
```
- This command applies all migrations, including those for Django's built-in apps (`admin`, `auth`, etc.) and the `api` app. You should see output like:
  
  Operations to perform:
    Apply all migrations: admin, api, auth, contenttypes, sessions
  Running migrations:
    Applying contenttypes.0001_initial... OK
    Applying auth.0001_initial... OK
    ...
    Applying api.0001_initial... OK
    ...
  

### Step 7: Load Initial Data
Load the initial dataset (e.g., city coordinates and fuel stations) into the database:
```powershell
docker exec -it fuel-django-web-1 python manage.py loaddata api/fixtures/initial_data.json
```
- You should see output like:
  
  Installed X object(s) from 1 fixture(s)
  

### Step 8: Access the Application
The API is now running and can be accessed at:
```
http://localhost:8000/api/route/<start_city>/<finish_city>/
```
Example: [http://localhost:8000/api/route/big-cabin/laurel/](http://localhost:8000/api/route/big-cabin/laurel/)
- Test additional routes like:
  - [http://localhost:8000/api/route/eloy/ogallala/](http://localhost:8000/api/route/eloy/ogallala/)
  - [http://localhost:8000/api/route/latimer/willard/](http://localhost:8000/api/route/latimer/willard/)
- If you encounter errors (e.g., connection issues with Redis or database errors), check the container logs for debugging:
  ```powershell
  docker logs fuel-django-web-1
  ```

## Data Preparation

The initial dataset for this project was provided in a CSV file named `fuel-prices-for-be-assessment.csv`, which contained fuel station details such as OPIS Truckstop ID, name, city, price per gallon, and geographic coordinates. This file was processed to prepare the data for use in the application:

- **Processing Steps**:
  1. The CSV file was loaded using `pandas` in the `FuelStation.load_fuel_data` method (defined in `api/models.py`).
  2. Data wrangling and cleaning were performed, including removing duplicates, handling missing values (e.g., filling missing prices with the mean), and validating city names using regular expressions.
  3. The data was transformed by converting string prices to numeric values and preparing it for storage in the database.
  4. City coordinates were fetched asynchronously from the OpenCage Geocoding API using `aiohttp`, with caching to optimize performance.
  5. The processed data was then exported to `api/fixtures/initial_data.json` using Django's `dumpdata` command, which is now used to populate the database during setup (see **Step 7: Load Initial Data**).

- **Original File**:
  The original CSV file (`fuel-prices-for-be-assessment.csv`) is included in the repository under the `raw_data/` directory for reference and potential future reprocessing. Note that this file is not required to run the application, as the processed data is already available in `api/fixtures/initial_data.json`.

## Technical Details

### Architecture
- **Framework**: Django 3.2.23 with Django REST Framework for building the API.
- **Database**: PostgreSQL for storing city coordinates, fuel stations, and route data.
- **Caching**: Redis for caching computed routes and coordinates to minimize external API calls.
- **Containerization**: Docker and Docker Compose for containerized deployment.
- **External APIs**:
  - OpenRouteService for route calculation.
  - OpenCage Geocoding API for fetching city coordinates.
  - (Optional) GraphHopper and HERE API for alternative routing services.
- **Data Science Libraries**:
  - `pandas` for data wrangling, cleaning, and transformation.
  - `aiohttp` for asynchronous data downloading from external APIs.

### Key Components
- **Models**:
  - `CityCoordinates`: Stores city names, latitudes, and longitudes. Includes a method to fetch coordinates asynchronously from the OpenCage Geocoding API, with caching to reduce API calls.
  - `FuelStation`: Stores fuel station details (e.g., OPIS Truckstop ID, name, city, price per gallon, latitude, longitude). Includes methods for loading and processing fuel station data from a CSV file.
  - `RouteData`: Stores route information, including the start and finish cities, total distance, route points, and associated fuel stations. This model enables efficient retrieval of previously computed routes, reducing the need for repeated API calls.
- **API Endpoint**:
  - `GET /api/route/<start_city>/<finish_city>/`: Returns the route, optimal fuel stops, and total fuel cost.
  - The core logic is implemented in the `process_request` method, which:
    - Validates city name formats (lowercase with hyphens, e.g., `big-cabin`).
    - Converts the input city names to match the database format (e.g., `Big Cabin`) using the `format_city_name` utility function.
    - Fetches coordinates for the start and finish cities asynchronously.
    - Calculates the route using a single call to the map/routing API.
    - Decodes the route points using the `polyline` library.
    - Computes the total distance using the Haversine formula to calculate the Great Circle Distance between geographic coordinates (as a substitute for driving distance, as explained in the "My Solution" section).
    - Determines the fuel needed (assuming 10 miles per gallon) and identifies optimal fuel stops if the distance exceeds 500 miles, optimizing for cost based on fuel prices.
    - Returns a JSON response with the route map, fuel stops, and total fuel cost.
- **Utility Functions**:
  - `format_city_name`: Converts city names from the API input format (`big-cabin`) to the database format (`Big Cabin`) by replacing hyphens with spaces and capitalizing each word.
  - `haversine_distance`: Calculates the Great Circle Distance between two geographic points using the Haversine formula, enabling accurate distance approximations for route planning.
  - `calculate_total_distance`: Aggregates the distances between route points to determine the total route length using Great Circle Distance.
  - `calculate_gallons_needed`: Computes the amount of fuel required based on the total distance and the vehicle's fuel efficiency.
- **Data Processing**:
  - The `FuelStation.load_fuel_data` method performs data wrangling, cleaning, and transformation on a CSV dataset of fuel stations:
    - Loads the data using `pandas` with proper encoding and delimiter handling.
    - Cleans the data by removing duplicates, handling missing values (e.g., filling missing prices with the mean), and validating city names using regular expressions.
    - Transforms the data by converting string prices to numeric values and preparing it for storage in the database.
    - Downloads city coordinates asynchronously from the OpenCage Geocoding API using `aiohttp`, with caching to optimize performance.
- **Caching**:
  - Redis is used to cache computed routes and city coordinates, ensuring that repeated requests do not trigger additional API calls.

### File Structure
- `docker-compose.yml`: Defines the services (web, db, redis) and volumes for persistent data.
- `Dockerfile`: Builds the Django application container.
- `.env.example`: Template for environment variables (e.g., API keys for external services).
- `.env.docker.example`: Template for PostgreSQL environment variables.
- `pg_hba.conf`: Configures PostgreSQL authentication.
- `requirements.txt`: Lists Python dependencies (e.g., Django 3.2.23, psycopg2-binary, redis, pandas, aiohttp).
- `raw_data/fuel-prices-for-be-assessment.csv`: The original CSV dataset of fuel stations (included for reference).
- `api/fixtures/initial_data.json`: Contains the processed dataset for cities and fuel stations.
- `api/views.py`: Implements the route calculation logic and API endpoint, including the `process_request` method.
- `api/models.py`: Defines the database models (`CityCoordinates`, `FuelStation`, `RouteData`) and includes data loading and processing logic.
- `api/utils.py`: Contains utility functions, including `format_city_name`, `haversine_distance`, `calculate_total_distance`, and `calculate_gallons_needed`.

## Challenges and Solutions

During the development of this project, I encountered several challenges and addressed them effectively:

1. **Distance Calculation Approach**:
   - **Challenge**: Accurate driving distances (actual road distances) typically require paid APIs (e.g., Google Maps Distance Matrix API, HERE API), which necessitate payment information. Due to temporary constraints with my payment setup, I was unable to integrate these services within the project timeline.
   - **Solution**: I opted to use the Great Circle Distance (calculated via the Haversine formula) as a reliable approximation for route planning. This approach allowed me to deliver a functional solution on time while maintaining accuracy for the purposes of this task. The Great Circle Distance provides a solid foundation for estimating fuel stops and costs, and the system is designed to easily integrate a paid driving distance API in the future for enhanced precision.

2. **Data Migration to Docker**:
   - **Challenge**: The initial database in Docker was empty, and the data needed to be migrated from the local PostgreSQL database.
   - **Solution**: I exported the data using `dumpdata`, resolved permission issues during file copying to the container, and handled encoding issues (UTF-16 to UTF-8 conversion) to successfully load the data with `loaddata`.

3. **File Encoding Issues**:
   - **Challenge**: The `initial_data_original.json` file was encoded in UTF-16, causing a `UnicodeDecodeError` during `loaddata`.
   - **Solution**: I converted the file to UTF-8 without BOM using PowerShell and Notepad, ensuring compatibility with Django.

4. **City Name Formatting**:
   - **Challenge**: The API expected city names in lowercase with hyphens (e.g., `big-cabin`), but the database stored city names with spaces and title case (e.g., `Big Cabin`).
   - **Solution**: I implemented the `format_city_name` utility function in `utils.py` to convert the API input format (`big-cabin`) to the database format (`Big Cabin`) by replacing hyphens with spaces and capitalizing each word. This ensured compatibility between the API inputs and the database without needing to modify the database records.

5. **Data Quality and Preparation**:
   - **Challenge**: The fuel station dataset in CSV format contained inconsistencies such as missing values, duplicates, and incorrect data types.
   - **Solution**: I used `pandas` to perform data wrangling and cleaning, including removing duplicates, handling missing values by filling them with appropriate defaults (e.g., mean price for missing fuel prices), and validating city names using regular expressions. I also transformed the data by converting string prices to numeric values and prepared it for storage in the database. See the **Data Preparation** section for more details.

6. **Performance Optimization**:
   - **Challenge**: The task required minimizing calls to external APIs (e.g., map/routing API, geocoding API) to ensure fast response times.
   - **Solution**: I implemented caching with Redis to store computed routes and city coordinates, ensuring that repeated requests do not trigger additional API calls. The API now makes only one call to the map/routing API per unique route. Additionally, I used asynchronous programming in the `process_request` method and `fetch_coordinates` method to handle external API calls efficiently, and processed data in chunks to optimize database operations.

## Skills Demonstrated

This project highlights my expertise in the following areas:
- **Backend Development**: Proficient in Django and Django REST Framework for building scalable APIs.
- **Data Science**: Applied data science techniques, including:
  - **Data Wrangling and Cleaning**: Used `pandas` to clean and preprocess a fuel station dataset, handling missing values, duplicates, and data validation.
  - **Data Transformation**: Transformed raw CSV data into a structured format suitable for database storage, including type conversion and data normalization.
  - **Data Download**: Fetched city coordinates asynchronously from the OpenCage Geocoding API using `aiohttp`, with error handling and caching.
  - **Geographic Data Analysis**: Used the Haversine formula to calculate Great Circle Distances between geographic coordinates for route planning, providing a practical approximation when driving distances were not feasible.
  - **Cost Optimization**: Optimized fuel stop selection based on fuel prices, balancing cost and distance constraints.
- **Asynchronous Programming**: Used `async`/`await` in Python to handle external API calls efficiently.
- **Database Management**: Experienced with PostgreSQL, including schema design, migrations, and data integrity.
- **Performance Optimization**: Skilled in caching with Redis to improve API response times, reducing external API calls, and optimizing database operations with bulk updates and chunk processing.
- **Containerization**: Proficient in Docker and Docker Compose for containerized deployment.
- **CI/CD**: Experienced in setting up Continuous Integration and Continuous Deployment pipelines. In this project, I implemented a basic CI/CD workflow to automate testing, building, and deployment of the Docker containers, ensuring consistent and reliable releases.
- **Problem-Solving**: Addressed complex challenges such as distance calculation constraints, data migration, file encoding, city name formatting, data quality, Redis connectivity, and performance optimization.
- **Version Control**: Used Git for version control and collaboration, ensuring proper management of migration files and fixtures.

## API Usage

### Endpoint
- **GET** `/api/route/<start_city>/<finish_city>/`
  - **Description**: Calculates the optimal route between two cities, identifies cost-effective fuel stops, and computes the total fuel cost.
  - **Parameters**:
    - `start_city`: Starting city in lowercase with hyphens (e.g., `big-cabin` for "Big Cabin").
    - `finish_city`: Destination city in lowercase with hyphens (e.g., `laurel` for "Laurel").
  - **Example Request**:
    ```
    GET http://localhost:8000/api/route/big-cabin/laurel/
    ```


### Testing with Postman
1. Open Postman and create a new GET request.
2. Enter the URL, e.g., `http://localhost:8000/api/route/big-cabin/laurel/`.
3. Send the request and verify the response matches the expected format.

## Troubleshooting

If you encounter issues while setting up or running the project, here are some common problems and solutions:

1. **Error: "relation 'api_routedata' does not exist"**
   - **Cause**: The database migrations for the `api` app were not applied.
   - **Solution**: Ensure you ran both `makemigrations` and `migrate`:
     ```powershell
     docker exec -it fuel-django-web-1 python manage.py makemigrations api
     docker exec -it fuel-django-web-1 python manage.py migrate
     ```

2. **Error: "No fixture named 'initial_data' found"**
   - **Cause**: The `initial_data.json` file is missing or not in the correct location.
   - **Solution**:
     1. Verify that `initial_data.json` exists in `api/fixtures/`.
     2. If the file is missing, you may need to create it or obtain it from the repository owner.
     3. Rebuild the Docker image to include the file:
        ```powershell
        docker-compose down
        docker-compose up --build -d
        ```
     4. Run the `loaddata` command again:
        ```powershell
        docker exec -it fuel-django-web-1 python manage.py loaddata api/fixtures/initial_data.json
        ```

3. **Error: "OPENCAGE_API_KEY not found"**
   - **Cause**: The API keys in the `.env` file are missing or incorrect.
   - **Solution**: Ensure your `.env` file contains valid API keys:
     ```
     OPENCAGE_API_KEY=your-opencage-api-key
     ```
     Then, restart the containers:
     ```powershell
     docker-compose down
     docker-compose up --build -d
     ```

4. **Application Not Responding or Returning Errors**
   - **Solution**: Check the container logs for detailed error messages:
     ```powershell
     docker logs fuel-django-web-1
     ```
     - If the logs indicate a database connection issue, ensure the `db` service is running and healthy (`docker ps`).


## Future Improvements
- **Integrate Driving Distance API**: Replace Great Circle Distance with actual driving distances using a paid API (e.g., Google Maps Distance Matrix API) for more accurate route planning

