"""Prompt and schema builders for AI-generated recipes."""

from __future__ import annotations

import asyncio
import json
import os
import importlib
import logging
from pathlib import Path
from typing import Any
import random
from datetime import date, timedelta
import pdb

from asgiref.sync import async_to_sync
from django.db.models import Max
from django.db import transaction

"""Note: This module is designed to be used both within the Django app and as a standalone script for testing.
The way that this would be used in the views is to first get the user then create the input 
dict using create_user_input(user_profile), then pass that dict to generate_recipe(input)."""

DEFAULT_RECIPE_MODEL = os.getenv("OPENAI_RECIPE_MODEL", "gpt-4.1-mini")
logger = logging.getLogger(__name__)
SCHEMA_FILE_PATH = Path(__file__).with_name("recipe_schema.json")
with SCHEMA_FILE_PATH.open("r", encoding="utf-8") as schema_file:
    RECIPE_JSON_SCHEMA: dict[str, Any] = json.load(schema_file)

PROMPT_CONFIG_FILE_PATH = Path(__file__).with_name("recipe_prompt_config.json")
with PROMPT_CONFIG_FILE_PATH.open("r", encoding="utf-8") as prompt_config_file:
    _prompt_config: dict[str, Any] = json.load(prompt_config_file)

RECIPE_SYSTEM_PROMPT: str = _prompt_config["recipe_system_prompt"].strip()
MEAL_STYLE_OVERRIDES: dict[str, str] = _prompt_config["meal_style_overrides"]


def build_recipe_memory_block(previous_recipes: list[dict[str, Any]], meal: str) -> str:
    """Build a low-token memory block for one meal within one week.

    We intentionally keep only high-signal fields so prompt size stays small while
    still discouraging concept-level duplicates.
    """
    if not previous_recipes:
        return ""

    lines = [
        f"Avoid repeating {meal} recipes already generated this week.",
        "Make the next recipe different in title, cuisine, and core ingredient combination.",
        "Already generated this week:",
    ]

    # Keep only short fingerprints: name + cuisine + top 2 ingredients.
    for index, recipe in enumerate(previous_recipes, start=1):
        recipe_name = recipe.get("recipe_name", "Unknown recipe")
        cuisine_type = recipe.get("cuisine_type", "Unknown cuisine")
        ingredients = recipe.get("ingredients", [])
        ingredient_text = ", ".join(ingredients) if ingredients else "Unknown ingredients"
        lines.append(f"{index}. Recipe Name: {recipe_name} | Cuisine: {cuisine_type} | Ingredients: {ingredient_text}")

    return "\n".join(lines)


def add_recipe_memory_to_prompt(
    prompt_text: str,
    previous_recipes: list[dict[str, Any]],
    meal: str,
) -> str:
    """Append short-term recipe memory to a prompt when prior recipes exist."""
    memory_block = build_recipe_memory_block(previous_recipes, meal)
    if not memory_block:
        return prompt_text

    return f"{prompt_text}\n\n{memory_block}"


