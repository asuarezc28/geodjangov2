from django.contrib.gis.db import models
from django.contrib.auth.models import User

class BaseLocation(models.Model):
    name = models.CharField(max_length=200)
    description = models.TextField()
    location = models.PointField()
    address = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True

class PointOfInterest(models.Model):
    name = models.CharField(max_length=200)
    description = models.TextField()
    location = models.PointField(null=True, blank=True)  # Hacemos el campo opcional temporalmente
    address = models.CharField(max_length=200)
    type = models.CharField(max_length=50, choices=[
        ('MONUMENT', 'Monumento'),
        ('MUSEUM', 'Museo'),
        ('PARK', 'Parque'),
        ('BEACH', 'Playa'),
        ('VIEWPOINT', 'Mirador'),
        ('OTHER', 'Otro')
    ])
    difficulty = models.CharField(max_length=20, choices=[
        ('EASY', 'Fácil'),
        ('MEDIUM', 'Medio'),
        ('HARD', 'Difícil')
    ])
    estimated_time = models.DurationField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

class Restaurant(BaseLocation):
    CUISINE_CHOICES = [
        ('LOCAL', 'Local'),
        ('SPANISH', 'Spanish'),
        ('INTERNATIONAL', 'International'),
    ]
    
    cuisine_type = models.CharField(max_length=20, choices=CUISINE_CHOICES)
    price_range = models.IntegerField(choices=[(1, '€'), (2, '€€'), (3, '€€€')], default=1)
    opening_hours = models.JSONField(help_text="Opening hours for each day of the week")
    
    def __str__(self):
        return f"{self.name} ({self.get_cuisine_type_display()})"

class Event(BaseLocation):
    start_date = models.DateTimeField()
    end_date = models.DateTimeField()
    price = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    url = models.URLField(blank=True)
    
    def __str__(self):
        return f"{self.name} ({self.start_date.date()})"

class Itinerary(models.Model):
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    start_date = models.DateField()
    end_date = models.DateField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_completed = models.BooleanField(default=False)
    
    def __str__(self):
        return f"{self.title} ({self.start_date} - {self.end_date})"

    def get_points_geojson(self):
        points = []
        for point in self.points.all():
            if point.point_of_interest:
                points.append({
                    'type': 'Feature',
                    'geometry': {
                        'type': 'Point',
                        'coordinates': [
                            point.point_of_interest.location.x,
                            point.point_of_interest.location.y
                        ]
                    },
                    'properties': {
                        'name': point.point_of_interest.name,
                        'description': point.point_of_interest.description,
                        'type': 'poi',
                        'day': point.day,
                        'order': point.order,
                        'notes': point.notes
                    }
                })
        return {
            'type': 'FeatureCollection',
            'features': points
        }

class ItineraryPoint(models.Model):
    itinerary = models.ForeignKey(Itinerary, related_name='points', on_delete=models.CASCADE)
    point_of_interest = models.ForeignKey(PointOfInterest, null=True, blank=True, on_delete=models.SET_NULL)
    restaurant = models.ForeignKey(Restaurant, null=True, blank=True, on_delete=models.SET_NULL)
    event = models.ForeignKey(Event, null=True, blank=True, on_delete=models.SET_NULL)
    day = models.IntegerField(help_text="Day number in the itinerary")
    order = models.IntegerField(help_text="Order of the point within the day")
    notes = models.TextField(blank=True)
    is_visited = models.BooleanField(default=False)
    visited_at = models.DateTimeField(null=True, blank=True)
    actual_time_spent = models.DurationField(null=True, blank=True, help_text="Tiempo real que se pasó en el lugar")
    
    class Meta:
        ordering = ['day', 'order']
    
    def __str__(self):
        point = self.point_of_interest or self.restaurant or self.event
        return f"Day {self.day}: {point.name if point else 'Deleted point'}"

class ItineraryReview(models.Model):
    RATING_CHOICES = [
        (1, '1 Estrella'),
        (2, '2 Estrellas'),
        (3, '3 Estrellas'),
        (4, '4 Estrellas'),
        (5, '5 Estrellas'),
    ]
    
    itinerary = models.ForeignKey(Itinerary, related_name='reviews', on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    rating = models.IntegerField(choices=RATING_CHOICES)
    comment = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Campos para valoraciones específicas
    scenery_rating = models.IntegerField(choices=RATING_CHOICES, null=True, blank=True, verbose_name="Valoración del paisaje")
    accessibility_rating = models.IntegerField(choices=RATING_CHOICES, null=True, blank=True, verbose_name="Valoración de la accesibilidad")
    signposting_rating = models.IntegerField(choices=RATING_CHOICES, null=True, blank=True, verbose_name="Valoración de la señalización")
    cleanliness_rating = models.IntegerField(choices=RATING_CHOICES, null=True, blank=True, verbose_name="Valoración de la limpieza")
    services_rating = models.IntegerField(choices=RATING_CHOICES, null=True, blank=True, verbose_name="Valoración de los servicios")
    
    class Meta:
        unique_together = ['itinerary', 'user']
    
    def __str__(self):
        return f"Review de {self.user.username} para {self.itinerary.title} ({self.rating} estrellas)"

class ReviewPhoto(models.Model):
    review = models.ForeignKey(ItineraryReview, related_name='photos', on_delete=models.CASCADE)
    photo = models.ImageField(upload_to='review_photos/')
    uploaded_at = models.DateTimeField(auto_now_add=True)
    caption = models.CharField(max_length=255, blank=True)
    
    def __str__(self):
        return f"Foto de {self.review.user.username} para {self.review.itinerary.title}"
