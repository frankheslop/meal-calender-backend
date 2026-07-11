# Subscriptions App Context

## models.py

- File path: `models.py`
- Summary: Defines the billing and entitlement data model for subscriptions, payments, webhook event tracking, and manual access overrides. This app is the source of truth for whether a user should have paid access.

### Class: SubscriptionPlan

- Inherits from: `django.db.models.Model`
- Purpose: Stores available sellable plans and Stripe price mapping.
- Fields/methods:
- `BillingInterval (TextChoices)`: `month` and `year` plan cadence.
- `code (CharField, unique)`: Internal stable plan identifier (e.g., monthly/yearly).
- `display_name (CharField)`: Human-friendly plan label.
- `stripe_price_id (CharField, unique)`: Stripe Price ID used for checkout.
- `billing_interval (CharField)`: Selected cadence from `BillingInterval`.
- `amount_cents (PositiveIntegerField)`: Plan amount in minor currency units.
- `currency (CharField, default="USD")`: Currency code.
- `trial_days (PositiveSmallIntegerField, default=14)`: Trial length used at checkout creation.
- `is_active (BooleanField, default=True)`: Controls whether plan is selectable.
- `created_at`, `updated_at`: Audit timestamps.
- `Meta.ordering = ["amount_cents"]`: Sort plans by price.
- `__str__(self)`: Returns display name and interval.

### Class: SubscriptionAccount

- Inherits from: `django.db.models.Model`
- Purpose: One billing/entitlement aggregate record per user.
- Fields/methods:
- `Status (TextChoices)`: `pending`, `trialing`, `active`, `past_due`, `canceled`, `expired`, `grandfathered`.
- `user (OneToOneField -> AUTH_USER_MODEL)`: Enforces one subscription account per user.
- `plan (ForeignKey -> SubscriptionPlan, nullable)`: Current plan reference.
- `status (CharField)`: Current entitlement/billing state.
- `stripe_customer_id (CharField, unique nullable)`: Stripe customer identifier.
- `stripe_subscription_id (CharField, unique nullable)`: Stripe subscription identifier.
- `trial_start_at`, `trial_end_at`: Trial window timestamps.
- `current_period_start_at`, `current_period_end_at`: Stripe billing period boundaries.
- `last_payment_at`: Most recent successful payment timestamp.
- `grace_end_at`: End of post-failure grace period.
- `grandfather_end_at`: End of migration grandfather window.
- `access_expires_at`: Materialized entitlement expiry boundary.
- `created_at`, `updated_at`: Audit timestamps.
- `__str__(self)`: Returns user and status summary.

### Class: PaymentRecord

- Inherits from: `django.db.models.Model`
- Purpose: Immutable-like payment outcome ledger for invoices/payment intents.
- Fields/methods:
- `Status (TextChoices)`: `paid`, `failed`, `refunded`.
- `account (ForeignKey -> SubscriptionAccount)`: Owning subscription account.
- `stripe_invoice_id (CharField, unique nullable)`: Stripe invoice identifier.
- `stripe_payment_intent_id (CharField, unique nullable)`: Stripe payment intent identifier.
- `amount_cents`, `currency`: Payment amount and currency.
- `status`: Payment outcome.
- `paid_at`: Timestamp for successful payment (nullable for failed events).
- `raw_payload (JSONField)`: Stored Stripe object snapshot.
- `created_at`: Audit timestamp.
- `Meta.ordering = ["-created_at"]`: Newest records first.

### Class: SubscriptionEvent

- Inherits from: `django.db.models.Model`
- Purpose: Webhook event ledger + idempotency anchor for Stripe events.
- Fields/methods:
- `stripe_event_id (CharField, unique)`: External idempotency key.
- `event_type (CharField)`: Stripe event type string.
- `account (ForeignKey -> SubscriptionAccount, nullable)`: Optional linked account.
- `processed (BooleanField)`: Handler completion flag.
- `processed_at`: Processing completion timestamp.
- `processing_error (TextField)`: Last processing error if failed.
- `payload (JSONField)`: Raw event payload.
- `created_at`, `updated_at`: Audit timestamps.
- `Meta.ordering = ["-created_at"]`: Newest events first.

