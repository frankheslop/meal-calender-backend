import logging
from datetime import datetime, timedelta
from datetime import timezone as dt_timezone
from typing import Any

from django.conf import settings
from django.contrib.auth import get_user_model
from django.utils import timezone

from .models import (
    AccessGrant,
    PaymentRecord,
    SubscriptionAccount,
    SubscriptionEvent,
    SubscriptionPlan,
)

logger = logging.getLogger(__name__)
User = get_user_model()


class SubscriptionServiceError(Exception):
    pass


def _get_stripe_module():
    try:
        import stripe

        stripe.api_key = settings.STRIPE_SECRET_KEY
        return stripe
    except ImportError as exc:
        raise SubscriptionServiceError("stripe package is not installed") from exc


def get_or_create_subscription_account(user):
    account, _ = SubscriptionAccount.objects.get_or_create(user=user)
    return account


def get_active_manual_grant(user, now=None):
    now = now or timezone.now()
    return (
        AccessGrant.objects.filter(user=user, is_active=True, starts_at__lte=now, ends_at__gte=now)
        .order_by("-ends_at")
        .first()
    )


def compute_entitlement_snapshot(user) -> dict[str, Any]:
    now = timezone.now()
    account = get_or_create_subscription_account(user)

    active_grant = get_active_manual_grant(user, now=now)
    if active_grant:
        return {
            "entitlement_active": True,
            "status": account.status,
            "reason_code": None,
            "plan_code": account.plan.code if account.plan else None,
            "trial_end_at": account.trial_end_at,
            "grace_end_at": account.grace_end_at,
            "grandfather_end_at": account.grandfather_end_at,
            "current_period_end_at": account.current_period_end_at,
            "access_expires_at": active_grant.ends_at,
            "next_action": {"type": "none", "endpoint": None},
        }

    if account.status in [SubscriptionAccount.Status.TRIALING, SubscriptionAccount.Status.ACTIVE]:
        return {
            "entitlement_active": True,
            "status": account.status,
            "reason_code": None,
            "plan_code": account.plan.code if account.plan else None,
            "trial_end_at": account.trial_end_at,
            "grace_end_at": account.grace_end_at,
            "grandfather_end_at": account.grandfather_end_at,
            "current_period_end_at": account.current_period_end_at,
            "access_expires_at": account.access_expires_at,
            "next_action": {"type": "none", "endpoint": None},
        }

    if (
        account.status == SubscriptionAccount.Status.PAST_DUE
        and account.grace_end_at
        and account.grace_end_at >= now
    ):
        return {
            "entitlement_active": True,
            "status": account.status,
            "reason_code": None,
            "plan_code": account.plan.code if account.plan else None,
            "trial_end_at": account.trial_end_at,
            "grace_end_at": account.grace_end_at,
            "grandfather_end_at": account.grandfather_end_at,
            "current_period_end_at": account.current_period_end_at,
            "access_expires_at": account.grace_end_at,
            "next_action": {"type": "portal", "endpoint": "/api/subscriptions/portal-session/"},
        }

    if account.grandfather_end_at and account.grandfather_end_at >= now:
        return {
            "entitlement_active": True,
            "status": SubscriptionAccount.Status.GRANDFATHERED,
            "reason_code": None,
            "plan_code": account.plan.code if account.plan else None,
            "trial_end_at": account.trial_end_at,
            "grace_end_at": account.grace_end_at,
            "grandfather_end_at": account.grandfather_end_at,
            "current_period_end_at": account.current_period_end_at,
            "access_expires_at": account.grandfather_end_at,
            "next_action": {"type": "checkout", "endpoint": "/api/subscriptions/checkout-session/"},
        }

    reason_code = "subscription_required"
    if account.status == SubscriptionAccount.Status.PAST_DUE:
        reason_code = "grace_expired"
    elif account.status == SubscriptionAccount.Status.EXPIRED:
        reason_code = "subscription_expired"
    elif account.status == SubscriptionAccount.Status.CANCELED:
        reason_code = "subscription_canceled"

    return {
        "entitlement_active": False,
        "status": account.status,
        "reason_code": reason_code,
        "plan_code": account.plan.code if account.plan else None,
        "trial_end_at": account.trial_end_at,
        "grace_end_at": account.grace_end_at,
        "grandfather_end_at": account.grandfather_end_at,
        "current_period_end_at": account.current_period_end_at,
        "access_expires_at": account.access_expires_at,
        "next_action": {"type": "checkout", "endpoint": "/api/subscriptions/checkout-session/"},
    }


