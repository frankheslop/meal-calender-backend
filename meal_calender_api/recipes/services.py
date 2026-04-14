# recipes/services.py  ← The AI logic lives here
from questionnaire.models import UserProfile    # ← pulls from questionnaire app

def build_prompt(user):
    profile = UserProfile.objects.get(user=user)
    return f"""
        Generate a {profile.meal_type} recipe for someone who:
        - Goal: {profile.goal}
        - Diet: {profile.diet_type}
        - Allergies: {', '.join(profile.allergies)}
        - Max calories: {profile.calories_per_day // profile.meals_per_day} per meal
        - Max cooking time: {profile.cooking_time} minutes
        - Servings: {profile.servings}

        Return as JSON with: title, description, ingredients, instructions, calories.
    """

def generate_recipe(user, meal_type):
    prompt   = build_prompt(user)
    response = anthropic.messages.create(   # or openai.chat.completions.create
        model    = "claude-opus-4-5",
        messages = [{"role": "user", "content": prompt}]
    )
    data = json.loads(response.content[0].text)
    return Recipe.objects.create(**data, meal_type=meal_type)

