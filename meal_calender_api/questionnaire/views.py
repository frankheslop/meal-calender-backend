from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import UserProfile as Questionnaire
from .serializers import QuestionnaireSerializer


class QuestionnaireDetailView(APIView):
    """GET /api/questionnaire/answers/ — fetch the logged-in user's saved answers."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            questionnaire = Questionnaire.objects.get(user=request.user)
            serializer = QuestionnaireSerializer(questionnaire)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Questionnaire.DoesNotExist:
            return Response({"detail": "Questionnaire not found"}, status=status.HTTP_404_NOT_FOUND)


class QuestionnaireSubmitView(APIView):
    """
    POST /api/questionnaire/submit/ — submit answers for the first time.
    PUT  /api/questionnaire/submit/ — update existing answers.
    """

    permission_classes = [IsAuthenticated]

    def _queue_recipe_generation(self, user, questionnaire) -> dict:
        from recipes.jobs import enqueue_recipe_generation_job
        from recipes.services import create_recipe_generation_job

        job = create_recipe_generation_job(user, questionnaire)
        enqueue_recipe_generation_job(job.id)
        return {
            "job_id": job.id,
            "status": job.status,
            "status_url": f"/api/recipes/generation-jobs/{job.id}/",
        }

    def post(self, request):
        serializer = QuestionnaireSerializer(data=request.data)
        if serializer.is_valid():
            questionnaire = serializer.save(user=request.user, completed=True)
            recipe_generation = self._queue_recipe_generation(request.user, questionnaire)

            return Response(
                {
                    "questionnaire": serializer.data,
                    "recipe_generation": recipe_generation,
                },
                status=status.HTTP_202_ACCEPTED,
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def put(self, request):
        try:
            questionnaire = Questionnaire.objects.get(user=request.user)
        except Questionnaire.DoesNotExist:
            return Response({"detail": "Questionnaire not found"}, status=status.HTTP_404_NOT_FOUND)
        serializer = QuestionnaireSerializer(questionnaire, data=request.data, partial=True)
        if serializer.is_valid():
            questionnaire = serializer.save(completed=True)
            recipe_generation = self._queue_recipe_generation(request.user, questionnaire)

            return Response(
                {
                    "questionnaire": serializer.data,
                    "recipe_generation": recipe_generation,
                },
                status=status.HTTP_202_ACCEPTED,
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
