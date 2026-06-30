# services.py — Call Flow & Concurrency Reference

## Function Call Flow: `generate_monthly_recipes_list`

```
generate_monthly_recipes_list(input)
│
├── build_weekly_recipe_prompts(input, start_date)  ← called 4 times (week 1–4)
│   └── returns: { week_start_date, week_end_date, breakfast: [...], lunch: [...], prompt_jobs: [...] }
│
├── asyncio.gather( week_tasks )  ← 4 tasks run concurrently
│   │
│   ├── generate_week_recipes("week_1", user_prompts, meals)
│   │   │
│   │   └── asyncio.gather( meal_tasks )  ← N tasks run concurrently (one per meal type)
│   │       │
│   │       ├── generate_meal_recipes_for_week("week_1", user_prompts, "breakfast")
│   │       │   ├── prompt_1 → add_recipe_memory_to_prompt(prompt, [], "breakfast")
│   │       │   │              └── build_recipe_memory_block([], "breakfast") → ""
│   │       │   │   └── generate_with_openai_chat_completions_async(prompt_1)  ← API call
│   │       │   │       └── returns recipe_1
│   │       │   ├── prompt_2 → add_recipe_memory_to_prompt(prompt, [recipe_1], "breakfast")
│   │       │   │              └── build_recipe_memory_block([recipe_1], "breakfast") → "Do not repeat..."
│   │       │   │   └── generate_with_openai_chat_completions_async(prompt_2 + memory)  ← API call
│   │       │   │       └── returns recipe_2
│   │       │   └── ... (sequential for each prompt in breakfast)
│   │       │       └── returns [recipe_1, recipe_2, ...]
│   │       │
│   │       ├── generate_meal_recipes_for_week("week_1", user_prompts, "lunch")
│   │       │   └── ... same sequential pattern as breakfast, but runs independently
│   │       │
│   │       └── generate_meal_recipes_for_week("week_1", user_prompts, "dinner")
│   │           └── ... same sequential pattern, also runs independently
│   │
│   ├── generate_week_recipes("week_2", ...)  ← runs at same time as week_1
│   ├── generate_week_recipes("week_3", ...)  ← runs at same time as week_1
│   └── generate_week_recipes("week_4", ...)  ← runs at same time as week_1
│
└── returns results:
    {
      "week_1": { week_start_date, week_end_date, breakfast: [...], lunch: [...], dinner: [...] },
      "week_2": { ... },
      "week_3": { ... },
      "week_4": { ... }
    }
```

---

## Concurrency Summary

| Level | Behaviour | Why |
|---|---|---|
| Weeks | Concurrent | Weeks are independent, no shared state |
| Meal types per week | Concurrent | Breakfast/lunch/dinner don't depend on each other |
| Recipes per meal type | Sequential | Each prompt needs memory of the previous recipe to avoid repeats |

---

## Key Helper Functions

| Function | Purpose |
|---|---|
| `build_weekly_recipe_prompts` | Builds all prompts and metadata for one Mon–Sun week |
| `generate_meal_recipes_for_week` | Generates all recipes for one meal type in one week sequentially |
| `generate_week_recipes` | Runs all meal types for one week concurrently |
| `generate_monthly_recipes_list` | Entry point — runs all 4 weeks concurrently |
| `add_recipe_memory_to_prompt` | Appends a short-term memory block to the next prompt in a meal chain |
| `build_recipe_memory_block` | Formats the compact "already generated this week" summary text |
| `generate_with_openai_chat_completions_async` | Stateless single OpenAI API call — used at every leaf node |

---

## Short-Term Memory Chain (per meal per week)

Each recipe generated in a meal type feeds a compact summary into the next prompt:

```
prompt_1 (no memory)
  → recipe_1: "Berry Oat Bowl | Universal | oats, berries, yogurt"

prompt_2 + memory block:
  "Do not repeat breakfast recipes already generated for this week.
   Already generated:
   1. Berry Oat Bowl | cuisine: Universal | core ingredients: oats, berries, yogurt"
  → recipe_2: clearly different concept

prompt_3 + memory block (recipe_1 + recipe_2):
  → recipe_3: clearly different from both
```

Memory is scoped to one `week + meal` pair. It resets for every new week and every new meal type.
