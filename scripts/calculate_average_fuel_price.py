import os
import sys
import django
from django.db.models import Avg


# Add project root to sys.path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BASE_DIR)

# Set up Django environment
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "fuel_route.settings")
django.setup()


from api.models import FuelStation

def calculate_average_fuel_price():
    """Calculate the average fuel price from the FuelStation table."""
    try:
        # Calculate the average price_per_gallon
        result = FuelStation.objects.aggregate(avg_price=Avg("price_per_gallon"))
        average_fuel_price = result["avg_price"]
            

        return average_fuel_price

    except Exception as e:
        raise Exception(f"Failed to calculate average fuel price: {str(e)}")

def save_average_fuel_price(average_price):
    """Save the average fuel price to a Python file for easy import."""
    try:
        with open("scripts/average_fuel_price.py", "w", encoding="utf-8") as f:
            f.write("# Generated average fuel price from database\n")
            f.write("# Note: we will use this value to calculate fuel cost in case of the distance between two locations less than 500 miles\n")
            f.write(f"AVERAGE_FUEL_PRICE = {average_price}\n")
    except Exception as e:
        raise Exception(f"Failed to save average fuel price to file: {str(e)}")

def main():
    """Main function to calculate and save the average fuel price."""
    try:
        print(" Fetching data from the database...")
        average_fuel_price = calculate_average_fuel_price()
        print(f" Calculated average fuel price: {average_fuel_price:.2f} USD/gallon")

        print(" Saving data to scripts/average_fuel_price.py...")
        save_average_fuel_price(average_fuel_price)
        print(" Average fuel price successfully saved to scripts/average_fuel_price.py!")

    except Exception as e:
        print(f" An error occurred: {e}")

if __name__ == "__main__":
    main()