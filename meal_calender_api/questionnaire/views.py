from rest_framework.views import APIView
from .serializers import QuestionnaireSerializer
from .models import UserProfile as Questionnaire
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated


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

    def post(self, request):
        serializer = QuestionnaireSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(user=request.user, completed=True)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def put(self, request):
        try:
            questionnaire = Questionnaire.objects.get(user=request.user)
        except Questionnaire.DoesNotExist:
            return Response({"detail": "Questionnaire not found"}, status=status.HTTP_404_NOT_FOUND)
        serializer = QuestionnaireSerializer(questionnaire, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save(completed=True)
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
