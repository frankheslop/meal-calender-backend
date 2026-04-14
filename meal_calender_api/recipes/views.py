from django.shortcuts import render

# recipes/views.py
class GenerateRecipeView(APIView):
    def post(self, request):
        # Only available to subscribed users
        if not request.user.subscription.is_active:
            return Response({"error": "Subscription required"}, status=403)
        recipe = generate_recipe(request.user, request.data["meal_type"])
        return Response(RecipeSerializer(recipe).data)