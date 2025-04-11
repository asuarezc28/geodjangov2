from django.shortcuts import render
from rest_framework import viewsets, filters
from rest_framework.decorators import action, api_view
from rest_framework.response import Response
from django.contrib.gis.geos import Point
from django.contrib.gis.db.models.functions import Distance
from django.contrib.gis.measure import D
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
import os
from django.conf import settings
from openai import OpenAI
import json
import re

# Create your views here.

def health_check(request):
    return JsonResponse({"status": "ok"})

@api_view(['GET', 'POST'])
def generate_itinerary(request):
    if request.method == 'GET':
        return Response({
            "message": "Este endpoint espera una petición POST con un JSON que contenga el campo 'query'",
            "example": {
                "query": "Quiero un itinerario de 2 días en La Palma visitando el Roque de los Muchachos"
            }
        })
    
    # 1. Recibir la consulta del usuario
    user_query = request.data.get('query')
    if not user_query:
        return Response(
            {"error": "El campo 'query' es requerido"},
            status=400
        )
    
    try:
        # 2. Obtener todos los puntos de interés
        points_of_interest = PointOfInterest.objects.all()
        pois_data = []
        
        for poi in points_of_interest:
            pois_data.append({
                'id': poi.id,
                'name': poi.name,
                'description': poi.description,
                'type': poi.type,
                'difficulty': poi.difficulty
            })
        
        # 3. Construir el contexto para GPT
        context = "\n".join([
            f"- {poi['name']} (ID: {poi['id']}): {poi['description']} - Tipo: {poi['type']}, Dificultad: {poi['difficulty']}"
            for poi in pois_data
        ])
        
        # 4. Preparar el prompt para GPT
        prompt = f"""
        Como experto en turismo de La Palma, genera un itinerario basado en esta solicitud: {user_query}
        
        Usa SOLO los siguientes puntos de interés disponibles:
        {context}
        
        IMPORTANTE: Debes devolver EXACTAMENTE este formato JSON, sin texto adicional antes o después:
        {{
            "display": "Texto formateado para mostrar al usuario. Debe incluir:
            - Un título atractivo con emojis relevantes
            - Una breve introducción sobre el itinerario
            - Para cada día:
              * Un subtítulo con el número de día y emojis
              * Una descripción de las actividades del día
              * Los puntos de interés a visitar con sus horarios recomendados
              * Consejos prácticos (qué llevar, mejor hora para visitar, etc.)
            - Una conclusión con recomendaciones finales
            Usa emojis estratégicamente para hacer el texto más atractivo y fácil de leer.",
            "data": {{
                "titulo": "Título del itinerario (OBLIGATORIO)",
                "description": "Descripción general del itinerario (OBLIGATORIO)",
                "start_date": "2024-03-15",  // Fecha de inicio en formato YYYY-MM-DD (OBLIGATORIO, debe ser una fecha real)
                "end_date": "2024-03-16",    // Fecha de fin en formato YYYY-MM-DD (OBLIGATORIO, debe ser una fecha real)
                "dias": [
                    {{
                        "numero": 1,  // Número del día (OBLIGATORIO)
                        "titulo": "Título del día (OBLIGATORIO)",
                        "puntos": [
                            {{
                                "poi_id": 1,  // ID del punto de interés (OBLIGATORIO)
                                "orden": 1,    // Orden del punto en el día (OBLIGATORIO)
                                "notas": "Notas específicas para este punto (OBLIGATORIO)"
                            }}
                        ]
                    }}
                ]
            }}
        }}
        
        REGLAS ESTRICTAS:
        1. Todos los campos marcados como OBLIGATORIO deben estar presentes
        2. El formato debe ser EXACTAMENTE como se muestra arriba
        3. No añadas texto antes o después del JSON
        4. Usa SOLO los puntos de interés listados arriba
        5. Los poi_id deben ser IDs válidos de la lista proporcionada
        6. El display debe ser detallado, informativo y atractivo visualmente
        7. Usa emojis relevantes para cada sección y punto de interés
        8. Incluye horarios recomendados y consejos prácticos
        9. Las fechas DEBEN ser reales y válidas en formato YYYY-MM-DD
        10. Usa fechas futuras (2024 o 2025) para los itinerarios
        11. La diferencia entre start_date y end_date debe coincidir con el número de días del itinerario
        """
        
        # 5. Llamar a GPT
        client = OpenAI(api_key=settings.OPENAI_API_KEY)
        response = client.chat.completions.create(
            model="gpt-4-1106-preview",  # Modelo más reciente que maneja mejor JSON
            messages=[
                {"role": "system", "content": "Eres un asistente especializado en crear itinerarios turísticos para La Palma. Debes responder SOLO con un JSON válido, sin texto adicional."},
                {"role": "user", "content": prompt}
            ],
            response_format={ "type": "json_object" }  # Forzar formato JSON
        )
        
        # 6. Procesar respuesta de GPT
        try:
            # Obtener la respuesta de GPT
            content = response.choices[0].message.content.strip()
            
            # Extraer la información relevante usando expresiones regulares
            
            # Extraer el display
            display_match = re.search(r'"display":\s*"([^"]*)"', content)
            if not display_match:
                raise ValueError("No se encontró el campo 'display' en la respuesta")
            display = display_match.group(1)
            
            # Extraer el título
            titulo_match = re.search(r'"titulo":\s*"([^"]*)"', content)
            if not titulo_match:
                raise ValueError("No se encontró el campo 'titulo' en la respuesta")
            titulo = titulo_match.group(1)
            
            # Extraer la descripción
            description_match = re.search(r'"description":\s*"([^"]*)"', content)
            if not description_match:
                raise ValueError("No se encontró el campo 'description' en la respuesta")
            description = description_match.group(1)
            
            # Extraer las fechas
            start_date_match = re.search(r'"start_date":\s*"([^"]*)"', content)
            if not start_date_match:
                raise ValueError("No se encontró el campo 'start_date' en la respuesta")
            start_date = start_date_match.group(1)
            
            end_date_match = re.search(r'"end_date":\s*"([^"]*)"', content)
            if not end_date_match:
                raise ValueError("No se encontró el campo 'end_date' en la respuesta")
            end_date = end_date_match.group(1)
            
            # Extraer los días
            dias_match = re.search(r'"dias":\s*(\[.*?\])', content, re.DOTALL)
            if not dias_match:
                raise ValueError("No se encontró el campo 'dias' en la respuesta")
            dias_str = dias_match.group(1)
            
            try:
                # Intentar parsear los días como JSON
                dias = json.loads(dias_str)
            except json.JSONDecodeError:
                # Si falla, intentar limpiar el string
                dias_str = dias_str.replace('\n', '').replace('\r', '').replace('\t', '')
                dias = json.loads(dias_str)
            
            # Construir el JSON manualmente
            gpt_response = {
                "display": display,
                "data": {
                    "titulo": titulo,
                    "description": description,
                    "start_date": start_date,
                    "end_date": end_date,
                    "dias": dias
                }
            }
            
        except Exception as e:
            return Response(
                {"error": f"Error procesando la respuesta de GPT: {str(e)}"},
                status=500
            )
        
        # 7. Crear itinerario en DB
        itinerary_data = gpt_response['data']
        itinerary = Itinerary.objects.create(
            title=itinerary_data['titulo'],
            description=itinerary_data.get('description', ''),
            start_date=itinerary_data.get('start_date'),
            end_date=itinerary_data.get('end_date')
        )
        
        # 8. Crear puntos del itinerario
        for dia in itinerary_data['dias']:
            for punto in dia['puntos']:
                ItineraryPoint.objects.create(
                    itinerary=itinerary,
                    point_of_interest_id=punto['poi_id'],
                    day=dia['numero'],
                    order=punto['orden'],
                    notes=punto['notas']
                )
        
        # 9. Devolver respuesta estructurada
        return Response({
            'display': gpt_response['display'],
            'itinerary_id': itinerary.id,
            'points': itinerary.get_points_geojson()
        })
        
    except Exception as e:
        return Response(
            {"error": str(e)},
            status=500
        )

class PointOfInterestViewSet(viewsets.ModelViewSet):
    queryset = PointOfInterest.objects.all()
    serializer_class = PointOfInterestSerializer
    filter_backends = [SearchFilter, OrderingFilter]
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
    filter_backends = [SearchFilter, OrderingFilter]
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
    filter_backends = [SearchFilter, OrderingFilter]
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
    filter_backends = [SearchFilter, OrderingFilter]
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

class ItineraryPointViewSet(viewsets.ModelViewSet):
    queryset = ItineraryPoint.objects.all()
    serializer_class = ItineraryPointSerializer
    filter_backends = [SearchFilter, OrderingFilter]
    ordering_fields = ['day', 'order']

    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return ItineraryPointCreateSerializer
        return self.serializer_class

class ItineraryReviewViewSet(viewsets.ModelViewSet):
    queryset = ItineraryReview.objects.all()
    serializer_class = ItineraryReviewSerializer
    filter_backends = [SearchFilter, OrderingFilter]
    search_fields = ['comment']
    ordering_fields = ['rating', 'created_at']

    def perform_create(self, serializer):
        serializer.save(user=None)  # Por ahora, sin usuario
