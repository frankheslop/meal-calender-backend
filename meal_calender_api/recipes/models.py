from django.conf import settings
from django.db import models


class RecipeGenerationJob(models.Model):
    """Tracks asynchronous recipe generation requested from questionnaire submission."""

    class Status(models.TextChoices):
        QUEUED = "queued", "Queued"
        RUNNING = "running", "Running"
        SUCCEEDED = "succeeded", "Succeeded"
        FAILED = "failed", "Failed"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="recipe_generation_jobs",
    )
    requested_input = models.JSONField(default=dict)
    start_from_date = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.QUEUED)
    celery_task_id = models.CharField(max_length=255, blank=True)
    error_message = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"RecipeGenerationJob(id={self.id}, user_id={self.user_id}, status={self.status})"


class WeeklyRecipeGeneration(models.Model):
    """Stores one generated week and its meal recipes."""

    job = models.ForeignKey(
        RecipeGenerationJob,
        on_delete=models.CASCADE,
        related_name="weekly_generations",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="weekly_recipe_generations",
    )
    week_start_date = models.DateField()
    week_end_date = models.DateField()
    meals_output = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-week_start_date", "-created_at"]
        indexes = [
            models.Index(fields=["job", "week_start_date"]),
            models.Index(fields=["user", "week_start_date"]),
        ]

    def __str__(self) -> str:
        return (
            f"WeeklyRecipeGeneration(user_id={self.user_id}, "
            f"week={self.week_start_date} to {self.week_end_date})"
        )
