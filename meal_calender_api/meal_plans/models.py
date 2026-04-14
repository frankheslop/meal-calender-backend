from django.db import models
from recipes.models import Recipe       # ← imports from recipes app
from users.models import User           # ← imports from users app

class MealPlan(models.Model):
    user       = models.ForeignKey(User, on_delete=models.CASCADE)
    week_start = models.DateField()     # always a Monday
    created_at = models.DateTimeField(auto_now_add=True)

class MealPlanEntry(models.Model):
    MEAL_CHOICES = [
        ("breakfast", "Breakfast"),
        ("lunch",     "Lunch"),
        ("dinner",    "Dinner"),
        ("snack",     "Snack"),
    ]
    DAY_CHOICES = [(i, day) for i, day in enumerate(
        ["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday"]
    )]

    meal_plan  = models.ForeignKey(MealPlan, related_name="entries", on_delete=models.CASCADE)
    recipe     = models.ForeignKey(Recipe, on_delete=models.CASCADE)
    day        = models.IntegerField(choices=DAY_CHOICES)   # 0=Monday, 6=Sunday
    meal_type  = models.CharField(max_length=20, choices=MEAL_CHOICES)
