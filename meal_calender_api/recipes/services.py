"""Prompt and schema builders for AI-generated recipes."""

from __future__ import annotations

import asyncio
import json
import os
import importlib
from typing import Any
import random


DEFAULT_RECIPE_MODEL = os.getenv("OPENAI_RECIPE_MODEL", "gpt-4.1-mini")
RECIPE_JSON_SCHEMA: dict[str, Any] = {
    "name": "recipe_generation_response",
    "strict": True,
    "schema": {
        "type": "object",
        "additionalProperties": False,
        "required": [
            "meal_type",
            "recipe_name",
            "cuisine_type",
            "diet_choice",
            "servings",
            "estimated_time",
            "nutrition_per_serving",
            "ingredients",
            "grocery_list",
            "recipe_steps",
        ],
        "properties": {
            "meal_type": {"type": "string", "minLength": 5},
            "recipe_name": {"type": "string", "minLength": 5},
            "cuisine_type": {"type": "string", "minLength": 3},
            "diet_choice": {"type": "string", "minLength": 3},
            "servings": {"type": "string", "minLength": 1},
            "estimated_time": {
                "type": "object",
                "additionalProperties": False,
                "required": ["prep_time", "cook_time", "total_time"],
                "properties": {
                    "prep_time": {"type": "string", "minLength": 1},
                    "cook_time": {"type": "string", "minLength": 1},
                    "total_time": {"type": "string", "minLength": 1},
                },
            },
            "nutrition_per_serving": {
                "type": "object",
                "additionalProperties": False,
                "required": ["calories", "protein", "fat", "carbohydrates", "fiber"],
                "properties": {
                    "calories": {"type": "string", "minLength": 1},
                    "protein": {"type": "string", "minLength": 1},
                    "fat": {"type": "string", "minLength": 1},
                    "carbohydrates": {"type": "string", "minLength": 1},
                    "fiber": {"type": "string", "minLength": 1},
                },
            },
            "ingredients": {
                "type": "array",
                "items": {"type": "string", "minLength": 1},
                "minItems": 1,
            },
            "grocery_list": {
                "type": "array",
                "items": {"type": "string", "minLength": 1},
                "minItems": 1,
            },
            "recipe_steps": {
                "type": "array",
                "items": {"type": "string", "minLength": 1},
                "minItems": 1,
            },
        },
    },
}


RECIPE_SYSTEM_PROMPT = """
You are a recipe generation engine for a meal planning app.

Follow these rules exactly:
1. Output must be valid JSON only and must match the provided JSON schema exactly.
2. No markdown, no code fences, no commentary, and no extra keys.
3. Respect user constraints strictly: diet choice, allergies, cooking time, calories per meal,
   cooking skill, and household size.
4. Do not include any ingredient that conflicts with allergies or diet choice.
5. Use practical ingredient amounts and clear home-cooking steps.
6. Keep times realistic and consistent with the selected cooking_time limit.
7. nutrition_per_serving values must include units (for example: "530 kcal", "38g").
8. servings must be returned as a string value.
9. recipe_steps must be an ordered array of strings.
10. If constraints conflict, produce the closest valid recipe and reflect compromises using
    ingredient substitutions and conservative nutrition.
""".strip()

MEAL_STYLE_OVERRIDES = {
    "breakfast": (
        "Generate a practical, universally appealing breakfast. "
        "Do not apply cuisine preferences — breakfast should be simple, "
        "nutritious and familiar (e.g. eggs, oats, fruit, toast, smoothies, yoghurt)."
    ),
    "snack": (
        "Generate a simple, healthy snack. "
        "Do not apply cuisine preferences — keep it light and practical "
        "(e.g. fruit, nuts, energy balls, hummus and veg)."
    ),
    "lunch": (
        "Generate a practical lunch. Cuisine preference can loosely influence "
        "the style but keep it realistic for a midday meal "
        "(e.g. wraps, salads, soups, grain bowls)."
    ),
    "dinner": (
        "Generate a dinner recipe. Apply the user's cuisine preferences fully — "
        "this is the primary meal where cuisine style matters most."
    ),
}

