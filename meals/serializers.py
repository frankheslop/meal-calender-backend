from rest_framework import serializers
from .models import Meal, ScheduledMeal


class MealSerializer(serializers.ModelSerializer):
    class Meta:
        model = Meal
        fields = ['id', 'name', 'description', 'calories', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']


class ScheduledMealSerializer(serializers.ModelSerializer):
    meal_name = serializers.CharField(source='meal.name', read_only=True)

    class Meta:
        model = ScheduledMeal
        fields = ['id', 'meal', 'meal_name', 'date', 'meal_type', 'notes', 'created_at', 'updated_at']
        read_only_fields = ['id', 'meal_name', 'created_at', 'updated_at']