def create_user_input(profile) -> dict[str, Any]:
    """Convert a user profile model into the prompt input shape used by this module."""
    # Keep the payload close to the profile fields so prompt builders stay predictable.
    return {
        "goal": profile.goal,
        "meal_plan_type": profile.meal_plan_type,
        "food_avoidances": profile.food_avoidances,
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



def build_weekly_recipe_prompts(input: dict, begin_date: date) -> dict[str, Any]:
    """Build all recipe prompts and week metadata for a single Monday-to-Sunday week."""
    recipe_prompt_dict: dict[str, Any] = {}
    recipes_per_meal = input["unique_recipes_per_meal"]
    cuisine_preferences = input.get("cuisine_preferences", "")
    # Align the requested date to a full Monday-to-Sunday week for consistent grouping.

    days_since_monday = begin_date.weekday()  # Monday=0, Sunday=6
    start_date = begin_date - timedelta(days=days_since_monday)  # Get the most recent Monday
    end_date = start_date + timedelta(days=6)  # End of the week (Sunday)

    recipe_prompt_dict["week_start_date"] = start_date.isoformat()
    recipe_prompt_dict["week_end_date"] = end_date.isoformat()
    recipe_prompt_dict["prompt_jobs"] = []
    extra_recipe_choices = 3
    for meal in recipes_per_meal:
        recipe_prompt_dict[meal] = []
        for i in range(recipes_per_meal[meal] + extra_recipe_choices):
            cuisine_preference = random.choice(cuisine_preferences) if cuisine_preferences else "None"
            request_payload = {
                "meal_type":                meal,
                "meal_style_instruction":   MEAL_STYLE_OVERRIDES[meal],
                "goal":                     input.get("goal"),
                "meal_plan_type":           input.get("meal_plan_type"),
                "food_avoidances":          input.get("food_avoidances"),
                "calories_per_day":         input.get("calories_per_day"),
                "meals_per_day":            input.get("meals_per_day"),
                "calories_target_per_meal": input.get("calories_target_per_meal"),
                "cooking_time":             input.get("cooking_time"),
                "household_size":           input.get("household_size"),
                "cooking_skill":            input.get("cooking_skill"),
                "meal_slots":               input.get("meal_slots"),
                "cuisine_preference":       cuisine_preference,

            }
            prompt_text = (
                f"Generate one {meal} recipe using the following user profile.\n"
                "Follow the meal_style_instruction exactly.\n"
                "Return only JSON matching the required schema.\n\n"
                "Set grocery_list as an array of objects with exactly these keys: item, amount, unit.\n\n"
                "The request payload is:\n"
                f"{json.dumps(request_payload, indent=2)}"
            )
            # Keep both grouped prompts and a flat prompt_jobs view available to callers.
            recipe_prompt_dict[meal].append({"prompt": prompt_text})
            recipe_prompt_dict["prompt_jobs"].append({"meal": meal, "prompt": prompt_text})
    return recipe_prompt_dict




async def generate_with_openai_chat_completions_async(
    user_prompt: str,
    model: str = DEFAULT_RECIPE_MODEL,
    api_key: str | None = None,
) -> dict[str, Any]:
    """Call OpenAI once and return the parsed recipe JSON response.

    This function is intentionally stateless. Callers are responsible for adding any
    short-term recipe memory they want the model to consider.
    """
    try:
        openai_module = importlib.import_module("openai")
        AsyncOpenAI = openai_module.AsyncOpenAI
    except ImportError as exc:
        raise RuntimeError("openai package is required. Install with: uv pip install openai") from exc
    if not api_key:
        # Only load dotenv when the caller did not explicitly provide an API key.
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


async def generate_meal_recipes_for_week(
    week: str,
    user_prompts: dict[str, Any],
    meal: str,
) -> list[dict[str, Any]]:
    """Generate recipes for one meal type in one week, sequentially.

    Sequential generation is intentional so each next prompt can include short-term
    memory from recipes already generated for the same meal in the same week.
    """
    generated_recipes_for_meal: list[dict[str, Any]] = []

    for prompt_job in user_prompts[meal]:
        prompt_text = add_recipe_memory_to_prompt(
            prompt_job["prompt"],
            generated_recipes_for_meal,
            meal,
        )
        try:
            recipe_json = await generate_with_openai_chat_completions_async(prompt_text)
            generated_recipes_for_meal.append(recipe_json)
        except Exception:
            logger.exception(
                "Failed to generate recipe",
                extra={
                    "week": week,
                    "week_start_date": user_prompts["week_start_date"],
                    "week_end_date": user_prompts["week_end_date"],
                    "meal": meal,
                },
            )

    return generated_recipes_for_meal


async def generate_week_recipes(
    week: str,
    user_prompts: dict[str, Any],
    meals: list[str],
) -> dict[str, Any]:
    """Generate all meals for one week.

    Meal types run concurrently (breakfast/lunch/dinner/snack), while each meal chain
    remains sequential to preserve short-term deduplication memory.
    """
    week_result: dict[str, Any] = {
        "week_start_date": user_prompts["week_start_date"],
        "week_end_date": user_prompts["week_end_date"],
        **{meal: [] for meal in meals},
    }

    # Parallelize meal types inside the same week.
    meal_tasks = [
        asyncio.create_task(generate_meal_recipes_for_week(week, user_prompts, meal))
        for meal in meals
    ]
    meal_outputs = await asyncio.gather(*meal_tasks)

    for meal, recipes in zip(meals, meal_outputs):
        week_result[meal] = recipes

    return week_result


async def generate_monthly_recipes_list(
    input: dict,
    begin_date: date | None = None,
) -> dict[str, dict[str, Any]]:
    """Generate monthly recipes grouped by week and meal.

    Recipes for the same meal within the same week are generated sequentially so each
    later prompt can see a compact summary of what was already created and avoid repeats.
    """
    number_of_weeks = 4
    anchor_date = begin_date or date.today()
    monthly_prompts = {}
    for week in range(number_of_weeks):
        start_date = anchor_date + timedelta(weeks=week)
        user_prompts = build_weekly_recipe_prompts(input, start_date)
        week_label = user_prompts["week_start_date"]
        monthly_prompts[week_label] = user_prompts

    meals = list(input["unique_recipes_per_meal"].keys())
    results: dict[str, dict[str, Any]] = {}

    # Parallelize weeks so users do not wait for strict week-by-week processing.
    week_keys = list(monthly_prompts.keys())
    week_tasks = [
        asyncio.create_task(generate_week_recipes(week, monthly_prompts[week], meals))
        for week in week_keys
    ]
    week_outputs = await asyncio.gather(*week_tasks)

    for week, week_result in zip(week_keys, week_outputs):
        results[week] = week_result

    return results


def build_weekly_generation_records(
    monthly_results: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    """Convert monthly output into one persistence record payload per week."""
    weekly_records: list[dict[str, Any]] = []

    for _, week_payload in monthly_results.items():
        week_start_date = week_payload["week_start_date"]
        week_end_date = week_payload["week_end_date"]
        meals_output = {
            key: value
            for key, value in week_payload.items()
            if key not in {"week_start_date", "week_end_date"}
        }
        weekly_records.append(
            {
                "week_start_date": week_start_date,
                "week_end_date": week_end_date,
                "meals_output": meals_output,
            }
        )

    return weekly_records


def save_weekly_recipe_generations(
    job,
    monthly_results: dict[str, dict[str, Any]],
):
    """Persist one WeeklyRecipeGeneration row per generated week."""
    from .models import WeeklyRecipeGeneration

    weekly_records = build_weekly_generation_records(monthly_results)
    generation_rows = [
        WeeklyRecipeGeneration(
            job=job,
            user=job.user,
            week_start_date=date.fromisoformat(record["week_start_date"]),
            week_end_date=date.fromisoformat(record["week_end_date"]),
            meals_output=record["meals_output"],
        )
        for record in weekly_records
    ]

    with transaction.atomic():
        WeeklyRecipeGeneration.objects.bulk_create(generation_rows)

    return generation_rows


def create_recipe_generation_job(user, profile, start_from_date: date | None = None):
    """Create a queued generation job using the current questionnaire snapshot."""
    from .models import RecipeGenerationJob

    requested_input = create_user_input(profile)
    return RecipeGenerationJob.objects.create(
        user=user,
        requested_input=requested_input,
        start_from_date=start_from_date,
    )


def generate_and_store_weekly_recipes(job) -> dict[str, Any]:
    """Generate four weeks of recipes for a queued job, then save one row per week."""
    requested_input = job.requested_input
    monthly_results = async_to_sync(generate_monthly_recipes_list)(requested_input, job.start_from_date)
    generation_rows = save_weekly_recipe_generations(
        job,
        monthly_results,
    )

    return {
        "job_id": job.id,
        "weeks_saved": len(generation_rows),
        "results": monthly_results,
    }


def maybe_queue_recipe_top_up(user) -> dict[str, Any]:
    """Queue another 4-week generation when only one future week remains."""
    from questionnaire.models import UserProfile

    from .jobs import enqueue_recipe_generation_job
    from .models import RecipeGenerationJob, WeeklyRecipeGeneration

    if RecipeGenerationJob.objects.filter(
        user=user,
        status__in=[RecipeGenerationJob.Status.QUEUED, RecipeGenerationJob.Status.RUNNING],
    ).exists():
        return {"triggered": False, "reason": "job_already_in_progress"}

    today = date.today()
    current_week_start = today - timedelta(days=today.weekday())
    future_weeks_count = (
        WeeklyRecipeGeneration.objects.filter(user=user, week_start_date__gt=current_week_start)
        .values("week_start_date")
        .distinct()
        .count()
    )

    if future_weeks_count > 1:
        return {"triggered": False, "reason": "enough_future_weeks", "future_weeks_count": future_weeks_count}

    try:
        profile = UserProfile.objects.get(user=user, completed=True)
    except UserProfile.DoesNotExist:
        return {"triggered": False, "reason": "questionnaire_not_completed"}

    latest_week_end = WeeklyRecipeGeneration.objects.filter(user=user).aggregate(max_end=Max("week_end_date"))["max_end"]
    start_from_date = latest_week_end + timedelta(days=1) if latest_week_end else current_week_start

    job = create_recipe_generation_job(user, profile, start_from_date=start_from_date)
    enqueue_recipe_generation_job(job.id)
    return {
        "triggered": True,
        "job_id": job.id,
        "status": job.status,
        "start_from_date": start_from_date.isoformat(),
    }

