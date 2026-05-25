from django.shortcuts import render
from rest_framework.views import APIView
from .serializers import QuestionnaireSerializer
from .models import Questionnaire
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated

# questionnaire/views.py
class QuestionnaireView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request): # POST /api/questionnaire/  ← submit answers for the first time
        serializer = QuestionnaireSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(user=request.user)  # Associate with logged-in user
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    def get(self, request): # GET  /api/questionnaire/  ← fetch current answers
        try:
            questionnaire = Questionnaire.objects.get(user=request.user)
            serializer = QuestionnaireSerializer(questionnaire)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Questionnaire.DoesNotExist:
            return Response({"detail": "Questionnaire not found"}, status=status.HTTP_404_NOT_FOUND)
    def put(self, request): # PUT  /api/questionnaire/  ← save/update answers
        try:
            questionnaire = Questionnaire.objects.get(user=request.user)
            serializer = QuestionnaireSerializer(questionnaire, data=request.data, partial=True)
            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data, status=status.HTTP_200_OK)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except Questionnaire.DoesNotExist:
            return Response({"detail": "Questionnaire not found"}, status=status.HTTP_404_NOT_FOUND)


# Create your views here.
