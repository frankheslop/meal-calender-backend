from django.shortcuts import render

# questionnaire/views.py
class QuestionnaireView(RetrieveUpdateAPIView):
    def get(self, request): # GET  /api/questionnaire/  ← fetch current answers
        pass
    def put(self, request): # PUT  /api/questionnaire/  ← save/update answers
        pass


# Create your views here.
