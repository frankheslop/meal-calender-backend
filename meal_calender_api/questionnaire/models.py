from django.db import models
from users.models import User
from django.core.validators import MaxValueValidator, MinValueValidator


class UserProfile(models.Model):

    GOAL_CHOICES = [
        ("lose_weight",  "Lose Weight"),
        ("gain_muscle",  "Gain Muscle"),
        ("eat_healthy",  "Eat Healthy"),
        ("maintain",     "Maintain Weight"),
    ]
    MEASURING_STANDARD_CHOICES = [
        ("imperial", "Imperial (lbs, oz)"),
        ("metric",   "Metric (kg, g)"),
    ]

    DIET_CHOICES = [
        ("none",          "No Restriction"),
        ("vegetarian",    "Vegetarian"),
        ("vegan",         "Vegan"),
        ("keto",          "Keto"),
        ("paleo",         "Paleo"),
        ("gluten_free",   "Gluten Free"),
        ("dairy_free",    "Dairy Free"),
        ("low_carb",      "Low Carb"),
        ("high_protein",  "High Protein"),
        ("mediterranean", "Mediterranean"),
        ("other",         "Other"),
        ("halal",         "Halal"),
        ("kosher",        "Kosher"),
    ]

    COOKING_TIME_CHOICES = [
        ("15",  "15 minutes or less"),
        ("30",  "30 minutes or less"),
        ("60",  "1 hour or less"),
        ("120", "More than 1 hour"),
    ]

    COOKING_SKILL_CHOICES = [
        ("beginner",     "Beginner"),
        ("intermediate", "Intermediate"),
        ("advanced",     "Advanced"),
    ]

    MEAL_SLOT_CHOICES = [
        ("breakfast", "Breakfast"),
        ("lunch",     "Lunch"),
        ("dinner",    "Dinner"),
        ("snack",     "Snack"),
    ]

    # ── Relationships ──────────────────────────────────────────────────────────
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")

    # ── Health & Diet ──────────────────────────────────────────────────────────
    goal      = models.CharField(max_length=20, choices=GOAL_CHOICES,    default="eat_healthy")
    meal_plan_type = models.CharField(max_length=20, choices=DIET_CHOICES,    default="none")
    food_avoidances = models.JSONField(default=list)
    # Stores: ["nuts", "dairy", "shellfish"], it includes both allergies and personal dislikes.

    # ── Calories & Meals ───────────────────────────────────────────────────────
    calories_per_day = models.IntegerField(default=2000)

    # ── Meal Slots — which meals the user wants ────────────────────────────────
    meal_slots = models.JSONField(default=list)
    # Stores: ["breakfast", "lunch", "dinner"] or ["breakfast", "dinner"] etc.
    # Validated against MEAL_SLOT_CHOICES in the serializer
    meal_plan_repetition = models.IntegerField(default=1, validators=[MinValueValidator(1), MaxValueValidator(4)])

    # ── Unique Recipes Per Meal — how many different recipes per meal type ──────
    unique_recipes_per_meal = models.JSONField(default=dict)
    # Stores: {"breakfast": 1, "lunch": 2, "dinner": 3}
    # Keys must match entries in meal_slots
    # Value of 1 = same meal every day, 3 = three rotating recipes across the week

    # ── Cooking Preferences ────────────────────────────────────────────────────
    cooking_time  = models.CharField(max_length=3,  choices=COOKING_TIME_CHOICES,  default="30")
    cooking_skill = models.CharField(max_length=20, choices=COOKING_SKILL_CHOICES, default="intermediate")
    household_size = models.IntegerField(default=2)

    # ── Cuisine — only applied to lunch and dinner in prompt logic ─────────────
    cuisine_preferences = models.JSONField(default=list)
    # Stores: ["italian", "japanese"]
    # MultipleChoiceField is not a native Django field — JSONField is the
    # correct approach. Validated against CUISINE_PREFERENCES in the serializer.
    measuring_standard = models.CharField(max_length=10, choices=MEASURING_STANDARD_CHOICES, default="metric")

    # ── Meta ───────────────────────────────────────────────────────────────────
    completed  = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
