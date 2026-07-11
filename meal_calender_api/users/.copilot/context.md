# Users App Context

## models.py

Purpose: Defines the custom authentication user model used by the project. It extends Django's built-in user model and adds account metadata fields.

### Class: CustomUser

Inherits from: AbstractUser

Purpose: Project user entity with unique email and additional profile/account state fields.

Fields and methods:
- email (EmailField, unique=True): Primary email address; uniqueness is enforced at the database level.
- email_verified (BooleanField, default=False): Tracks whether the email has been verified.
- timezone (CharField, max_length=64, default="UTC"): Stores the user's preferred timezone.
- Inherited fields/methods from AbstractUser: username, password, first_name, last_name, is_active, is_staff, permissions, authentication helpers, etc.

Standalone functions:
- None.

Notable decorators:
- None.

Additional module-level symbols:
- User = CustomUser: Backward-compatibility alias for modules importing User from this file.

## serializers.py

Purpose: Defines REST Framework serializers for user read/update payloads and authentication-related input payloads.

### Class: UserSerializer

Inherits from: serializers.ModelSerializer

Purpose: Serializes user profile data for API responses and profile updates.

Fields and methods:
- Meta.model: User (resolved via get_user_model()).
- Meta.fields: id, username, email, timezone, email_verified.
- Meta.read_only_fields: id and email_verified (cannot be modified through this serializer).

Notable decorators:
- None.

### Class: RegisterSerializer

Inherits from: serializers.ModelSerializer

Purpose: Validates registration payloads and creates users with properly hashed passwords.

Fields and methods:
- password (CharField, write_only=True): Accepts password input but never returns it in responses.
- Meta.model: User.
- Meta.fields: username, email, password, timezone.
- create(validated_data): Creates and returns a user using User.objects.create_user so password hashing and default user creation behavior are preserved.
  - Side effects: DB write (new user row).

Notable decorators:
- None.

### Class: LoginSerializer

Inherits from: serializers.Serializer

Purpose: Validates login credentials payload.

Fields and methods:
- username (CharField): Accepts either username or email-like input (view determines how it is interpreted).
- password (CharField, write_only=True): Password credential.

Notable decorators:
- None.

Standalone functions:
- None.

## views.py

Purpose: Implements auth/profile API endpoints: register, login, and authenticated profile retrieval/update.

### Class: RegisterView

Inherits from: APIView

Purpose: Handles user registration and token issuance.

Fields and methods:
- permission_classes = [AllowAny]: Endpoint is publicly accessible.
- post(self, request):
  - Validates request data with RegisterSerializer.
  - On success, saves the user and creates/retrieves an auth token.
  - Returns token plus serialized user data with HTTP 201.
  - On validation failure, returns serializer errors with HTTP 400.
  - Side effects: DB write (user creation), DB write/read (token create/get).

Notable decorators:
- None (uses class attribute permission_classes rather than a decorator).

### Class: LoginView

Inherits from: APIView

Purpose: Authenticates users and returns an auth token with user payload.

Fields and methods:
- permission_classes = [AllowAny]: Endpoint is publicly accessible.
- post(self, request):
  - Validates request data with LoginSerializer.
  - Attempts authentication using username/password.
  - If username auth fails and the username contains @, performs case-insensitive email lookup, then retries authentication with matched username.
  - On success, creates/retrieves token and returns token plus serialized user with HTTP 200.
  - On auth failure, returns error with HTTP 401.
  - On validation failure, returns serializer errors with HTTP 400.
  - Side effects: DB reads (user lookup), DB write/read (token create/get), authentication backend invocation.

Notable decorators:
- None (uses class attribute permission_classes rather than a decorator).

### Class: ProfileView

Inherits from: RetrieveUpdateAPIView

Purpose: Retrieves and updates the currently authenticated user's profile (no user id URL parameter needed).

Fields and methods:
- permission_classes = [IsAuthenticated]: Requires valid authentication (token auth expected by project setup).
- serializer_class = UserSerializer: Uses profile serializer for read/update.
- get_object(self): Returns request.user so the endpoint always operates on the current authenticated user.
  - Side effects: None directly; update operations from inherited view behavior can write user fields to DB.

Notable decorators:
- None.

Standalone functions:
- None.

## urls.py

Purpose: Declares URL routes for the users app API endpoints.

### Module-level URL configuration

- app_name = "users": Namespaces URL names under users.
- urlpatterns:
  - register/ -> RegisterView.as_view(), name="register"
  - login/ -> LoginView.as_view(), name="login"
  - profile/ -> ProfileView.as_view(), name="profile"

Classes in this file:
- None.

Standalone functions in this file:
- None.

Notable decorators:
- None.

## __init__.py

Purpose: Package marker for the users Django app module.

Classes in this file:
- None.

Standalone functions in this file:
- None.

Notable decorators:
- None.

## apps.py

Purpose: Defines Django app configuration metadata for app registration.

### Class: UsersConfig

Inherits from: AppConfig

Purpose: Identifies the app to Django's app registry.

Fields and methods:
- name = "users": App label/path Django uses when loading the app.

Notable decorators:
- None.

Standalone functions:
- None.

## admin.py

Purpose: Registers and customizes admin interface behavior for the custom user model.

### Class: CustomUserAdmin

Inherits from: UserAdmin

Purpose: Extends Django admin presentation for CustomUser to expose custom fields and improved listing/search behavior.

Fields and methods:
- list_display: Shows username, email, email_verified, timezone, is_staff, is_active in admin list view.
- search_fields: Enables admin search by username and email.
- fieldsets: Extends UserAdmin fieldsets with an "Account Preferences" section containing timezone and email_verified.
- Inherited UserAdmin behavior handles CRUD forms, permissions, and save flows.

Notable decorators:
- @admin.register(CustomUser): Registers CustomUser with this admin class in Django admin site.

Standalone functions:
- None.

## How it fits together

Request/data flow:
1. URL resolution maps incoming users routes in urls.py to class-based views in views.py.
2. Views validate input using serializers.py classes.
3. Serializer create logic (RegisterSerializer.create) writes to the CustomUser model in models.py via get_user_model().
4. Views serialize user output through UserSerializer and return API responses.
5. Authentication token creation/retrieval uses rest_framework.authtoken.models.Token.

View -> Serializer mapping:
- RegisterView uses RegisterSerializer for input validation/creation and UserSerializer for response payload.
- LoginView uses LoginSerializer for input validation and UserSerializer for response payload.
- ProfileView uses UserSerializer as serializer_class for retrieve/update operations.

Serializer -> Model mapping:
- UserSerializer targets User (active auth user model; in this project it resolves to CustomUser).
- RegisterSerializer targets User and calls User.objects.create_user.
- LoginSerializer is non-model and validates raw credential fields only.

Cross-file dependencies:
- views.py imports RegisterSerializer, LoginSerializer, and UserSerializer from serializers.py.
- admin.py imports CustomUser from models.py and registers it with CustomUserAdmin.
- serializers.py and views.py both use get_user_model(), coupling runtime behavior to AUTH_USER_MODEL.
- models.py exports compatibility alias User = CustomUser, supporting legacy imports.

Notable project/app dependencies visible from imports:
- django.contrib.auth (AbstractUser, authenticate, get_user_model, UserAdmin).
- rest_framework (APIView, RetrieveUpdateAPIView, serializers, permissions, Response, status).
- rest_framework.authtoken Token model for token-based auth.
- No direct imports from other local apps (recipes, questionnaire, subscriptions) were found in users app files.
