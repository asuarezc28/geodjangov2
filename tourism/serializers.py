from rest_framework import serializers
from django.contrib.auth.models import User
from .models import PointOfInterest, Restaurant, Event, Itinerary, ItineraryPoint, ItineraryReview, ReviewPhoto

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email']

class PointOfInterestSerializer(serializers.ModelSerializer):
    class Meta:
        model = PointOfInterest
        fields = ['id', 'name', 'description', 'address', 'type',
                 'difficulty', 'estimated_time', 'created_at', 'updated_at']

class RestaurantSerializer(serializers.ModelSerializer):
    class Meta:
        model = Restaurant
        fields = ['id', 'name', 'description', 'address',
                 'cuisine_type', 'price_range', 'opening_hours', 'created_at', 'updated_at']

class EventSerializer(serializers.ModelSerializer):
    class Meta:
        model = Event
        fields = ['id', 'name', 'description', 'address',
                 'start_date', 'end_date', 'price', 'url', 'created_at', 'updated_at']

class ReviewPhotoSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReviewPhoto
        fields = ['id', 'photo', 'caption', 'uploaded_at']

class ItineraryReviewSerializer(serializers.ModelSerializer):
    photos = ReviewPhotoSerializer(many=True, read_only=True)
    
    class Meta:
        model = ItineraryReview
        fields = ['id', 'rating', 'comment', 'created_at', 'updated_at',
                 'scenery_rating', 'accessibility_rating', 'signposting_rating',
                 'cleanliness_rating', 'services_rating', 'photos']

class ItineraryPointSerializer(serializers.ModelSerializer):
    point_details = serializers.SerializerMethodField()

    class Meta:
        model = ItineraryPoint
        fields = ['id', 'day', 'order', 'notes', 'point_details',
                 'point_of_interest', 'restaurant', 'event']
        read_only_fields = ['id']

    def get_point_details(self, obj):
        """
        Devuelve los detalles del punto según su tipo (POI, restaurante o evento)
        """
        if obj.point_of_interest:
            return PointOfInterestSerializer(obj.point_of_interest).data
        elif obj.restaurant:
            return RestaurantSerializer(obj.restaurant).data
        elif obj.event:
            return EventSerializer(obj.event).data
        return None

class ItinerarySerializer(serializers.ModelSerializer):
    points = ItineraryPointSerializer(many=True, read_only=True)
    user = UserSerializer(read_only=True)

    class Meta:
        model = Itinerary
        fields = ['id', 'title', 'description', 'start_date', 'end_date',
                 'user', 'points', 'created_at', 'updated_at']
        read_only_fields = ['id', 'user', 'created_at', 'updated_at']

class ItineraryCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Itinerary
        fields = ['id', 'title', 'description', 'start_date', 'end_date']
        read_only_fields = ['id']

    def validate(self, data):
        """
        Verifica que la fecha de inicio sea anterior a la fecha de fin
        """
        if data['start_date'] > data['end_date']:
            raise serializers.ValidationError(
                "La fecha de inicio debe ser anterior a la fecha de fin"
            )
        return data

# Serializadores para crear/actualizar puntos de itinerario
class ItineraryPointCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = ItineraryPoint
        fields = ['itinerary', 'point_of_interest', 'restaurant', 'event',
                 'day', 'order', 'notes'] 