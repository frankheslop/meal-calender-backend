from django.db import models
# recipes/models.py
class Recipe(models.Model):
    title        = models.CharField(max_length=200)
    description  = models.TextField()
    ingredients  = models.JSONField()   # [{"name": "chicken", "amount": "200g"}]
    instructions = models.JSONField()   # ["Step 1...", "Step 2..."]
    calories     = models.IntegerField()
    prep_time    = models.IntegerField()  # minutes
    servings     = models.IntegerField()
    meal_type    = models.CharField(max_length=20)  # breakfast/lunch/dinner
    image_url    = models.URLField(blank=True)
    created_at   = models.DateTimeField(auto_now_add=True)

# recipes/views.py
class GenerateRecipeView(APIView):
    def post(self, request):
        # Only available to subscribed users
        if not request.user.subscription.is_active:
            return Response({"error": "Subscription required"}, status=403)
        recipe = generate_recipe(request.user, request.data["meal_type"])
        return Response(RecipeSerializer(recipe).data)
