#!/usr/bin/env python
"""Simple debugger to test recipe generation with mock data."""

import os
import sys
import time

# Load environment variables from .env file

# Add meal_calender_api to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import asyncio
import json

# Import only what we need - skip Django models entirely
try:
    from services import generate_monthly_recipes_list
except ImportError:
    print("Error: Could not import generate_monthly_recipes_list")
    print("Make sure to run this from the meal_calender_api directory:")
    print("  cd meal_calender_api && python recipes/debugger.py")
    sys.exit(1)

# Mock input data - no UserProfile needed
mock_input = {
    "goal": "gain_muscle",
    "diet_type": "high_protein",
    "allergies": ["nuts", "dairy"],
    "calories_per_day": 2500,
    "meals_per_day": 3,
    "cooking_time": "30",
    "cooking_skill": "intermediate",
    "household_size": 4,
    "meal_slots": ["breakfast", "lunch", "dinner"],
    "unique_recipes_per_meal": {"breakfast": 2, "lunch": 3, "dinner": 4},
    "cuisine_preferences": ["italian", "japanese", "mexican", "indian"],
    "measuring_standard": "metric",
}


async def main():
    print("🍳 Starting recipe generation with mock data...\n")
    try:
        recipes = await generate_monthly_recipes_list(mock_input)
        # Keep Unicode characters (like °C) readable in console/file output.
        print(json.dumps(recipes, indent=2, ensure_ascii=False))
    except Exception:
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    start_time = time.time()
    asyncio.run(main())
    end_time = time.time()
    print(f"\n⏱️  Total execution time: {(end_time - start_time) / 60:.2f} minutes")
