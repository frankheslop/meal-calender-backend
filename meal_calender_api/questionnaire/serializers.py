from rest_framework import serializers

from .models import UserProfile


class QuestionnaireSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserProfile
        fields = (
            "goal",
            "meal_plan_type",
            "food_avoidances",
            "calories_per_day",
            "meal_slots",
            "meal_plan_repetition",
            "unique_recipes_per_meal",
            "cooking_time",
            "cooking_skill",
            "household_size",
            "cuisine_preferences",
            "measuring_standard",
            "completed",
        )
        read_only_fields = ("completed",)

    def validate(self, data):
        # On updates, merge incoming data with existing instance values so partial
        # updates don't incorrectly fail the completion check.
        instance = self.instance

        def get(field):
            return data.get(field, getattr(instance, field, None) if instance else None)

        meal_slots = get("meal_slots") or []
        unique_recipes = get("unique_recipes_per_meal") or {}

        if not meal_slots:
            raise serializers.ValidationError({"meal_slots": "At least one meal slot is required."})

        invalid_slots = [s for s in meal_slots if s not in dict(UserProfile.MEAL_SLOT_CHOICES)]
        if invalid_slots:
            raise serializers.ValidationError(
                {"meal_slots": f"Invalid meal slot(s): {invalid_slots}."}
            )

        missing_slots = [s for s in meal_slots if s not in unique_recipes]
        if missing_slots:
            raise serializers.ValidationError(
                {"unique_recipes_per_meal": f"Missing recipe count for slot(s): {missing_slots}."}
            )

        invalid_counts = [s for s, v in unique_recipes.items() if not isinstance(v, int) or v < 1]
        if invalid_counts:
            raise serializers.ValidationError(
                {
                    "unique_recipes_per_meal": f"Recipe count must be a positive integer for: {invalid_counts}."
                }
            )

        return data
