from django.db import models
from users.models import User           # ← imports from users app
# questionnaire/models.py
class UserProfile(models.Model):
    GOAL_CHOICES = [
        ("lose_weight",   "Lose Weight"),
        ("gain_muscle",   "Gain Muscle"),
        ("eat_healthy",   "Eat Healthy"),
        ("maintain",      "Maintain Weight"),
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
        ("mediterranean",  "Mediterranean"),
        ("other",         "Other"),
        ('halal',         "Halal"),
        ('kosher',        "Kosher"),
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
    ]
    COOKING_TIME = (
        ("15", "15 minutes or less"),
        ("30", "30 minutes or less"),
        ("60", "1 hour or less"),
        ("120", "More than 1 hour")
    )
    COOKING_SKILL = (
        ("beginner", "Beginner"),
        ("intermediate", "Intermediate"),
        ("advanced", "Advanced")
    )
    

    user             = models.OneToOneField(User, on_delete=models.CASCADE)
    goal             = models.CharField(max_length=20, choices=GOAL_CHOICES)
    diet_type        = models.CharField(max_length=20, choices=DIET_CHOICES)
    allergies        = models.JSONField(default=list)   # ["nuts", "dairy"]
    calories_per_day = models.IntegerField(default=2000)
    meals_per_day    = models.IntegerField(default=3)
    cooking_time     = models.CharField(max_length=20, choices=COOKING_TIME, default="30")  # max minutes per meal
    household_size   = models.IntegerField(default=2)
    completed        = models.BooleanField(default=False)
    cuisine_preferences = models.CharField(max_length=20, choices=CUISINE_PREFERENCES)
    cooking_skill    = models.CharField(max_length=20, choices=COOKING_SKILL, default="intermediate")