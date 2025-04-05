from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'points-of-interest', views.PointOfInterestViewSet)
router.register(r'restaurants', views.RestaurantViewSet)
router.register(r'events', views.EventViewSet)
router.register(r'itineraries', views.ItineraryViewSet)

urlpatterns = [
    path('', views.health_check, name='health_check'),
    path('api/', include(router.urls)),
] 