### Class: AccessGrant

- Inherits from: `django.db.models.Model`
- Purpose: Manual access override window (support/ops controlled).
- Fields/methods:
- `Source (TextChoices)`: `trial_extension`, `support_comp`, `migration_grandfather`.
- `user (ForeignKey -> AUTH_USER_MODEL)`: User receiving temporary access.
- `source (CharField)`: Grant reason category.
- `starts_at`, `ends_at`: Effective time window.
- `granted_by (ForeignKey -> AUTH_USER_MODEL, nullable)`: Staff actor reference.
- `reason (TextField)`: Optional human explanation.
- `is_active (BooleanField)`: Soft switch for grant validity.
- `created_at`: Audit timestamp.
- `Meta.ordering = ["-ends_at"]`: Most urgent/latest ending grants first.
- `__str__(self)`: Human summary.

- Standalone functions: None.
- Notable decorators: None.

## serializers.py

- File path: `serializers.py`
- Summary: Defines request/response validation for plan listing, checkout/portal session creation, status response shape, and admin grant creation.

### Class: SubscriptionPlanSerializer

- Inherits from: `rest_framework.serializers.ModelSerializer`
- Purpose: Serializes active plan metadata for frontend pricing/selection.
- Fields/methods:
- `Meta.model = SubscriptionPlan`
- `Meta.fields`: `code`, `display_name`, `amount_cents`, `currency`, `billing_interval`, `trial_days`.

### Class: CheckoutSessionCreateSerializer

- Inherits from: `rest_framework.serializers.Serializer`
- Purpose: Validates checkout session create payload.
- Fields/methods:
- `plan_code (CharField)`
- `success_url (URLField)`
- `cancel_url (URLField)`

### Class: PortalSessionCreateSerializer

- Inherits from: `rest_framework.serializers.Serializer`
- Purpose: Validates customer portal session create payload.
- Fields/methods:
- `return_url (URLField)`

### Class: SubscriptionStatusSerializer

- Inherits from: `rest_framework.serializers.Serializer`
- Purpose: Shapes entitlement snapshot response contract.
- Fields/methods:
- `entitlement_active (BooleanField)`
- `status (CharField)`
- `reason_code (CharField, nullable)`
- `plan_code (CharField, nullable)`
- `trial_end_at`, `grace_end_at`, `grandfather_end_at`, `current_period_end_at`, `access_expires_at` (DateTimeField, nullable)
- `next_action (DictField)`

### Class: AdminAccessGrantCreateSerializer

- Inherits from: `rest_framework.serializers.ModelSerializer`
- Purpose: Validates staff-created manual access grants.
- Fields/methods:
- `Meta.model = AccessGrant`
- `Meta.fields`: `user`, `source`, `starts_at`, `ends_at`, `reason`.
- ```python
  def validate(self, attrs)
  ```
  - Ensures `ends_at` is strictly after `starts_at`.
  - Side effects: none.

- Standalone functions: None.
- Notable decorators: None.

## views.py

- File path: `views.py`
- Summary: Implements subscriptions API endpoints for plan discovery, checkout/portal session creation, status retrieval, Stripe webhook ingestion, and admin grant creation.

### Class: SubscriptionPlanListView

- Inherits from: `rest_framework.views.APIView`
- Purpose: Returns active plans.
- Fields/methods:
- `permission_classes = [AllowAny]`
- ```python
  def get(self, request)
  ```
  - Queries active plans and serializes them.
  - Output: `{ "plans": [...] }`.
  - Side effects: DB read.

### Class: CreateCheckoutSessionView