def ensure_customer(account):
    if account.stripe_customer_id:
        return account.stripe_customer_id

    stripe = _get_stripe_module()
    customer = stripe.Customer.create(
        email=account.user.email,
        name=account.user.username,
        metadata={"user_id": str(account.user_id)},
    )
    account.stripe_customer_id = customer["id"]
    account.save(update_fields=["stripe_customer_id", "updated_at"])
    return account.stripe_customer_id


def create_checkout_session(user, plan: SubscriptionPlan, success_url: str, cancel_url: str):
    account = get_or_create_subscription_account(user)
    customer_id = ensure_customer(account)
    stripe = _get_stripe_module()

    session = stripe.checkout.Session.create(
        mode="subscription",
        customer=customer_id,
        line_items=[{"price": plan.stripe_price_id, "quantity": 1}],
        success_url=success_url,
        cancel_url=cancel_url,
        metadata={"user_id": str(user.id), "plan_code": plan.code},
        subscription_data={"trial_period_days": plan.trial_days},
    )
    return session


def create_portal_session(user, return_url: str):
    account = get_or_create_subscription_account(user)
    if not account.stripe_customer_id:
        raise SubscriptionServiceError("No Stripe customer for user")

    stripe = _get_stripe_module()
    session = stripe.billing_portal.Session.create(
        customer=account.stripe_customer_id,
        return_url=return_url,
    )
    return session


def record_subscription_event(payload: dict[str, Any]) -> SubscriptionEvent:
    event_id = payload.get("id", "")
    event_type = payload.get("type", "unknown")
    event, _ = SubscriptionEvent.objects.get_or_create(
        stripe_event_id=event_id,
        defaults={"event_type": event_type, "payload": payload},
    )
    return event


def _sync_account_common_fields(account, stripe_subscription: dict[str, Any]):
    status = stripe_subscription.get("status")
    status_map = {
        "trialing": SubscriptionAccount.Status.TRIALING,
        "active": SubscriptionAccount.Status.ACTIVE,
        "past_due": SubscriptionAccount.Status.PAST_DUE,
        "canceled": SubscriptionAccount.Status.CANCELED,
        "unpaid": SubscriptionAccount.Status.EXPIRED,
        "incomplete_expired": SubscriptionAccount.Status.EXPIRED,
    }
    account.status = status_map.get(status, SubscriptionAccount.Status.PENDING)
    account.stripe_subscription_id = (
        stripe_subscription.get("id", "") or account.stripe_subscription_id
    )

    trial_end = stripe_subscription.get("trial_end")
    current_period_end = stripe_subscription.get("current_period_end")

    account.trial_end_at = (
        datetime.fromtimestamp(trial_end, tz=dt_timezone.utc) if trial_end else None
    )
    account.current_period_end_at = (
        datetime.fromtimestamp(current_period_end, tz=dt_timezone.utc)
        if current_period_end
        else None
    )
    account.access_expires_at = account.current_period_end_at


def process_webhook_event(payload: dict[str, Any]):
    event = record_subscription_event(payload)
    if event.processed:
        return

    event_type = payload.get("type", "")
    data_object = payload.get("data", {}).get("object", {})

    try:
        if event_type == "checkout.session.completed":
            _handle_checkout_completed(data_object)
        elif event_type == "customer.subscription.updated":
            _handle_subscription_updated(data_object)
        elif event_type == "customer.subscription.deleted":
            _handle_subscription_deleted(data_object)
        elif event_type == "invoice.paid":
            _handle_invoice_paid(data_object)
        elif event_type == "invoice.payment_failed":
            _handle_invoice_payment_failed(data_object)

        event.processed = True
        event.processed_at = timezone.now()
        event.processing_error = ""
        event.save(update_fields=["processed", "processed_at", "processing_error", "updated_at"])
    except Exception as exc:
        logger.exception(
            "Failed to process Stripe event", extra={"event_id": event.stripe_event_id}
        )
        event.processing_error = str(exc)
        event.save(update_fields=["processing_error", "updated_at"])
        raise


def _get_user_from_customer_id(stripe_customer_id):
    account = (
        SubscriptionAccount.objects.filter(stripe_customer_id=stripe_customer_id)
        .select_related("user")
        .first()
    )
    if not account:
        return None, None
    return account.user, account


def _handle_checkout_completed(session_obj: dict[str, Any]):
    user_id = (session_obj.get("metadata") or {}).get("user_id")
    customer_id = session_obj.get("customer")

    account = None
    if user_id:
        account = SubscriptionAccount.objects.filter(user_id=user_id).first()

    if not account and customer_id:
        _, account = _get_user_from_customer_id(customer_id)

    if not account:
        return

    account.stripe_customer_id = customer_id or account.stripe_customer_id
    subscription_id = session_obj.get("subscription")
    if subscription_id:
        account.stripe_subscription_id = subscription_id
    account.save(update_fields=["stripe_customer_id", "stripe_subscription_id", "updated_at"])