def create_user_input(profile) -> dict[str, Any]:
    """Convert a UserProfile model instance to a recipe input dict."""
    return {
        "goal": profile.goal,
        "diet_type": profile.diet_type,
        "allergies": profile.allergies,
        "calories_per_day": profile.calories_per_day,
        "meals_per_day": profile.meals_per_day,
        "cooking_time": profile.cooking_time,
        "cooking_skill": profile.cooking_skill,
        "household_size": profile.household_size,
        "meal_slots": profile.meal_slots,
        "unique_recipes_per_meal": profile.unique_recipes_per_meal,
        "cuisine_preferences": profile.cuisine_preferences,  
    }



def build_recipe_user_prompts(input: dict) -> dict[str, list[str]]:
    recipe_prompt_dict = {}
    recipes_per_meal = input["unique_recipes_per_meal"]
    cuisine_preferences = input.get("cuisine_preferences", "")


    for meal in recipes_per_meal:
        recipe_prompt_dict[meal] = []
        for i in range(recipes_per_meal[meal]):  
            cuisine_preference = random.choice(cuisine_preferences) if cuisine_preferences else "None"
            request_payload = {
                "meal_type":                meal,
                "meal_style_instruction":   MEAL_STYLE_OVERRIDES[meal],
                "goal":                     input.get("goal"),
                "diet_type":                input.get("diet_type"),
                "allergies":                input.get("allergies"),
                "calories_per_day":         input.get("calories_per_day"),
                "meals_per_day":            input.get("meals_per_day"),
                "calories_target_per_meal": input.get("calories_target_per_meal"),
                "cooking_time":             input.get("cooking_time"),
                "household_size":           input.get("household_size"),
                "cooking_skill":            input.get("cooking_skill"),
                "meal_slots":               input.get("meal_slots"),
                "cuisine_preference":       cuisine_preference,

            }
            recipe_prompt_dict[meal].append(
                f"Generate one {meal} recipe using the following user profile.\n"
                "Follow the meal_style_instruction exactly.\n"
                "Return only JSON matching the required schema.\n\n"
                "The request payload is:\n"
                f"{json.dumps(request_payload, indent=2)}"
            )
    return recipe_prompt_dict




async def generate_with_openai_chat_completions_async(
    user_prompt: str,
    model: str = DEFAULT_RECIPE_MODEL,
    api_key: str | None = None,
) -> dict[str, Any]:
    """Asynchronously calls OpenAI chat.completions and returns validated recipe JSON."""
    try:
        openai_module = importlib.import_module("openai")
        AsyncOpenAI = openai_module.AsyncOpenAI
    except ImportError as exc:
        raise RuntimeError("openai package is required. Install with: uv pip install openai") from exc

    key = api_key or os.getenv("OPENAI_API_KEY")
    if not key:
        raise RuntimeError("OPENAI_API_KEY is not set")

    client = AsyncOpenAI(api_key=key)
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": RECIPE_SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        "response_format": {
            "type": "json_schema",
            "json_schema": RECIPE_JSON_SCHEMA,
        },
    }

    completion = await client.chat.completions.create(**payload)
    content = completion.choices[0].message.content
    return json.loads(content)

async def generate_recipe(input: dict | None = None) -> dict[str, list[dict[str, Any]]]:
    """Main entry point for generating a recipe based on user input.
    
    Args:
        input: Dict with recipe parameters. If None, creates a default UserProfile.
               For testing, pass a dict directly without needing Django setup.
    """
    if input is None:
        # Only import UserProfile if actually needed (lazy import)
        from questionnaire.models import UserProfile
        profile = UserProfile()
        input = create_user_input(profile)
    
    user_prompts = build_recipe_user_prompts(input)
    tasks = []
    for meal, prompts in user_prompts.items():
        for prompt in prompts:
            task = asyncio.create_task(
                generate_with_openai_chat_completions_async(prompt)
            )
            tasks.append((meal, task))

    results: dict[str, list[dict[str, Any]]] = {}
    for meal, task in tasks:
        try:
            recipe_json = await task
            results.setdefault(meal, []).append(recipe_json)
        except Exception as exc:
            results.setdefault(meal, []).append({"error": str(exc)})

    return results

