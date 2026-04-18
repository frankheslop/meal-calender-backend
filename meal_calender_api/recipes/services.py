"""Prompt and schema builders for AI-generated recipes."""

from __future__ import annotations

import json
import os
import importlib
from typing import Any

from questionaire.models import UserProfile


DEFAULT_RECIPE_MODEL = os.getenv("OPENAI_RECIPE_MODEL", "gpt-4.1-mini")
RECIPE_JSON_SCHEMA: dict[str, Any] = {
    "name": "recipe_generation_response",
    "strict": True,
    "schema": {
        "type": "object",
        "additionalProperties": False,
        "required": [
            "recipe_name",
            "cuisine_type",
            "diet_choice",
            "servings",
            "estimated_time",
            "nutrition_per_serving",
            "ingredients",
            "recipe_steps",
        ],
        "properties": {
            "recipe_name": {"type": "string", "minLength": 1},
            "cuisine_type": {"type": "string", "minLength": 1},
            "diet_choice": {"type": "string", "minLength": 1},
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
CUISINE_APPLICABLE_MEALS = {"dinner", "lunch"}  # snack and breakfast ignored

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

def _to_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if isinstance(value, str):
        cleaned = value.strip()
        if not cleaned:
            return []
        if cleaned.startswith("[") and cleaned.endswith("]"):
            try:
                parsed = json.loads(cleaned)
                if isinstance(parsed, list):
                    return [str(item).strip() for item in parsed if str(item).strip()]
            except json.JSONDecodeError:
                pass
        return [part.strip() for part in cleaned.split(",") if part.strip()]
    return [str(value).strip()]


def build_openai_chat_completions_request(
    profile: UserProfile,
    model: str = DEFAULT_RECIPE_MODEL,
) -> dict[str, Any]:
    """Builds a request payload for OpenAI Chat Completions API."""
    return {
        "model": model,
        "messages": [
            {"role": "system", "content": RECIPE_SYSTEM_PROMPT},
            {"role": "user", "content": build_recipe_user_prompt(profile)},
        ],
        "response_format": {
            "type": "json_schema",
            "json_schema": RECIPE_JSON_SCHEMA,
        },
    }


def generate_with_openai_chat_completions(
    profile: UserProfile,
    *,
    model: str = DEFAULT_RECIPE_MODEL,
    api_key: str | None = None,
) -> dict[str, Any]:
    """Calls OpenAI chat.completions and returns validated recipe JSON."""
    try:
        openai_module = importlib.import_module("openai")
        OpenAI = openai_module.OpenAI
    except ImportError as exc:
        raise RuntimeError("openai package is required. Install with: uv pip install openai") from exc

    key = api_key or os.getenv("OPENAI_API_KEY")
    if not key:
        raise RuntimeError("OPENAI_API_KEY is not set")

    client = OpenAI(api_key=key)
    payload = build_openai_chat_completions_request(profile=profile, model=model)
    completion = client.chat.completions.create(**payload)

    content = completion.choices[0].message.content
    if not content:
        raise RuntimeError("OpenAI returned an empty response")

    try:
        return json.loads(content)
    except json.JSONDecodeError as exc:
        raise RuntimeError("OpenAI response was not valid JSON") from exc
    

# recipes/prompt_builders.py


# The goal is to receive the meal type and the number of times per week the user wants that meal, and then generate a recipe that fits the meal type and user profile. For example, if the user wants 3 dinners per week and has a preference for Italian cuisine, we would generate an Italian dinner recipe that fits their dietary restrictions and cooking time.
def build_recipe_user_prompt(profile: UserProfile, meal_type: str = "dinner") -> str:
    allergies = _to_list(profile.allergies)
    cuisines  = _to_list(profile.cuisine_preferences)
    meal_slots = _to_list(getattr(profile, "meal_slots", []))
    unique_recipes_per_meal = getattr(profile, "unique_recipes_per_meal", {}) or {}
    if not isinstance(unique_recipes_per_meal, dict):
        unique_recipes_per_meal = {}

    unique_recipes_for_meal = unique_recipes_per_meal.get(meal_type, 1)
    try:
        unique_recipes_for_meal = max(1, int(unique_recipes_for_meal))
    except (TypeError, ValueError):
        unique_recipes_for_meal = 1

    max_calories_per_meal = max(1, profile.calories_per_day // max(profile.meals_per_day, 1))

    # Only pass cuisine into the payload if it's relevant for this meal
    cuisine_instruction = MEAL_STYLE_OVERRIDES.get(meal_type, "")
    apply_cuisine       = meal_type in CUISINE_APPLICABLE_MEALS

    request_payload = {
        "meal_type":                meal_type,
        "meal_style_instruction":   cuisine_instruction,
        "goal":                     profile.goal,
        "diet_type":                profile.diet_type,
        "allergies":                allergies,
        "calories_per_day":         profile.calories_per_day,
        "meals_per_day":            profile.meals_per_day,
        "calories_target_per_meal": max_calories_per_meal,
        "cooking_time":             profile.cooking_time,
        "household_size":           profile.household_size,
        "cooking_skill":            profile.cooking_skill,
        "meal_slots":               meal_slots,
        "unique_recipes_per_meal":  unique_recipes_per_meal,
        "unique_recipes_for_this_meal_type": unique_recipes_for_meal,

        # Only include cuisine for relevant meal types
        "cuisine_preferences": cuisines if apply_cuisine else [],
    }

    return (
        f"Generate one {meal_type} recipe using the following user profile.\n"
        "Follow the meal_style_instruction exactly.\n"
        "Return only JSON matching the required schema.\n\n"
        f"{json.dumps(request_payload, indent=2)}"
    )

