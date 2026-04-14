from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import MealViewSet, ScheduledMealViewSet

router = DefaultRouter()
router.register(r'meals', MealViewSet, basename='meal')
router.register(r'scheduled-meals', ScheduledMealViewSet, basename='scheduled-meal')

urlpatterns = [
    path('', include(router.urls)),
]
