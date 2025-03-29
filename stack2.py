import asyncio
import os
import django
import aiohttp
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "fuel_route.settings")
django.setup()
from api.models import CityCoordinates,FuelStation
from asgiref.sync import sync_to_async
import pandas as pd



# from django.db import connection

# with connection.cursor() as cursor:
#     cursor.execute("SELECT id, city, latitude, longitude FROM api_citycoordinates WHERE latitude IN (0, 0.0, '0', '0.0') OR longitude IN (0, 0.0, '0', '0.0');")
#     rows = cursor.fetchall()

# print(f"🔍 عدد المدن التي تحتوي على أي شكل من أشكال 0: {len(rows)}")
# for row in rows[:10]:  # طباعة أول 10 نتائج فقط
#     print(row)
import os
import django
from django.db.models import Avg
from api.models import FuelStation

# تهيئة بيئة Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "fuel_route.settings")
django.setup()

# حساب متوسط السعر مرة واحدة فقط
average_fuel_price = FuelStation.objects.aggregate(avg_price=Avg("price_per_gallon"))["avg_price"]

# حفظ القيمة في ملف الإعدادات (settings.py)
if average_fuel_price is not None:
    with open("average_fuel_price.txt", "w") as f:
        f.write(str(average_fuel_price))

print(f"✅ تم حساب وتخزين متوسط سعر الوقود: {average_fuel_price}")






# مسار ملف CSV
# CSV_FILE_PATH = r"D:\\fuel-prices-for-be-assessment.csv"

# async def update_opis_truckstop_id():
#     """ تحديث `opis_truckstop_id` في قاعدة البيانات باستخدام بيانات CSV """
    
#     print("📥 تحميل بيانات CSV...")
    
#     # **تحميل بيانات CSV**
#     df = pd.read_csv(
#         CSV_FILE_PATH,
#         encoding='ISO-8859-1',
#         dtype={'Truckstop Name': str, 'OPIS Truckstop ID': str},
#         delimiter=';',
#         quotechar='"',
#         engine='c'
#     )

#     # **تنظيف البيانات وإزالة القيم الفارغة**
#     df = df[['Truckstop Name', 'OPIS Truckstop ID']].dropna()

#     # **تحويل البيانات إلى قاموس لمطابقة سريعة**
#     opis_id_map = {str(row['Truckstop Name']).strip(): str(row['OPIS Truckstop ID']).strip() for _, row in df.iterrows()}

#     print(f"🔍 عدد المحطات في CSV: {len(opis_id_map)}")
    
#     # **جلب جميع المحطات التي لا تحتوي على `opis_truckstop_id` (Null أو فارغ)**
#     stations_to_update = await sync_to_async(
#         lambda: list(FuelStation.objects.filter(opis_truckstop_id__isnull=True))
#     )()

#     print(f"🛠️ عدد المحطات التي تحتاج تحديث: {len(stations_to_update)}")
    
#     updated_count = 0

#     # **تحديث المحطات التي تتطابق أسماؤها مع بيانات CSV**
#     for station in stations_to_update:
#         new_opis_id = opis_id_map.get(station.name.strip())  # البحث باستخدام `name`
        
#         if new_opis_id and new_opis_id.lower() not in ["null", "", "none"]:  # التأكد من أن القيمة صالحة
#             # ✅ التحقق مما إذا كان `opis_truckstop_id` مستخدمًا بالفعل
#             exists = await sync_to_async(lambda: FuelStation.objects.filter(opis_truckstop_id=new_opis_id).exists())()
            
#             if not exists:  # لا يوجد سجل آخر بنفس `opis_truckstop_id`
#                 station.opis_truckstop_id = new_opis_id
#                 await sync_to_async(lambda: station.save())()  # حفظ التحديث
#                 updated_count += 1
#                 print(f"✅ تم تحديث `opis_truckstop_id` للمحطة {station.name} -> {new_opis_id}")
#             else:
#                 print(f"⚠️ تم تخطي {station.name} لأن `opis_truckstop_id` {new_opis_id} مستخدم بالفعل!")

#     print(f"\n🚀 تم تحديث {updated_count} محطة بنجاح!")

# # تشغيل السكربت
# asyncio.run(update_opis_truckstop_id())



# async def count_unique_opis_ids():
#     """ حساب عدد القيم الفريدة وغير الفريدة لـ `opis_truckstop_id` """

#     print("📊 جاري استخراج بيانات `opis_truckstop_id` ...")
    
#     # **جلب جميع القيم غير الفارغة من قاعدة البيانات**
#     opis_ids = await sync_to_async(lambda: list(FuelStation.objects.exclude(opis_truckstop_id__isnull=True).values_list('opis_truckstop_id', flat=True)))()

