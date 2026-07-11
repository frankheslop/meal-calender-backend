# Recipes App Context

## models.py

- File path: `models.py`
- Summary: Defines the persistence layer for asynchronous recipe generation jobs and per-week generated recipe payloads. It stores both job lifecycle metadata and weekly JSON outputs keyed by user/job/week.

### Class: RecipeGenerationJob

- Inherits from: `django.db.models.Model`
- Purpose: Tracks one recipe-generation request lifecycle from queued -> running -> succeeded/failed.
- Fields/methods:
- `Status (TextChoices)`: Enum-like status values (`queued`, `running`, `succeeded`, `failed`) used by `status`.
- `user (ForeignKey -> settings.AUTH_USER_MODEL)`: Owner of the generation job; cascades on user delete.
- `requested_input (JSONField)`: Snapshot of questionnaire/user input used for generation.
- `start_from_date (DateField, nullable)`: Optional start date anchor for generated week ranges.
- `status (CharField)`: Current lifecycle state; defaults to `queued`.
- `celery_task_id (CharField)`: Placeholder/metadata for async task id (currently thread runner is used).
- `error_message (TextField)`: Failure details when generation fails.
- `created_at (DateTimeField)`: Job creation timestamp.
- `started_at (DateTimeField, nullable)`: Timestamp when processing begins.
- `completed_at (DateTimeField, nullable)`: Timestamp when processing ends (success/failure).
- `Meta.ordering = ["-created_at"]`: Newest jobs first.
- `__str__(self) -> str`: Human-readable job identifier/status string.

### Class: WeeklyRecipeGeneration

- Inherits from: `django.db.models.Model`
- Purpose: Stores one generated week of meal recipes tied to a job and user.
- Fields/methods:
- `job (ForeignKey -> RecipeGenerationJob)`: Parent job producing this week.
- `user (ForeignKey -> settings.AUTH_USER_MODEL)`: User owning generated week.
- `week_start_date (DateField)`: Monday-aligned week start date.
- `week_end_date (DateField)`: Week end date.
- `meals_output (JSONField)`: Structured generated recipes by meal key.
- `created_at (DateTimeField)`: Record creation timestamp.
- `Meta.ordering = ["-week_start_date", "-created_at"]`: Most recent weeks first.
- `Meta.indexes`: Composite indexes on (`job`, `week_start_date`) and (`user`, `week_start_date`) for status/detail and user-week queries.
- `__str__(self) -> str`: Human-readable user/week summary string.

- Standalone functions: None.
- Notable decorators: None.

## serializers.py

- File path: `serializers.py`
- Summary: Defines DRF serializers for job-status responses and nested weekly generation payloads. It shapes API output for job polling and user weekly listing endpoints.

### Class: WeeklyRecipeGenerationSerializer

- Inherits from: `rest_framework.serializers.ModelSerializer`
- Purpose: Serializes weekly generation records for API responses.
- Fields/methods:
- `Meta.model = WeeklyRecipeGeneration`
- `Meta.fields = ("id", "week_start_date", "week_end_date", "meals_output", "created_at")`

### Class: RecipeGenerationJobStatusSerializer

- Inherits from: `rest_framework.serializers.ModelSerializer`
- Purpose: Serializes job state plus nested generated weeks.
- Fields/methods:
- `weeks = WeeklyRecipeGenerationSerializer(source="weekly_generations", many=True, read_only=True)`: Exposes reverse FK relation from `RecipeGenerationJob` to weekly records.
- `Meta.model = RecipeGenerationJob`
- `Meta.fields = ("id", "status", "error_message", "created_at", "started_at", "completed_at", "weeks")`

- Standalone functions: None.
- Notable decorators: None.

## views.py

- File path: `views.py`
- Summary: Provides authenticated read endpoints for polling generation-job status and listing user weekly generations. It also triggers auto top-up queueing when user inventory is low.

### Class: RecipeGenerationJobStatusView

