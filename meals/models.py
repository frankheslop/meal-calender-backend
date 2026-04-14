from django.db import models


class Meal(models.Model):
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, default='')
    calories = models.PositiveIntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name


class ScheduledMeal(models.Model):
    meal = models.ForeignKey(Meal, on_delete=models.CASCADE, related_name='scheduled_meals')
    date = models.DateField()
    meal_type = models.CharField(
        max_length=20,
        choices=[
            ('breakfast', 'Breakfast'),
            ('lunch', 'Lunch'),
            ('dinner', 'Dinner'),
            ('snack', 'Snack'),
        ],
    )
    notes = models.TextField(blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['date', 'meal_type']

    def __str__(self):
        return f'{self.meal.name} on {self.date} ({self.meal_type})'
