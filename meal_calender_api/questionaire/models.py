from django.db import models
from users.models import User


class UserProfile(models.Model):

    GOAL_CHOICES = [
        ("lose_weight",  "Lose Weight"),
        ("gain_muscle",  "Gain Muscle"),
        ("eat_healthy",  "Eat Healthy"),
        ("maintain",     "Maintain Weight"),
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

    CUISINE_PREFERENCES = [
        ("italian",       "Italian"),
        ("mexican",       "Mexican"),
        ("chinese",       "Chinese"),
        ("indian",        "Indian"),
        ("american",      "American"),
        ("mediterranean", "Mediterranean"),
        ("thai",          "Thai"),
        ("japanese",      "Japanese"),
        ("french",        "French"),
        ("other",         "Other"),
        ("none",          "No Preference"),
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
    diet_type = models.CharField(max_length=20, choices=DIET_CHOICES,    default="none")
    allergies = models.JSONField(default=list)
    # Stores: ["nuts", "dairy", "shellfish"]

    # ── Calories & Meals ───────────────────────────────────────────────────────
    calories_per_day = models.IntegerField(default=2000)
    meals_per_day    = models.IntegerField(default=3)

    # ── Meal Slots — which meals the user wants ────────────────────────────────
    meal_slots = models.JSONField(default=list)
    # Stores: ["breakfast", "lunch", "dinner"] or ["breakfast", "dinner"] etc.
    # Validated against MEAL_SLOT_CHOICES in the serializer

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

    # ── Meta ───────────────────────────────────────────────────────────────────
    completed  = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name        = "User Profile"
        verbose_name_plural = "User Profiles"

    def __str__(self):
        return f"{self.user.username} — {self.get_goal_display()}"

    # ── Helpers ────────────────────────────────────────────────────────────────
    def get_calories_per_meal(self) -> int:
        """Returns the target calories per individual meal."""
        if not self.meals_per_day:
            return self.calories_per_day
        return self.calories_per_day // self.meals_per_day

    def get_unique_recipes_for_meal(self, meal_type: str) -> int:
        """Returns how many unique recipes are wanted for a given meal type."""
        return self.unique_recipes_per_meal.get(meal_type, 1)

    def get_active_meal_slots(self) -> list[str]:
        """Returns the list of active meal slots in order."""
        order = ["breakfast", "lunch", "dinner", "snack"]
        return [slot for slot in order if slot in self.meal_slots]