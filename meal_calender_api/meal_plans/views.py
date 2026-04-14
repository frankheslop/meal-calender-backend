from django.shortcuts import render
from rest_framework.views import APIView


# meal_plans/views.py
class WeeklyPlanView(APIView):
    def get(self, request):
        # Returns the full week structured for the calendar
        plan = MealPlan.objects.get(user=request.user, week_start=this_monday())
        return Response(MealPlanSerializer(plan).data)

    def post(self, request):
        # Auto-generate a full week using the recipes app
        plan = generate_weekly_plan(request.user)
        return Response(MealPlanSerializer(plan).data)
