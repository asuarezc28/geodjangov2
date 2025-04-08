from django.shortcuts import render
from rest_framework import viewsets, filters
from rest_framework.decorators import action, api_view
from rest_framework.response import Response
from django.contrib.gis.geos import Point
from django.contrib.gis.db.models.functions import Distance
from django.contrib.gis.measure import D
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter
from .models import PointOfInterest, Restaurant, Event, Itinerary, ItineraryPoint, ItineraryReview
from .serializers import (
    PointOfInterestSerializer, RestaurantSerializer, EventSerializer,
    ItinerarySerializer, ItineraryPointSerializer, ItineraryReviewSerializer,
    ItineraryCreateSerializer, ItineraryPointCreateSerializer
)
from django.utils import timezone
from django.db.models import Avg, Max
from django.http import JsonResponse

# Create your views here.

class PointOfInterestViewSet(viewsets.ModelViewSet):
    queryset = PointOfInterest.objects.all()
    serializer_class = PointOfInterestSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['type', 'difficulty']
    search_fields = ['name', 'description']
    ordering_fields = ['name', 'created_at']

    @action(detail=False, methods=['get'])
    def nearby(self, request):
        """
        Encuentra puntos de interés cercanos a una ubicación dada.
        Parámetros:
        - lat: latitud
        - lng: longitud
        - max_distance: distancia máxima en kilómetros (default: 10)
        - type: tipo de punto de interés (opcional)
        """
        try:
            lat = float(request.query_params.get('lat', 0))
            lng = float(request.query_params.get('lng', 0))
            max_distance = float(request.query_params.get('max_distance', 10))
            point_type = request.query_params.get('type')

            user_location = Point(lng, lat, srid=4326)
            
            queryset = self.get_queryset().annotate(
                distance=Distance('location', user_location)
            ).filter(location__distance_lte=(user_location, D(km=max_distance)))

            if point_type:
                queryset = queryset.filter(type=point_type)

            queryset = queryset.order_by('distance')
            
            serializer = self.get_serializer(queryset, many=True)
            return Response(serializer.data)
        
        except (ValueError, TypeError):
            return Response(
                {"error": "Parámetros de ubicación inválidos"},
                status=400
            )

    @action(detail=False, methods=['get'])
    def by_type(self, request):
        """
        Agrupa puntos de interés por tipo y devuelve estadísticas básicas.
        """
        types = PointOfInterest.objects.values('type').distinct()
        result = []
        
        for type_dict in types:
            type_name = type_dict['type']
            points = self.get_queryset().filter(type=type_name)
            
            result.append({
                'type': type_name,
                'count': points.count(),
                'avg_difficulty': points.aggregate(Avg('difficulty'))['difficulty__avg'],
                'points': self.get_serializer(points, many=True).data
            })
        
        return Response(result)

class RestaurantViewSet(viewsets.ModelViewSet):
    queryset = Restaurant.objects.all()
    serializer_class = RestaurantSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['cuisine_type', 'price_range']
    search_fields = ['name', 'description']
    ordering_fields = ['name', 'created_at']

    @action(detail=False, methods=['get'])
    def nearby(self, request):
        """
        Encuentra restaurantes cercanos a una ubicación dada.
        """
        try:
            lat = float(request.query_params.get('lat', 0))
            lng = float(request.query_params.get('lng', 0))
            max_distance = float(request.query_params.get('max_distance', 5))
            cuisine = request.query_params.get('cuisine_type')

            user_location = Point(lng, lat, srid=4326)
            
            queryset = self.get_queryset().annotate(
                distance=Distance('location', user_location)
            ).filter(location__distance_lte=(user_location, D(km=max_distance)))

            if cuisine:
                queryset = queryset.filter(cuisine_type=cuisine)

            queryset = queryset.order_by('distance')
            
            serializer = self.get_serializer(queryset, many=True)
            return Response(serializer.data)
        
        except (ValueError, TypeError):
            return Response(
                {"error": "Parámetros de ubicación inválidos"},
                status=400
            )

class EventViewSet(viewsets.ModelViewSet):
    queryset = Event.objects.all()
    serializer_class = EventSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['start_date', 'end_date']
    search_fields = ['name', 'description']
    ordering_fields = ['name', 'start_date', 'created_at']

    def get_queryset(self):
        queryset = super().get_queryset()
        start_date = self.request.query_params.get('start_date', None)
        end_date = self.request.query_params.get('end_date', None)

        if start_date:
            queryset = queryset.filter(start_date__gte=start_date)
        if end_date:
            queryset = queryset.filter(end_date__lte=end_date)

        return queryset

    @action(detail=False, methods=['get'])
    def upcoming(self, request):
        """
        Devuelve eventos próximos en un área específica.
        """
        try:
            lat = float(request.query_params.get('lat', 0))
            lng = float(request.query_params.get('lng', 0))
            max_distance = float(request.query_params.get('max_distance', 10))

            user_location = Point(lng, lat, srid=4326)
            
            queryset = self.get_queryset().annotate(
                distance=Distance('location', user_location)
            ).filter(
                location__distance_lte=(user_location, D(km=max_distance)),
                end_date__gte=timezone.now()
            ).order_by('start_date')
            
            serializer = self.get_serializer(queryset, many=True)
            return Response(serializer.data)
        
        except (ValueError, TypeError):
            return Response(
                {"error": "Parámetros de ubicación inválidos"},
                status=400
            )