- Inherits from: `rest_framework.views.APIView`
- Purpose: Creates Stripe hosted checkout session for authenticated user.
- Fields/methods:
- `permission_classes = [IsAuthenticated]`
- ```python
  def post(self, request)
  ```
  - Validates request payload.
  - Resolves active plan by code.
  - Calls `services.create_checkout_session`.
  - Returns checkout URL/session metadata.
  - Side effects: DB reads and Stripe API call.

### Class: CreatePortalSessionView

- Inherits from: `rest_framework.views.APIView`
- Purpose: Creates Stripe customer portal session.
- Fields/methods:
- `permission_classes = [IsAuthenticated]`
- ```python
  def post(self, request)
  ```
  - Validates return URL.
  - Calls `services.create_portal_session`.
  - Returns portal URL.
  - Side effects: Stripe API call, possible DB read.

### Class: SubscriptionStatusView

- Inherits from: `rest_framework.views.APIView`
- Purpose: Returns canonical entitlement snapshot for current user.
- Fields/methods:
- `permission_classes = [IsAuthenticated]`
- ```python
  def get(self, request)
  ```
  - Calls `compute_entitlement_snapshot` and serializes result.
  - Side effects: DB read.

### Class: StripeWebhookView

- Inherits from: `rest_framework.views.APIView`
- Purpose: Receives and verifies Stripe webhook events, then dispatches event processing.
- Fields/methods:
- `permission_classes = [AllowAny]`
- ```python
  def post(self, request)
  ```
  - Validates `Stripe-Signature` header and local webhook secret.
  - Verifies payload signature via `stripe.Webhook.construct_event`.
  - Calls `process_webhook_event` service handler.
  - Side effects: DB writes/updates via service layer; may call Stripe SDK validation.

### Class: AdminAccessGrantCreateView

- Inherits from: `rest_framework.views.APIView`
- Purpose: Creates manual access grant records for staff users.
- Fields/methods:
- `permission_classes = [IsAdminUser]`
- ```python
  def post(self, request)
  ```
  - Validates payload with `AdminAccessGrantCreateSerializer`.
  - Saves grant with `granted_by=request.user`.
  - Returns created grant metadata.
  - Side effects: DB write.

- Standalone functions: None.
- Notable decorators: None.

## urls.py

- File path: `urls.py`
- Summary: Declares subscriptions API routes.

### Module-level URL config

- `app_name = "subscriptions"`
- `urlpatterns`:
- `plans/` -> `SubscriptionPlanListView`
- `checkout-session/` -> `CreateCheckoutSessionView`
- `portal-session/` -> `CreatePortalSessionView`
- `status/` -> `SubscriptionStatusView`
- `webhooks/stripe/` -> `StripeWebhookView`
- `admin/grants/` -> `AdminAccessGrantCreateView`

- Classes: None.
- Standalone functions: None.
- Notable decorators: None.

## permissions.py

- File path: `permissions.py`
- Summary: Contains a reusable DRF permission that checks whether a user currently has active subscription entitlement.

### Class: HasActiveSubscription

- Inherits from: `rest_framework.permissions.BasePermission`
- Purpose: Central permission check for paid feature gates.
- Fields/methods:
- `message = "Active subscription required"`
- ```python
  def has_permission(self, request, view)
  ```
  - Rejects anonymous users.
  - Calls `compute_entitlement_snapshot(request.user)`.
  - Returns `snapshot["entitlement_active"]`.
  - Side effects: DB read via service call.

- Standalone functions: None.
- Notable decorators: None.

## services.py

- File path: `services.py`
- Summary: Encapsulates entitlement computation, Stripe session creation, webhook event persistence/dispatch, and recipe-gate payload composition.

### Class: SubscriptionServiceError

- Inherits from: `Exception`
- Purpose: Domain-specific service error for Stripe/config/runtime failures.

### Standalone function