- Inherits from: `rest_framework.views.APIView`
- Purpose: Returns status/details for one job that belongs to the authenticated user.
- Fields/methods:
- `permission_classes = [IsAuthenticated]`: Requires authenticated user.
- ```python
  def get(self, request, job_id: int)
  ```
  - Loads `RecipeGenerationJob` by `id` scoped to `request.user`.
  - Returns 404 if not found.
  - Serializes with `RecipeGenerationJobStatusSerializer` and returns 200.
  - Inputs: path param `job_id`, authenticated `request.user`.
  - Outputs: JSON job lifecycle data plus nested weeks.
  - Side effects: DB read only.

### Class: UserWeeklyRecipeGenerationsView

- Inherits from: `rest_framework.views.APIView`
- Purpose: Lists all weekly generations for the authenticated user and may enqueue a new generation job.
- Fields/methods:
- `permission_classes = [IsAuthenticated]`: Requires authenticated user.
- ```python
  def get(self, request)
  ```
  - Calls `maybe_queue_recipe_top_up(request.user)` before querying weeks.
  - Queries `WeeklyRecipeGeneration` for `request.user` and serializes many.
  - Returns `{ top_up, weekly_generations }` payload.
  - Inputs: authenticated `request.user`.
  - Outputs: top-up status object and list of weekly generation objects.
  - Side effects: may create/enqueue a job indirectly via service; always performs DB reads.

- Standalone functions: None.
- Notable decorators: None.

## urls.py

- File path: `urls.py`
- Summary: Registers URL routes for recipe job status polling and user weekly generation listing.

### Module-level URL config

- `app_name = "recipes"`: Namespaced URL names under `recipes`.
- `urlpatterns`:
- `generation-jobs/<int:job_id>/` -> `RecipeGenerationJobStatusView.as_view()` (`generation-job-status`)
- `weekly-generations/` -> `UserWeeklyRecipeGenerationsView.as_view()` (`user-weekly-generations`)

- Classes: None.
- Standalone functions: None.
- Notable decorators: None.

## apps.py

- File path: `apps.py`
- Summary: Declares Django app configuration metadata for app registration/loading.

### Class: RecipesConfig

- Inherits from: `django.apps.AppConfig`
- Purpose: Registers app identity with Django.
- Fields/methods:
- `name = "recipes"`: App import path/name used by Django app registry.

- Standalone functions: None.
- Notable decorators: None.

## admin.py

- File path: `admin.py`
- Summary: Admin module placeholder; currently no recipes models are registered with Django admin.

- Classes: None.
- Standalone functions: None.
- Notable decorators: None.

## services.py

- File path: `services.py`
- Summary: Core domain service layer for prompt construction, OpenAI generation orchestration, weekly/monthly aggregation, persistence, job creation, and automatic top-up queueing.

### Standalone function

```python
def build_recipe_memory_block(previous_recipes: list[dict[str, Any]], meal: str) -> str:
```
- Builds a compact text memory block from prior recipes for one meal to reduce duplicate concepts in subsequent prompts.
- Inputs: `previous_recipes` list of generated recipe dicts, `meal` name.
- Outputs: newline-delimited prompt appendix string (or empty string).
- Side effects: none.

### Standalone function

```python
def add_recipe_memory_to_prompt(prompt_text: str, previous_recipes: list[dict[str, Any]], meal: str) -> str:
```
- Appends memory block (if any) to a prompt.
- Inputs: base prompt, prior recipes, meal name.
- Outputs: augmented prompt string.
- Side effects: none.

### Standalone function

```python
def create_user_input(profile) -> dict[str, Any]:
```
- Maps questionnaire profile object fields into recipe-generation input shape.
- Inputs: `profile` model instance (expects fields like `goal`, `meal_slots`, `unique_recipes_per_meal`, etc.).
- Outputs: normalized input dict for prompt generation.
- Side effects: none.

### Standalone function

```python
def build_weekly_recipe_prompts(input: dict, begin_date: date) -> dict[str, Any]:
```
- Builds prompts for one Monday-Sunday week and each meal type; includes extra over-generation slots.
- Inputs: user input dict, anchor date.
- Outputs: dict containing `week_start_date`, `week_end_date`, meal prompt lists, and flat `prompt_jobs`.
- Side effects: uses random cuisine sampling (`random.choice`), no I/O/DB writes.

### Standalone async function