#     print(f"📌 عدد القيم غير الفارغة في `opis_truckstop_id`: {len(opis_ids)}")

#     # **تحويلها إلى مجموعة `set` للحصول على القيم الفريدة**
#     unique_opis_ids = set(opis_ids)

#     print(f"✅ عدد القيم الفريدة في `opis_truckstop_id`: {len(unique_opis_ids)}")

#     # **حساب عدد القيم المكررة**
#     duplicate_count = len(opis_ids) - len(unique_opis_ids)
#     print(f"⚠️ عدد القيم المكررة في `opis_truckstop_id`: {duplicate_count}")

# # تشغيل السكربت
# asyncio.run(count_unique_opis_ids())





# API_KEY = "2173b7201e034c3d97fc76eb132f5ac1"
# API_KEY = "3f24008e7a5c49ac918a87e4e5297da9"

# async def update_wrong_coordinates():
#     async with aiohttp.ClientSession() as session:
#         try:
#             # جلب المدن التي تحتاج تحديث بشكل غير متزامن
#             cities_to_update = await sync_to_async(
#                 lambda: list(FuelStation.objects.filter(latitude=0, longitude=0))
#             )()

#             for city in cities_to_update:
#                 print(city)
#                 try:
#                     url = f"https://api.opencagedata.com/geocode/v1/json?q={city.city}&key={API_KEY}"
                    
#                     async with session.get(url, timeout=10) as response:
#                         if response.status == 200:
#                             data = await response.json()
#                             if data and data.get("results"):
#                                 lat = data["results"][0]["geometry"]["lat"]
#                                 lon = data["results"][0]["geometry"]["lng"]
                                
#                                 # تحديث قاعدة البيانات
#                                 await sync_to_async(
#                                     lambda: CityCoordinates.objects.filter(city=city.city).update(latitude=lat, longitude=lon)
#                                 )()
                                
#                                 print(f"✅ تم تحديث: {city.city} -> ({lat}, {lon})")
#                         else:
#                             print(f"⚠️ فشل في جلب الإحداثيات لـ {city.city}: كود الاستجابة {response.status}")
                
#                 except Exception as e:
#                     print(f"❌ خطأ أثناء تحديث {city.city}: {e}")

#         except Exception as e:
#             print(f"❌ خطأ عام في تحديث الإحداثيات: {e}")

# asyncio.run(update_wrong_coordinates())
# import cProfile
# import pstats
# import asyncio
# import os
# import django
# os.environ.setdefault("DJANGO_SETTINGS_MODULE", "fuel_route.settings")
# django.setup()
# from api.views import RouteWithFuel
# from rest_framework.request import Request
# from rest_framework.test import APIRequestFactory

# def main():
#     """ الدالة الرئيسية لتشغيل تحليل الأداء """
#     route_fuel = RouteWithFuel()
    
#     # إنشاء كائن طلب وهمي
#     factory = APIRequestFactory()
#     dummy_request = factory.get('/dummy-path/')  # طلب GET وهمي
    
#     # استدعاء الوظائف التي تريد تحليلها
#     asyncio.run(route_fuel.fetch_coordinate("New York"))
#     asyncio.run(route_fuel.get_route((40.7128, -74.0060), (34.0522, -118.2437)))
#     asyncio.run(route_fuel.get_fuel_stations([(40.7128, -74.0060), (39.9526, -75.1652)]))
    
#     # تحليل أداء الدوال الإضافية المطلوبة
#     asyncio.run(route_fuel.get_city_coordinates("Los Angeles"))
#     asyncio.run(route_fuel.get_cached_route("NYC-LA"))
#     asyncio.run(route_fuel.process_request(dummy_request, "New York", "Los Angeles"))  # تمرير request وهمي
#     asyncio.run(route_fuel.get_nearby_stations(40.0, 41.0, -75.0, -74.0))
#     # استدعاء مباشر لأنها ليست دالة غير متزامنة
#     miles = route_fuel.calculate_miles_from_start([(40.7128, -74.0060), (39.9526, -75.1652)], (39.9526, -75.1652))
#     print(f"Miles from start: {miles}")
#     # asyncio.run(route_fuel.select_fuel_stations([(40.7128, -74.0060), (39.9526, -75.1652)], [], 50))
    
#     # تحليل أداء دالة حساب المسافة الجغرافية
#     distance = route_fuel.haversine_distance(40.7128, -74.0060, 34.0522, -118.2437)
#     print(f"Calculated Distance: {distance} miles")

# if __name__ == "__main__":
#     profiler = cProfile.Profile()  # إنشاء كائن لتحليل الأداء
#     profiler.enable()  # بدء التحليل
    
#     main()  # تشغيل الوظائف المحددة
    
#     profiler.disable()  # إيقاف التحليل

