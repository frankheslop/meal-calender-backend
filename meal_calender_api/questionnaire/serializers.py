from rest_framework import serializers
from .models import UserProfile
class QuestionnaireSerializer(serializers.ModelSerializer):
    # Define fields based on the questionnaire model
    class Meta:
        model = UserProfile
        fields = (
            'goal',
            'diet_type',
            'allergies',
            'calories_per_day',
            'meal_slots',
            'unique_recipes_per_meal',
            'cooking_time',
            'cooking_skill',
            'household_size',
            'cuisine_preferences',
            'measuring_standard',
            'completed',
        )     