```python
def _get_stripe_module():
```
- Imports Stripe SDK and sets API key from settings.
- Inputs: none.
- Outputs: `stripe` module.
- Side effects: sets global Stripe API key; raises `SubscriptionServiceError` if SDK missing.

### Standalone function

```python
def get_or_create_subscription_account(user):
```
- Ensures a `SubscriptionAccount` exists for user.
- Outputs: account model instance.
- Side effects: DB read/write (`get_or_create`).

### Standalone function

```python
def get_active_manual_grant(user, now=None):
```
- Returns currently active manual grant window for user.
- Outputs: latest matching `AccessGrant` or `None`.
- Side effects: DB read.

### Standalone function

```python
def compute_entitlement_snapshot(user) -> dict[str, Any]:
```
- Computes entitlement status snapshot based on account state, manual grants, grace, and grandfather windows.
- Outputs: dict used by status endpoint and gating logic.
- Side effects: DB read; may create account through helper.

### Standalone function

```python
def ensure_customer(account):
```
- Creates Stripe customer if missing and stores id on account.
- Outputs: `stripe_customer_id`.
- Side effects: Stripe API call + DB update.

### Standalone function

```python
def create_checkout_session(user, plan: SubscriptionPlan, success_url: str, cancel_url: str):
```
- Creates Stripe hosted checkout session in subscription mode.
- Inputs: authenticated user, plan model, success/cancel URLs.
- Outputs: Stripe Checkout Session object.
- Side effects: Stripe API call, possible customer creation, DB update.

### Standalone function

```python
def create_portal_session(user, return_url: str):
```
- Creates Stripe customer billing portal session.
- Outputs: Stripe portal session object.
- Side effects: Stripe API call; raises error if no customer exists.

### Standalone function

```python
def record_subscription_event(payload: dict[str, Any]) -> SubscriptionEvent:
```
- Upserts webhook event by Stripe event id for idempotency.
- Outputs: `SubscriptionEvent` model instance.
- Side effects: DB read/write.

### Standalone function

```python
def _sync_account_common_fields(account, stripe_subscription: dict[str, Any]):
```
- Maps Stripe subscription object into local account status/period fields.
- Side effects: mutates unsaved model instance fields.

### Standalone function

```python
def process_webhook_event(payload: dict[str, Any]):
```
- Dispatches supported webhook types and records processing status.
- Side effects: DB writes/updates; logs errors; can raise on handler failure.

### Standalone function

```python
def _get_user_from_customer_id(stripe_customer_id):
```
- Resolves local user/account from Stripe customer id.
- Outputs: `(user, account)` tuple or `(None, None)`.
- Side effects: DB read.

### Standalone function

```python
def _handle_checkout_completed(session_obj: dict[str, Any]):
```
- Links checkout customer/subscription identifiers to local account.
- Side effects: DB update.

### Standalone function

```python
def _handle_subscription_updated(subscription_obj: dict[str, Any]):
```
- Applies Stripe subscription state updates to local account.
- Side effects: DB update.

### Standalone function

```python
def _handle_subscription_deleted(subscription_obj: dict[str, Any]):
```
- Marks account canceled and sets access expiry when provided.
- Side effects: DB update.

### Standalone function

```python
def _handle_invoice_paid(invoice_obj: dict[str, Any]):
```
- Writes paid `PaymentRecord` and updates account to active.
- Side effects: DB write/update.

### Standalone function

```python
def _handle_invoice_payment_failed(invoice_obj: dict[str, Any]):
```
- Writes failed `PaymentRecord`, marks account `past_due`, and sets grace window.
- Side effects: DB write/update.

### Standalone function

```python
def get_blocked_recipe_payload(user):
```
- Builds standardized recipe-access denial payload when entitlement inactive.
- Outputs: `None` when allowed, otherwise payload dict containing `code`, `message`, `subscription_status`, and `next_action`.
- Side effects: DB read via entitlement snapshot.

- Notable decorators:
- None.

## admin.py