#     # حفظ البيانات في ملف
#     with open("profile_output.prof", "w") as f:
#         stats = pstats.Stats(profiler, stream=f)
#         stats.sort_stats("cumulative")  # ترتيب حسب الوقت التراكمي
#         stats.print_stats()
    
#     print("✅ تم حفظ تقرير الأداء في profile_output.prof")

import asyncio
import os
import django
from django.db.models import Q
from asgiref.sync import sync_to_async
from api.models import CityCoordinates, FuelStation

# تهيئة بيئة Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "fuel_route.settings")
django.setup()

async def fetch_city_coordinates():
    """جلب إحداثيات المدن من قاعدة البيانات."""
    # جلب إحداثيات big-cabin وlaurel (يمكن تعديل الشروط حسب الحاجة)
    cities = await sync_to_async(
        lambda: list(CityCoordinates.objects.filter(
            Q(city__iexact="big-cabin") | Q(city__iexact="laurel")
        ).values("city", "latitude", "longitude"))
    )()

    # تحويل الإحداثيات إلى قاموس لسهولة الوصول
    city_coords = {city["city"]: (city["latitude"], city["longitude"]) for city in cities}
    return city_coords

async def fetch_fuel_stations():
    """جلب مواقع محطات الوقود من قاعدة البيانات."""
    stations = await sync_to_async(
        lambda: list(FuelStation.objects.all().values("id", "name", "price_per_gallon", "latitude", "longitude"))
    )()
    return [
        (str(station["id"]), station["name"] or "N/A", station["price_per_gallon"], station["latitude"], station["longitude"])
        for station in stations
    ]

async def generate_mock_data():
    """إنشاء بيانات محاكاة ديناميكية بناءً على قاعدة البيانات."""
    # جلب الإحداثيات
    city_coords = await fetch_city_coordinates()
    fuel_stations = await fetch_fuel_stations()

    # التحقق من وجود big-cabin وlaurel
    if "big-cabin" not in city_coords or "laurel" not in city_coords:
        raise ValueError("لم يتم العثور على إحداثيات big-cabin أو laurel في قاعدة البيانات!")

    # إنشاء MOCK_ROUTE_POINTS (مسار مبسط بين big-cabin وlaurel مع نقاط وسطية)
    big_cabin_coords = city_coords["big-cabin"]
    laurel_coords = city_coords["laurel"]
    # إضافة نقاط وسطية تقريبية بناءً على الانتقال التدريجي (يمكن تحسينها لاحقًا)
    mid_points = [
        (
            big_cabin_coords[0] - (i * (big_cabin_coords[0] - laurel_coords[0]) / 4),
            big_cabin_coords[1] - (i * (big_cabin_coords[1] - laurel_coords[1]) / 4)
        )
        for i in range(1, 4)
    ]
    MOCK_ROUTE_POINTS = [big_cabin_coords] + mid_points + [laurel_coords]

    # تصفية المحطات القريبة من المسار (يمكن تحسين هذا الجزء باستخدام KDTree لاحقًا)
    MOCK_FUEL_STATIONS = [
        station for station in fuel_stations
        if any(
            abs(station[3] - point[0]) < 5 and abs(station[4] - point[1]) < 5
            for point in MOCK_ROUTE_POINTS
        )
    ]

    return MOCK_ROUTE_POINTS, MOCK_FUEL_STATIONS

def save_mock_data(route_points, fuel_stations):
    """حفظ البيانات المحاكاة في ملف لاستخدامه في الاختبارات."""
    with open("mock_data.py", "w", encoding="utf-8") as f:
        f.write("# Generated mock data from database\n")
        f.write("MOCK_ROUTE_POINTS = [\n")
        for point in route_points:
            f.write(f"    ({point[0]}, {point[1]}),  # Approximate midway point\n")
        f.write("]\n\n")
        f.write("MOCK_FUEL_STATIONS = [\n")
        for station in fuel_stations:
            f.write(f"    (\"{station[0]}\", \"{station[1]}\", {station[2]}, {station[3]}, {station[4]}),  # {station[1]}\n")
        f.write("]\n")

async def main():
    """الدالة الرئيسية لتشغيل السكربت."""
    try:
        print("📥 جاري جلب البيانات من قاعدة البيانات...")
        route_points, fuel_stations = await generate_mock_data()
        print(f"✅ تم إنشاء {len(route_points)} نقاط مسار و{len(fuel_stations)} محطات وقود.")
        
        print("💾 جاري حفظ البيانات في ملف mock_data.py...")
        save_mock_data(route_points, fuel_stations)
        print("🚀 تم حفظ البيانات بنجاح في mock_data.py!")
    except Exception as e:
        print(f"❌ حدث خطأ: {e}")

if __name__ == "__main__":
    asyncio.run(main())








