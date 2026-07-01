from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import RecipeGenerationJob, WeeklyRecipeGeneration
from .serializers import RecipeGenerationJobStatusSerializer, WeeklyRecipeGenerationSerializer
from .services import maybe_queue_recipe_top_up


class RecipeGenerationJobStatusView(APIView):
    """GET /api/recipes/generation-jobs/<job_id>/ — fetch generation status and weekly results."""

    permission_classes = [IsAuthenticated]

    def get(self, request, job_id: int):
        try:
            job = RecipeGenerationJob.objects.get(id=job_id, user=request.user)
        except RecipeGenerationJob.DoesNotExist:
            return Response({"detail": "Generation job not found"}, status=status.HTTP_404_NOT_FOUND)

        serializer = RecipeGenerationJobStatusSerializer(job)
        return Response(serializer.data, status=status.HTTP_200_OK)


class UserWeeklyRecipeGenerationsView(APIView):
    """GET /api/recipes/weekly-generations/ — list all weekly generations for the authenticated user."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        top_up = maybe_queue_recipe_top_up(request.user)
        weekly_generations = WeeklyRecipeGeneration.objects.filter(user=request.user)
        serializer = WeeklyRecipeGenerationSerializer(weekly_generations, many=True)
        return Response(
            {
                "top_up": top_up,
                "weekly_generations": serializer.data,
            },
            status=status.HTTP_200_OK,
        )