```python
async def generate_with_openai_chat_completions_async(user_prompt: str, model: str = DEFAULT_RECIPE_MODEL, api_key: str | None = None) -> dict[str, Any]:
```
- Calls OpenAI chat completions with JSON schema response format and parses returned JSON.
- Inputs: prompt text, optional model name, optional API key.
- Outputs: parsed recipe JSON dict.
- Side effects: external network call to OpenAI API; may load `.env` via `dotenv`; raises runtime errors for missing dependency/key.

### Standalone async function

```python
async def generate_meal_recipes_for_week(week: str, user_prompts: dict[str, Any], meal: str) -> list[dict[str, Any]]:
```
- Generates recipes sequentially for one meal in one week so each prompt can include short-term memory.
- Inputs: week label, prompt bundle, meal key.
- Outputs: list of generated recipe dicts.
- Side effects: repeated OpenAI calls; exception logging.

### Standalone async function

```python
async def generate_week_recipes(week: str, user_prompts: dict[str, Any], meals: list[str]) -> dict[str, Any]:
```
- Generates all meal types for a week concurrently while preserving sequential chain per meal.
- Inputs: week label, weekly prompts, meal key list.
- Outputs: week payload with week range plus generated recipes by meal.
- Side effects: concurrent async tasks/OpenAI calls.

### Standalone async function

```python
async def generate_monthly_recipes_list(input: dict, begin_date: date | None = None) -> dict[str, dict[str, Any]]:
```
- Builds prompts for 4 weeks and generates each week concurrently.
- Inputs: user input dict, optional start date.
- Outputs: dict keyed by `week_start_date` -> generated week payload.
- Side effects: concurrent async generation/OpenAI calls.

### Standalone function

```python
def build_weekly_generation_records(monthly_results: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
```
- Converts monthly nested output into persistence-ready per-week records.
- Inputs: monthly results map.
- Outputs: list of records with `week_start_date`, `week_end_date`, `meals_output`.
- Side effects: none.

### Standalone function

```python
def save_weekly_recipe_generations(job, monthly_results: dict[str, dict[str, Any]]):
```
- Bulk persists one `WeeklyRecipeGeneration` row per week inside an atomic transaction.
- Inputs: `job` model instance, monthly results map.
- Outputs: list of created `WeeklyRecipeGeneration` instances.
- Side effects: DB writes (`bulk_create`) under `transaction.atomic`.
- Notable decorators/context managers:
- `transaction.atomic()`: all weekly row inserts succeed or rollback together.

### Standalone function

```python
def create_recipe_generation_job(user, profile, start_from_date: date | None = None):
```
- Creates a queued `RecipeGenerationJob` from current questionnaire snapshot.
- Inputs: user instance, questionnaire profile instance, optional start date.
- Outputs: created job instance.
- Side effects: DB write to `RecipeGenerationJob`.

### Standalone function

```python
def generate_and_store_weekly_recipes(job) -> dict[str, Any]:
```
- Runs 4-week generation synchronously (async bridged with `async_to_sync`) and persists outputs.
- Inputs: job instance containing `requested_input` and optional start date.
- Outputs: summary dict with `job_id`, `weeks_saved`, and raw `results`.
- Side effects: OpenAI external calls and DB writes (via save helper).

### Standalone function

```python
def maybe_queue_recipe_top_up(user) -> dict[str, Any]:
```
- Decides whether to enqueue a new 4-week generation when user has <= 1 future week and no active job.
- Inputs: user instance.
- Outputs: status dict describing whether queueing was triggered and why.
- Side effects:
- DB reads for active jobs/future week counts/latest week end date/profile.
- DB write via `create_recipe_generation_job` when triggered.
- Starts background thread job indirectly via `enqueue_recipe_generation_job`.
- Cross-app dependency: imports `UserProfile` from `questionnaire.models`.

- Module-level constants/state:
- `DEFAULT_RECIPE_MODEL`: model selection from env.
- `RECIPE_JSON_SCHEMA`: loaded from `recipe_schema.json`.
- `RECIPE_SYSTEM_PROMPT`, `MEAL_STYLE_OVERRIDES`: loaded from `recipe_prompt_config.json`.

- Notable decorators:
- None.

## jobs.py

