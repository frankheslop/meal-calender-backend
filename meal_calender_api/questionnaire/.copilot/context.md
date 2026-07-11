# Questionnaire App Context

## models.py

- File path: `models.py`
- Summary: Defines the questionnaire persistence model (`UserProfile`) that stores user diet/meal/cooking preferences and completion state. This data acts as the source input for downstream recipe generation.

### Class: UserProfile

- Inherits from: `django.db.models.Model`
- Purpose: Stores one questionnaire profile per user with structured preference data used by recommendation/generation workflows.
- Fields/methods:
- `GOAL_CHOICES`: Allowed fitness/health goals.
- `MEASURING_STANDARD_CHOICES`: Allowed unit systems (`imperial`, `metric`).
- `DIET_CHOICES`: Allowed meal plan/diet types (e.g., vegetarian, vegan, keto, halal).
- `COOKING_TIME_CHOICES`: Allowed cooking-time preferences.
- `COOKING_SKILL_CHOICES`: Allowed self-reported cooking skill levels.
- `MEAL_SLOT_CHOICES`: Allowed meal slot identifiers (`breakfast`, `lunch`, `dinner`, `snack`).
- `user (OneToOneField -> users.models.User)`: One questionnaire per user; cascades on user delete.
- `goal (CharField)`: Selected user goal.
- `meal_plan_type (CharField)`: Selected diet restriction/type.
- `food_avoidances (JSONField[list])`: Allergies/dislikes list.
- `calories_per_day (IntegerField)`: Daily calorie target.
- `meal_slots (JSONField[list])`: Enabled meal slots.
- `meal_plan_repetition (IntegerField)`: Repetition cadence; validated between 1 and 4 by field validators.
- `unique_recipes_per_meal (JSONField[dict])`: Recipe-count map keyed by meal slot.
- `cooking_time (CharField)`: Preferred time budget.
- `cooking_skill (CharField)`: Skill level.
- `household_size (IntegerField)`: Number of servings/people.
- `cuisine_preferences (JSONField[list])`: Preferred cuisines.
- `measuring_standard (CharField)`: Preferred measurement system.
- `completed (BooleanField)`: Tracks whether questionnaire submission is complete.
- `created_at (DateTimeField)`: Creation timestamp.
- `updated_at (DateTimeField)`: Last update timestamp.

- Standalone functions: None.
- Notable decorators: None.

## serializers.py

- File path: `serializers.py`
- Summary: Defines DRF serializer for questionnaire payload validation and model persistence. Includes cross-field validation for meal slot consistency and recipe-count integrity.

### Class: QuestionnaireSerializer

- Inherits from: `rest_framework.serializers.ModelSerializer`
- Purpose: Validates and serializes `UserProfile` data for create/update/read API flows.
- Fields/methods:
- `Meta.model = UserProfile`
- `Meta.fields`: goal, meal_plan_type, food_avoidances, calories_per_day, meal_slots, meal_plan_repetition, unique_recipes_per_meal, cooking_time, cooking_skill, household_size, cuisine_preferences, measuring_standard, completed.
- `Meta.read_only_fields = ("completed",)`: clients cannot directly set completion via payload.
- ```python
  def validate(self, data):
  ```
  - Performs object-level validation using merge logic against `self.instance` for partial updates.
  - Enforces at least one meal slot.
  - Enforces all `meal_slots` values exist in `UserProfile.MEAL_SLOT_CHOICES`.
  - Enforces `unique_recipes_per_meal` contains counts for every chosen slot.
  - Enforces each recipe count is a positive integer.
  - Inputs: incoming validated field dict (`data`) and optional existing instance values.
  - Outputs: validated `data` dict or raises `serializers.ValidationError`.
  - Side effects: none (validation only).

- Standalone functions: None.
- Notable decorators: None.

## views.py

- File path: `views.py`
- Summary: Implements authenticated questionnaire retrieval and submit/update endpoints. Submission/update also triggers asynchronous recipe generation job creation in the `recipes` app.

### Class: QuestionnaireDetailView

- Inherits from: `rest_framework.views.APIView`
- Purpose: Returns the logged-in user's saved questionnaire data.
- Fields/methods:
- `permission_classes = [IsAuthenticated]`: endpoint requires authenticated user.
- ```python
  def get(self, request):
  ```
  - Looks up `UserProfile` by `request.user`.
  - On success returns serialized questionnaire (200).
  - If missing returns 404 with detail message.
  - Inputs: authenticated request user.
  - Outputs: questionnaire JSON or not-found detail.
  - Side effects: DB read only.

### Class: QuestionnaireSubmitView

