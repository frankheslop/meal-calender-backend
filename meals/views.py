from rest_framework import viewsets
from .models import Meal, ScheduledMeal
from .serializers import MealSerializer, ScheduledMealSerializer


class MealViewSet(viewsets.ModelViewSet):
    queryset = Meal.objects.all().order_by('name')
    serializer_class = MealSerializer


class ScheduledMealViewSet(viewsets.ModelViewSet):
    queryset = ScheduledMeal.objects.all().select_related('meal')
    serializer_class = ScheduledMealSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        date = self.request.query_params.get('date')
        if date:
            queryset = queryset.filter(date=date)
        return queryset
