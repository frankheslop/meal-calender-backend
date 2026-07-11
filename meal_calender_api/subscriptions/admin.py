from django.contrib import admin

from .models import AccessGrant, PaymentRecord, SubscriptionAccount, SubscriptionEvent, SubscriptionPlan


@admin.register(SubscriptionPlan)
class SubscriptionPlanAdmin(admin.ModelAdmin):
	list_display = ("code", "display_name", "billing_interval", "amount_cents", "currency", "is_active")
	list_filter = ("billing_interval", "is_active")
	search_fields = ("code", "display_name", "stripe_price_id")


@admin.register(SubscriptionAccount)
class SubscriptionAccountAdmin(admin.ModelAdmin):
	list_display = (
		"user",
		"status",
		"plan",
		"stripe_customer_id",
		"stripe_subscription_id",
		"current_period_end_at",
		"grandfather_end_at",
	)
	list_filter = ("status",)
	search_fields = ("user__username", "user__email", "stripe_customer_id", "stripe_subscription_id")


@admin.register(PaymentRecord)
class PaymentRecordAdmin(admin.ModelAdmin):
	list_display = ("account", "status", "amount_cents", "currency", "paid_at", "created_at")
	list_filter = ("status", "currency")
	search_fields = ("stripe_invoice_id", "stripe_payment_intent_id", "account__user__email")


@admin.register(SubscriptionEvent)
class SubscriptionEventAdmin(admin.ModelAdmin):
	list_display = ("stripe_event_id", "event_type", "processed", "processed_at", "created_at")
	list_filter = ("processed", "event_type")
	search_fields = ("stripe_event_id",)


@admin.register(AccessGrant)
class AccessGrantAdmin(admin.ModelAdmin):
	list_display = ("user", "source", "starts_at", "ends_at", "is_active", "granted_by")
	list_filter = ("source", "is_active")
	search_fields = ("user__username", "user__email", "reason")
