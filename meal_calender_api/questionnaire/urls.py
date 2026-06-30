from django.urls import path

from .views import QuestionnaireDetailView, QuestionnaireSubmitView

app_name = "questionnaire"

urlpatterns = [
    path("answers/", QuestionnaireDetailView.as_view(), name="answers"),
    path("submit/", QuestionnaireSubmitView.as_view(), name="submit"),
]
