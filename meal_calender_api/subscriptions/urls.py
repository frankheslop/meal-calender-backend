from django.urls import path

from .views import (
    AdminAccessGrantCreateView,
    CreateCheckoutSessionView,
    CreatePortalSessionView,
    StripeWebhookView,
    SubscriptionPlanListView,
    SubscriptionStatusView,
)

app_name = "subscriptions"

urlpatterns = [
    path("plans/", SubscriptionPlanListView.as_view(), name="plans"),
    path("checkout-session/", CreateCheckoutSessionView.as_view(), name="checkout-session"),
    path("portal-session/", CreatePortalSessionView.as_view(), name="portal-session"),
    path("status/", SubscriptionStatusView.as_view(), name="status"),
    path("webhooks/stripe/", StripeWebhookView.as_view(), name="stripe-webhook"),
    path("admin/grants/", AdminAccessGrantCreateView.as_view(), name="admin-grants"),
]
