from rest_framework import serializers

from .models import RecipeGenerationJob, WeeklyRecipeGeneration


class WeeklyRecipeGenerationSerializer(serializers.ModelSerializer):
    class Meta:
        model = WeeklyRecipeGeneration
        fields = ("id", "week_start_date", "week_end_date", "meals_output", "created_at")


class RecipeGenerationJobStatusSerializer(serializers.ModelSerializer):
    weeks = WeeklyRecipeGenerationSerializer(source="weekly_generations", many=True, read_only=True)

    class Meta:
        model = RecipeGenerationJob
        fields = (
            "id",
            "status",
            "error_message",
            "created_at",
            "started_at",
            "completed_at",
            "weeks",
        )