class ItineraryViewSet(viewsets.ModelViewSet):
    queryset = Itinerary.objects.all()
    serializer_class = ItinerarySerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['start_date', 'end_date', 'is_completed']
    search_fields = ['title', 'description']
    ordering_fields = ['title', 'start_date', 'created_at']

    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return ItineraryCreateSerializer
        return ItinerarySerializer

    def perform_create(self, serializer):
        # Durante desarrollo, usar un usuario por defecto o None
        serializer.save(user=None)

    @action(detail=True, methods=['post'])
    def add_point(self, request, pk=None):
        """
        Añade un punto al itinerario.
        Parámetros en el body:
        - point_type: 'poi', 'restaurant' o 'event'
        - point_id: ID del punto a añadir
        - day: número del día
        - order: orden dentro del día (opcional)
        - notes: notas adicionales (opcional)
        """
        itinerary = self.get_object()
        
        point_type = request.data.get('point_type')
        point_id = request.data.get('point_id')
        day = request.data.get('day')
        order = request.data.get('order')
        notes = request.data.get('notes', '')

        if not all([point_type, point_id, day]):
            return Response(
                {"error": "Se requieren point_type, point_id y day"},
                status=400
            )

        # Si no se especifica order, añadir al final del día
        if not order:
            max_order = ItineraryPoint.objects.filter(
                itinerary=itinerary,
                day=day
            ).aggregate(Max('order'))['order__max'] or 0
            order = max_order + 1

        # Crear el punto según el tipo
        point_data = {
            'itinerary': itinerary,
            'day': day,
            'order': order,
            'notes': notes
        }

        if point_type == 'poi':
            point_data['point_of_interest_id'] = point_id
        elif point_type == 'restaurant':
            point_data['restaurant_id'] = point_id
        elif point_type == 'event':
            point_data['event_id'] = point_id
        else:
            return Response(
                {"error": "point_type debe ser 'poi', 'restaurant' o 'event'"},
                status=400
            )

        try:
            point = ItineraryPoint.objects.create(**point_data)
            serializer = ItineraryPointSerializer(point)
            return Response(serializer.data, status=201)
        except Exception as e:
            return Response({"error": str(e)}, status=400)

    @action(detail=True, methods=['post'])
    def reorder_points(self, request, pk=None):
        """
        Reordena los puntos de un día específico.
        Parámetros en el body:
        - day: número del día
        - points: lista de IDs de puntos en el nuevo orden
        """
        itinerary = self.get_object()
        day = request.data.get('day')
        point_ids = request.data.get('points', [])

        if not day or not point_ids:
            return Response(
                {"error": "Se requieren day y points"},
                status=400
            )

        try:
            # Verificar que todos los puntos pertenecen al itinerario y día
            points = ItineraryPoint.objects.filter(
                itinerary=itinerary,
                day=day,
                id__in=point_ids
            )

            if points.count() != len(point_ids):
                return Response(
                    {"error": "Algunos puntos no existen o no pertenecen a este día"},
                    status=400
                )

            # Actualizar el orden
            for new_order, point_id in enumerate(point_ids, 1):
                ItineraryPoint.objects.filter(id=point_id).update(order=new_order)

            # Devolver los puntos actualizados
            points = ItineraryPoint.objects.filter(
                itinerary=itinerary,
                day=day
            ).order_by('order')
            serializer = ItineraryPointSerializer(points, many=True)
            return Response(serializer.data)

        except Exception as e:
            return Response({"error": str(e)}, status=400)

    @action(detail=True, methods=['post'])
    def move_point(self, request, pk=None):
        """
        Mueve un punto a otro día y/o posición.
        Parámetros en el body:
        - point_id: ID del punto a mover
        - new_day: nuevo número de día
        - new_order: nueva posición en el día (opcional)
        """
        itinerary = self.get_object()
        point_id = request.data.get('point_id')
        new_day = request.data.get('new_day')
        new_order = request.data.get('new_order')

        if not all([point_id, new_day]):
            return Response(
                {"error": "Se requieren point_id y new_day"},
                status=400
            )

        try:
            point = ItineraryPoint.objects.get(
                itinerary=itinerary,
                id=point_id
            )

            # Si no se especifica new_order, añadir al final del nuevo día
            if not new_order:
                max_order = ItineraryPoint.objects.filter(
                    itinerary=itinerary,
                    day=new_day
                ).aggregate(Max('order'))['order__max'] or 0
                new_order = max_order + 1

            point.day = new_day
            point.order = new_order
            point.save()

            serializer = ItineraryPointSerializer(point)
            return Response(serializer.data)

        except ItineraryPoint.DoesNotExist:
            return Response(
                {"error": "Punto no encontrado"},
                status=404
            )
        except Exception as e:
            return Response({"error": str(e)}, status=400)

@api_view(['GET'])
def health_check(request):
    return JsonResponse({"status": "ok"})
