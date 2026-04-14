from django.contrib import admin
from .models import Meal, ScheduledMeal


@admin.register(Meal)
class MealAdmin(admin.ModelAdmin):
    list_display = ['name', 'calories', 'created_at']
    search_fields = ['name', 'description']


@admin.register(ScheduledMeal)
class ScheduledMealAdmin(admin.ModelAdmin):
    list_display = ['meal', 'date', 'meal_type']
    list_filter = ['date', 'meal_type']
    search_fields = ['meal__name']
