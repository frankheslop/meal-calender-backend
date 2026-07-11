# Subscriptions Next Steps

## Immediate Priorities

1. Apply DB migration
- Run migrations in each environment so the new subscription tables exist.
- Command target:
- `python manage.py migrate`

2. Seed initial plans
- Create two `SubscriptionPlan` rows:
- Monthly: `$9.99` (`amount_cents=999`, `billing_interval=month`)
- Yearly: `$99.00` (`amount_cents=9900`, `billing_interval=year`)
- Populate real `stripe_price_id` values from Stripe dashboard.

3. Configure environment settings
- Ensure these settings are present:
- `STRIPE_SECRET_KEY`
- `STRIPE_WEBHOOK_SECRET`
- `SUBSCRIPTIONS_GRACE_DAYS=7`

4. Wire webhook endpoint in Stripe
- Configure endpoint URL to `/api/subscriptions/webhooks/stripe/`.
- Subscribe at minimum to:
- `checkout.session.completed`
- `customer.subscription.updated`
- `customer.subscription.deleted`
- `invoice.paid`
- `invoice.payment_failed`

## Validation Checklist

1. API smoke tests
- `GET /api/subscriptions/plans/` returns active plans.
- `POST /api/subscriptions/checkout-session/` returns checkout URL.
- `GET /api/subscriptions/status/` returns valid snapshot payload.

2. Webhook flow tests
- Replay Stripe test events and verify:
- `SubscriptionEvent` deduplicates by `stripe_event_id`.
- `PaymentRecord` rows are created for paid/failed invoices.
- `SubscriptionAccount.status` transitions correctly.

3. Access gate tests
- When entitlement inactive, recipes endpoints return HTTP 402 with reason code payload.
- When entitlement active/trialing/grace/grandfather/manual grant is valid, recipes endpoints are accessible.

## Gaps To Implement Next

1. URL allowlist validation
- Restrict `success_url`, `cancel_url`, and `return_url` to approved frontend origins.

2. Account lifecycle helpers
- Add management command to backfill `SubscriptionAccount` for existing users.
- Add management command to apply 30-day grandfather window for existing users.

3. Observability and reliability
- Add structured logging fields for webhook processing outcomes.
- Add scheduled reconciliation job to compare local subscription state against Stripe.

4. Tests (currently missing)
- Unit tests for entitlement matrix in `compute_entitlement_snapshot`.
- Unit tests for webhook idempotency and handler transitions.
- Integration tests for recipes HTTP 402 gate behavior.

## Suggested Work Order

1. Migration + plan seeding + env setup.
2. Stripe webhook setup and event verification in local/staging.
3. Add URL allowlist and management commands.
4. Add automated test suite for subscriptions and recipe gating.
5. Add reconciliation/monitoring before production rollout.

## Files To Touch Next

- `subscriptions/management/commands/seed_subscription_plans.py`
- `subscriptions/management/commands/backfill_subscription_accounts.py`
- `subscriptions/management/commands/grandfather_existing_users.py`
- `subscriptions/tests.py`
- `subscriptions/services.py`
- `subscriptions/views.py`
- `recipes/views.py`