def _handle_subscription_updated(subscription_obj: dict[str, Any]):
    customer_id = subscription_obj.get("customer")
    _, account = _get_user_from_customer_id(customer_id)
    if not account:
        return

    _sync_account_common_fields(account, subscription_obj)
    account.save(
        update_fields=[
            "status",
            "stripe_subscription_id",
            "trial_end_at",
            "current_period_end_at",
            "access_expires_at",
            "updated_at",
        ]
    )


def _handle_subscription_deleted(subscription_obj: dict[str, Any]):
    customer_id = subscription_obj.get("customer")
    _, account = _get_user_from_customer_id(customer_id)
    if not account:
        return

    account.status = SubscriptionAccount.Status.CANCELED
    ended_at = subscription_obj.get("ended_at")
    if ended_at:
        account.access_expires_at = datetime.fromtimestamp(ended_at, tz=dt_timezone.utc)
    account.save(update_fields=["status", "access_expires_at", "updated_at"])


def _handle_invoice_paid(invoice_obj: dict[str, Any]):
    customer_id = invoice_obj.get("customer")
    _, account = _get_user_from_customer_id(customer_id)
    if not account:
        return

    paid_at_ts = invoice_obj.get("status_transitions", {}).get("paid_at") or invoice_obj.get(
        "created"
    )
    paid_at = (
        datetime.fromtimestamp(paid_at_ts, tz=dt_timezone.utc) if paid_at_ts else timezone.now()
    )

    PaymentRecord.objects.get_or_create(
        stripe_invoice_id=invoice_obj.get("id"),
        defaults={
            "account": account,
            "stripe_payment_intent_id": invoice_obj.get("payment_intent"),
            "amount_cents": invoice_obj.get("amount_paid", 0),
            "currency": (invoice_obj.get("currency") or "usd").upper(),
            "status": PaymentRecord.Status.PAID,
            "paid_at": paid_at,
            "raw_payload": invoice_obj,
        },
    )

    account.last_payment_at = paid_at
    account.status = SubscriptionAccount.Status.ACTIVE
    account.grace_end_at = None
    account.access_expires_at = account.current_period_end_at or (paid_at + timedelta(days=30))
    account.save(
        update_fields=[
            "last_payment_at",
            "status",
            "grace_end_at",
            "access_expires_at",
            "updated_at",
        ]
    )


def _handle_invoice_payment_failed(invoice_obj: dict[str, Any]):
    customer_id = invoice_obj.get("customer")
    _, account = _get_user_from_customer_id(customer_id)
    if not account:
        return

    PaymentRecord.objects.get_or_create(
        stripe_invoice_id=invoice_obj.get("id"),
        defaults={
            "account": account,
            "stripe_payment_intent_id": invoice_obj.get("payment_intent"),
            "amount_cents": invoice_obj.get("amount_due", 0),
            "currency": (invoice_obj.get("currency") or "usd").upper(),
            "status": PaymentRecord.Status.FAILED,
            "paid_at": None,
            "raw_payload": invoice_obj,
        },
    )

    account.status = SubscriptionAccount.Status.PAST_DUE
    account.grace_end_at = timezone.now() + timedelta(days=settings.SUBSCRIPTIONS_GRACE_DAYS)
    account.save(update_fields=["status", "grace_end_at", "updated_at"])


def get_blocked_recipe_payload(user):
    snapshot = compute_entitlement_snapshot(user)
    if snapshot["entitlement_active"]:
        return None

    code = snapshot["reason_code"] or "subscription_required"
    next_action_type = snapshot.get("next_action", {}).get("type", "checkout")
    next_action_endpoint = snapshot.get("next_action", {}).get(
        "endpoint", "/api/subscriptions/checkout-session/"
    )
    message_map = {
        "subscription_required": "An active subscription is required to access recipe features.",
        "subscription_expired": "Your subscription is expired. Renew to continue using recipe features.",
        "subscription_canceled": "Your subscription is canceled. Renew to continue using recipe features.",
        "grace_expired": "Payment grace period has expired. Update billing to regain access.",
    }

    return {
        "code": code,
        "message": message_map.get(code, "Subscription is required for recipe access."),
        "subscription_status": snapshot["status"],
        "next_action": {
            "type": next_action_type,
            "endpoint": next_action_endpoint,
        },
    }
