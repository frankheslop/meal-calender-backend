from django.db import models
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
    ]

    user             = models.OneToOneField(User, on_delete=models.CASCADE)
    goal             = models.CharField(max_length=20, choices=GOAL_CHOICES)
    diet_type        = models.CharField(max_length=20, choices=DIET_CHOICES)
    allergies        = models.JSONField(default=list)   # ["nuts", "dairy"]
    calories_per_day = models.IntegerField(default=2000)
    meals_per_day    = models.IntegerField(default=3)
    cooking_time     = models.IntegerField(default=30)  # max minutes per meal
    servings         = models.IntegerField(default=2)
    completed        = models.BooleanField(default=False)
