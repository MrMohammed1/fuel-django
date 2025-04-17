from django.urls import path
from .views import TripPlanner

urlpatterns = [
    path('route/<str:start_city>/<str:finish_city>/', TripPlanner.as_view(), name='route_with_fuel'),
       

]