- Inherits from: `rest_framework.views.APIView`
- Purpose: Handles first-time questionnaire submission (POST) and updates (PUT), then queues recipe generation.
- Fields/methods:
- `permission_classes = [IsAuthenticated]`: endpoint requires authenticated user.
- ```python
  def _queue_recipe_generation(self, user, questionnaire) -> dict:
  ```
  - Imports recipe job helpers from `recipes.jobs` and `recipes.services`.
  - Creates recipe generation job from questionnaire and enqueues background processing.
  - Returns metadata payload with job id/status/status URL.
  - Inputs: user instance, questionnaire instance.
  - Outputs: dict with job metadata.
  - Side effects: DB write (job create via service), background thread/task enqueue.
- ```python
  def post(self, request):
  ```
  - Validates incoming payload with `QuestionnaireSerializer(data=request.data)`.
  - On success saves profile with `user=request.user` and `completed=True`.
  - Queues recipe generation and returns questionnaire + recipe job metadata (202).
  - On validation failure returns 400.
  - Inputs: request body, authenticated user.
  - Outputs: combined questionnaire and recipe_generation payload.
  - Side effects: DB write/create on `UserProfile`; DB write/enqueue in recipes app.
- ```python
  def put(self, request):
  ```
  - Loads existing `UserProfile` for user; 404 if missing.
  - Applies partial update serializer validation and saves with `completed=True`.
  - Queues recipe generation and returns questionnaire + job metadata (202).
  - On validation failure returns 400.
  - Inputs: request body (partial), authenticated user.
  - Outputs: combined questionnaire and recipe_generation payload.
  - Side effects: DB read + write/update on `UserProfile`; DB write/enqueue in recipes app.

- Standalone functions: None.
- Notable decorators: None.

## urls.py

- File path: `urls.py`
- Summary: Defines the questionnaire app API routes for reading existing answers and submitting/updating questionnaire data.

### Module-level URL config

- `app_name = "questionnaire"`: namespaced route names for this app.
- `urlpatterns`:
- `answers/` -> `QuestionnaireDetailView.as_view()` (`answers`)
- `submit/` -> `QuestionnaireSubmitView.as_view()` (`submit`)

- Classes: None.
- Standalone functions: None.
- Notable decorators: None.

## apps.py

- File path: `apps.py`
- Summary: Declares Django app configuration metadata for questionnaire app registration.

### Class: QuestionnaireConfig

- Inherits from: `django.apps.AppConfig`
- Purpose: Registers app identity with Django app registry.
- Fields/methods:
- `name = "questionnaire"`: app import path/name.

- Standalone functions: None.
- Notable decorators: None.

## admin.py

- File path: `admin.py`
- Summary: Admin module placeholder; no questionnaire models are currently registered in Django admin.

- Classes: None.
- Standalone functions: None.
- Notable decorators: None.

## __init__.py

- File path: `__init__.py`
- Summary: Package marker for the questionnaire app module.

- Classes: None.
- Standalone functions: None.
- Notable decorators: None.

## How it fits together

- Request/data flow:
1. Client hits questionnaire routes configured in `urls.py`.
2. `QuestionnaireDetailView` reads and returns existing `UserProfile` for authenticated user.
3. `QuestionnaireSubmitView` validates payload via `QuestionnaireSerializer`.
4. Serializer enforces consistency between selected meal slots and `unique_recipes_per_meal` counts.
5. View saves/updates `UserProfile` (`completed=True`) in `models.py`.
6. Submit/update flow calls `_queue_recipe_generation`, which delegates to `recipes.services.create_recipe_generation_job` and `recipes.jobs.enqueue_recipe_generation_job`.
7. Response returns questionnaire payload plus recipe job metadata for async status polling.

- View -> Serializer mapping:
- `QuestionnaireDetailView` uses `QuestionnaireSerializer` for read serialization.
- `QuestionnaireSubmitView` uses `QuestionnaireSerializer` for create/update validation and serialization.

- Serializer -> Model mapping:
- `QuestionnaireSerializer` targets `UserProfile`.

- Cross-file dependencies:
- `views.py` imports `Questionnaire` alias from `.models` and `QuestionnaireSerializer` from `.serializers`.
- `serializers.py` validation depends on constants in `UserProfile` (`MEAL_SLOT_CHOICES`).
- `views.py` private helper `_queue_recipe_generation` imports and calls recipe app services/jobs.

- Notable relationships to other apps:
- `models.py` imports `User` from `users.models` and uses it as `OneToOneField` target.
- `views.py` imports `create_recipe_generation_job` from `recipes.services` and `enqueue_recipe_generation_job` from `recipes.jobs`, creating a direct dependency on the recipes app async pipeline.
