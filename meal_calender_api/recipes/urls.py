from django.urls import path

from .views import RecipeGenerationJobStatusView, UserWeeklyRecipeGenerationsView

app_name = "recipes"

urlpatterns = [
    path(
        "generation-jobs/<int:job_id>/",
        RecipeGenerationJobStatusView.as_view(),
        name="generation-job-status",
    ),
    path(
        "weekly-generations/",
        UserWeeklyRecipeGenerationsView.as_view(),
        name="user-weekly-generations",
    ),
]