- File path: `jobs.py`
- Summary: Lightweight in-process asynchronous execution layer that runs recipe generation in a background thread and updates job state transitions.

### Standalone function

```python
def _run_recipe_generation_job(job_id: int) -> None:
```
- Internal worker routine to execute one job and update lifecycle fields.
- Inputs: job id.
- Outputs: none.
- Side effects:
- DB reads/writes on `RecipeGenerationJob` status timestamps/errors.
- Calls `generate_and_store_weekly_recipes` (external API calls + DB writes downstream).
- Closes/reopens DB connections for thread safety (`close_old_connections`).
- Logs warnings/errors.

### Standalone function

```python
def enqueue_recipe_generation_job(job_id: int) -> None:
```
- Spawns a daemon thread to run `_run_recipe_generation_job` outside request thread.
- Inputs: job id.
- Outputs: none.
- Side effects: starts background daemon thread.

- Notable decorators:
- None.

## __init__.py

- File path: `__init__.py`
- Summary: Package marker for the `recipes` app module.

- Classes: None.
- Standalone functions: None.
- Notable decorators: None.

## debugger.py

- File path: `debugger.py`
- Summary: Standalone script utility for manual/local testing of recipe generation with mock input, bypassing Django models.

### Standalone async function

```python
async def main():
```
- Runs `generate_monthly_recipes_list` with hard-coded mock input and prints JSON output.
- Inputs: none (uses module-level `mock_input`).
- Outputs: none (prints to stdout).
- Side effects: external OpenAI calls via services, console output.

### Script entrypoint block

```python
if __name__ == "__main__":
```
- Measures execution time, runs async `main`, prints total runtime.
- Side effects: console output, process exit codes on import failure path.

- Classes: None.
- Notable decorators: None.

## How it fits together

- Request/data flow:
1. Router maps incoming paths in `urls.py` to API views in `views.py`.
2. `RecipeGenerationJobStatusView` reads job + nested weeks and returns serialized status/result data.
3. `UserWeeklyRecipeGenerationsView` first calls `services.maybe_queue_recipe_top_up(user)`.
4. Top-up service checks DB state and questionnaire completion; if needed, creates a `RecipeGenerationJob` and calls `jobs.enqueue_recipe_generation_job(job_id)`.
5. Background thread (`jobs._run_recipe_generation_job`) marks job running, calls `services.generate_and_store_weekly_recipes`, then marks job succeeded/failed.
6. Generation service builds prompts, calls OpenAI asynchronously, aggregates weekly/monthly payloads, and persists `WeeklyRecipeGeneration` rows.
7. Views serialize and return `WeeklyRecipeGeneration` and job status data to clients.

- View -> Serializer mapping:
- `RecipeGenerationJobStatusView` -> `RecipeGenerationJobStatusSerializer` (which nests `WeeklyRecipeGenerationSerializer`).
- `UserWeeklyRecipeGenerationsView` -> `WeeklyRecipeGenerationSerializer` (many=True for user list).

- Serializer -> Model mapping:
- `WeeklyRecipeGenerationSerializer` -> `WeeklyRecipeGeneration`.
- `RecipeGenerationJobStatusSerializer` -> `RecipeGenerationJob` with reverse relation `weekly_generations`.

- Cross-file dependencies:
- `views.py` imports `maybe_queue_recipe_top_up` from `services.py`.
- `views.py` imports `RecipeGenerationJob`/`WeeklyRecipeGeneration` models and DRF serializers.
- `services.py` imports `enqueue_recipe_generation_job` from `jobs.py` (inside function), and models (`RecipeGenerationJob`, `WeeklyRecipeGeneration`) inside helper functions.
- `jobs.py` imports `generate_and_store_weekly_recipes` from `services.py` and updates `RecipeGenerationJob` lifecycle fields.
- Persistence path is: `services.generate_and_store_weekly_recipes` -> `services.save_weekly_recipe_generations` -> `WeeklyRecipeGeneration.objects.bulk_create`.

- Notable relationships to other apps:
- `services.py` depends on `questionnaire.models.UserProfile` to determine whether recipe top-up is allowed and to build job input.
- User references use `settings.AUTH_USER_MODEL` (configured in users app), linking jobs/weeks to the project user model.