- File path: `admin.py`
- Summary: Registers billing/entitlement models with list/search filters for staff operations.

### Class: SubscriptionPlanAdmin

- Inherits from: `django.contrib.admin.ModelAdmin`
- Purpose: Manage plan catalog in admin.
- Fields and methods:
- `list_display`, `list_filter`, `search_fields` tuned for plan maintenance.
- Decorator: `@admin.register(SubscriptionPlan)`.

### Class: SubscriptionAccountAdmin

- Inherits from: `ModelAdmin`
- Purpose: Inspect user subscription state and Stripe linkage.
- Fields and methods:
- `list_display`, `list_filter`, `search_fields` for account operations.
- Decorator: `@admin.register(SubscriptionAccount)`.

### Class: PaymentRecordAdmin

- Inherits from: `ModelAdmin`
- Purpose: Inspect payment outcomes and amounts.
- Fields and methods: configured list/search/filter fields.
- Decorator: `@admin.register(PaymentRecord)`.

### Class: SubscriptionEventAdmin

- Inherits from: `ModelAdmin`
- Purpose: Inspect webhook processing status and event metadata.
- Fields and methods: configured list/search/filter fields.
- Decorator: `@admin.register(SubscriptionEvent)`.

### Class: AccessGrantAdmin

- Inherits from: `ModelAdmin`
- Purpose: Manage and audit manual access grants.
- Fields and methods: configured list/search/filter fields.
- Decorator: `@admin.register(AccessGrant)`.

## apps.py

- File path: `apps.py`
- Summary: App config for Django registration.

### Class: SubscriptionsConfig

- Inherits from: `django.apps.AppConfig`
- Purpose: Registers app identity.
- Fields/methods:
- `name = "subscriptions"`.

## __init__.py

- File path: `__init__.py`
- Summary: Package marker file for subscriptions app.

- Classes: None.
- Standalone functions: None.
- Notable decorators: None.

## How it fits together

- Request/data flow:
1. Frontend fetches plans via `GET /api/subscriptions/plans/`.
2. Authenticated user creates checkout session via `POST /api/subscriptions/checkout-session/`.
3. Stripe redirects through hosted flow; Stripe webhooks hit `POST /api/subscriptions/webhooks/stripe/`.
4. Webhook service persists/deduplicates events and updates `SubscriptionAccount`/`PaymentRecord` state.
5. Frontend and backend gates query `GET /api/subscriptions/status/` and/or `compute_entitlement_snapshot`.
6. Recipes app gating calls `get_blocked_recipe_payload` and returns HTTP 402 when entitlement is inactive.

- View -> Serializer mapping:
- `SubscriptionPlanListView` -> `SubscriptionPlanSerializer`.
- `CreateCheckoutSessionView` -> `CheckoutSessionCreateSerializer`.
- `CreatePortalSessionView` -> `PortalSessionCreateSerializer`.
- `SubscriptionStatusView` -> `SubscriptionStatusSerializer`.
- `AdminAccessGrantCreateView` -> `AdminAccessGrantCreateSerializer`.

- Serializer -> Model mapping:
- `SubscriptionPlanSerializer` -> `SubscriptionPlan`.
- `AdminAccessGrantCreateSerializer` -> `AccessGrant`.
- `CheckoutSessionCreateSerializer`/`PortalSessionCreateSerializer`/`SubscriptionStatusSerializer` are non-model serializers.

- Cross-file dependencies:
- `views.py` depends on `services.py` for core billing logic.
- `permissions.py` depends on `services.compute_entitlement_snapshot`.
- `admin.py` depends on all subscription models.
- `services.py` is depended on by this app’s views and by recipes app gate logic.

- Notable relationships to other apps:
- Model FKs/OneToOne use `settings.AUTH_USER_MODEL` (`users.CustomUser` in this project).
- Recipes app imports `get_blocked_recipe_payload` from this app to enforce paid access on recipe endpoints.
