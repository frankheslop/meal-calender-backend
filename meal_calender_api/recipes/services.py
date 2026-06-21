"""Prompt and schema builders for AI-generated recipes."""

from __future__ import annotations

import asyncio
import json
import os
import importlib
from typing import Any
import random
from datetime import date, timedelta

"""Note: This module is designed to be used both within the Django app and as a standalone script for testing.
The way that this would be used in the views is to first get the user then create the input 
dict using create_user_input(user_profile), then pass that dict to generate_recipe(input)."""

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
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": ["item", "amount", "unit"],
                    "properties": {
                        "item": {"type": "string", "minLength": 1},
                        "amount": {"type": "string", "minLength": 1},
                        "unit": {"type": "string", "minLength": 1},
                    },
                },
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
11. grocery_list must be an array of objects in this exact shape: {"item": "chicken", "amount": "200", "unit": "gr"}.
12. When giving the grocery_list include give it in the measuring standard specified by the user (metric or imperial).
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
        "meals_per_day": len(profile.meal_slots),
        "cooking_time": profile.cooking_time,
        "cooking_skill": profile.cooking_skill,
        "household_size": profile.household_size,
        "meal_slots": profile.meal_slots,
        "unique_recipes_per_meal": profile.unique_recipes_per_meal,
        "measuring_standard": profile.measuring_standard,
        "cuisine_preferences": profile.cuisine_preferences,  
    }



def build_recipe_user_prompts_per_week(input: dict) -> dict[str, list[str]]:
    recipe_prompt_dict = {}
    recipes_per_meal = input["unique_recipes_per_meal"]
    cuisine_preferences = input.get("cuisine_preferences", "")
    # getting dates for the upcoming week to include in the prompt for better contextual recipe generation.
    today = date.today()
    days_since_monday = today.weekday()  # Monday=0, Sunday=6
    start_date = today - timedelta(days=days_since_monday)  # Get the most recent Monday
    end_date = start_date + timedelta(days=6)  # End of the week (Sunday)
    days_in_week = 7

    recipe_prompt_dict["start_date"] = start_date.isoformat()
    recipe_prompt_dict["end_date"] = end_date.isoformat()
    for meal in recipes_per_meal:
        recipe_prompt_dict[meal] = []
        for i in range(int(recipes_per_meal[meal])):
            if i == 0:
                days_span_meal = round(days_in_week / int(recipes_per_meal[meal])) + (days_in_week % int(recipes_per_meal[meal]))
            days_span_meal = round(days_in_week / int(recipes_per_meal[meal]))
            meal_start_date = start_date
            meal_end_date = meal_start_date + timedelta(days=days_span_meal - 1)


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
            recipe_prompt_dict[meal].append({
                "recipe_start_date": meal_start_date.isoformat(),
                "recipe_end_date": meal_end_date.isoformat(),
                "prompt":
                f"Generate one {meal} recipe using the following user profile.\n"
                "Follow the meal_style_instruction exactly.\n"
                "Return only JSON matching the required schema.\n\n"
                "Set grocery_list as an array of objects with exactly these keys: item, amount, unit.\n\n"
                "The request payload is:\n"
                f"{json.dumps(request_payload, indent=2)}"}
            )
            start_date = meal_end_date + timedelta(days=1)  # Next meal starts the day after the current meal ends
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
    if not api_key:
        from dotenv import load_dotenv
        load_dotenv()
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

async def generate_recipe(input:dict) -> dict[str, list[dict[str, Any]]]:
    """Main entry point for generating a recipe based on user input.
    
    Args:
        input: Dict with recipe parameters. If None, creates a default UserProfile.
               For testing, pass a dict directly without needing Django setup.
    """
    
    user_prompts = build_recipe_user_prompts_per_week(input)
    tasks = []
    for meal, prompts in user_prompts.items():
        for prompt in prompts:
            task = asyncio.create_task(
                generate_with_openai_chat_completions_async(prompt)
            )
            tasks.append((plan_week_start, meal, task))

    results: dict[str, list[dict[str, Any]]] = {}
    
    for plan_week_start, meal, task in tasks:
        try:
            recipe_json = await task
            results.setdefault(meal, []).append(recipe_json)
        except Exception as exc:
            results.setdefault(meal, []).append({"error": str(exc)})

    return results

