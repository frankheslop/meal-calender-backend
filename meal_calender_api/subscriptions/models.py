from django.conf import settings
from django.db import models


class SubscriptionPlan(models.Model):
	class BillingInterval(models.TextChoices):
		MONTH = "month", "Monthly"
		YEAR = "year", "Yearly"

	code = models.CharField(max_length=50, unique=True)
	display_name = models.CharField(max_length=120)
	stripe_price_id = models.CharField(max_length=120, unique=True)
	billing_interval = models.CharField(max_length=10, choices=BillingInterval.choices)
	amount_cents = models.PositiveIntegerField()
	currency = models.CharField(max_length=10, default="USD")
	trial_days = models.PositiveSmallIntegerField(default=14)
	is_active = models.BooleanField(default=True)
	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)

	class Meta:
		ordering = ["amount_cents"]

	def __str__(self) -> str:
		return f"{self.display_name} ({self.billing_interval})"


class SubscriptionAccount(models.Model):
	class Status(models.TextChoices):
		PENDING = "pending", "Pending"
		TRIALING = "trialing", "Trialing"
		ACTIVE = "active", "Active"
		PAST_DUE = "past_due", "Past Due"
		CANCELED = "canceled", "Canceled"
		EXPIRED = "expired", "Expired"
		GRANDFATHERED = "grandfathered", "Grandfathered"

	user = models.OneToOneField(
		settings.AUTH_USER_MODEL,
		on_delete=models.CASCADE,
		related_name="subscription_account",
	)
	plan = models.ForeignKey(
		SubscriptionPlan,
		on_delete=models.SET_NULL,
		null=True,
		blank=True,
		related_name="accounts",
	)
	status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
	stripe_customer_id = models.CharField(max_length=120, blank=True, unique=True, null=True)
	stripe_subscription_id = models.CharField(max_length=120, blank=True, unique=True, null=True)
	trial_start_at = models.DateTimeField(null=True, blank=True)
	trial_end_at = models.DateTimeField(null=True, blank=True)
	current_period_start_at = models.DateTimeField(null=True, blank=True)
	current_period_end_at = models.DateTimeField(null=True, blank=True)
	last_payment_at = models.DateTimeField(null=True, blank=True)
	grace_end_at = models.DateTimeField(null=True, blank=True)
	grandfather_end_at = models.DateTimeField(null=True, blank=True)
	access_expires_at = models.DateTimeField(null=True, blank=True)
	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)

	def __str__(self) -> str:
		return f"SubscriptionAccount(user_id={self.user_id}, status={self.status})"


class PaymentRecord(models.Model):
	class Status(models.TextChoices):
		PAID = "paid", "Paid"
		FAILED = "failed", "Failed"
		REFUNDED = "refunded", "Refunded"

	account = models.ForeignKey(
		SubscriptionAccount,
		on_delete=models.CASCADE,
		related_name="payments",
	)
	stripe_invoice_id = models.CharField(max_length=120, blank=True, unique=True, null=True)
	stripe_payment_intent_id = models.CharField(max_length=120, blank=True, unique=True, null=True)
	amount_cents = models.PositiveIntegerField(default=0)
	currency = models.CharField(max_length=10, default="USD")
	status = models.CharField(max_length=20, choices=Status.choices)
	paid_at = models.DateTimeField(null=True, blank=True)
	raw_payload = models.JSONField(default=dict)
	created_at = models.DateTimeField(auto_now_add=True)

	class Meta:
		ordering = ["-created_at"]


class SubscriptionEvent(models.Model):
	stripe_event_id = models.CharField(max_length=120, unique=True)
	event_type = models.CharField(max_length=120)
	account = models.ForeignKey(
		SubscriptionAccount,
		on_delete=models.SET_NULL,
		null=True,
		blank=True,
		related_name="events",
	)
	processed = models.BooleanField(default=False)
	processed_at = models.DateTimeField(null=True, blank=True)
	processing_error = models.TextField(blank=True)
	payload = models.JSONField(default=dict)
	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)

	class Meta:
		ordering = ["-created_at"]


class AccessGrant(models.Model):
	class Source(models.TextChoices):
		TRIAL_EXTENSION = "trial_extension", "Trial Extension"
		SUPPORT_COMP = "support_comp", "Support Complimentary"
		MIGRATION_GRANDFATHER = "migration_grandfather", "Migration Grandfather"

	user = models.ForeignKey(
		settings.AUTH_USER_MODEL,
		on_delete=models.CASCADE,
		related_name="subscription_access_grants",
	)
	source = models.CharField(max_length=40, choices=Source.choices)
	starts_at = models.DateTimeField()
	ends_at = models.DateTimeField()
	granted_by = models.ForeignKey(
		settings.AUTH_USER_MODEL,
		on_delete=models.SET_NULL,
		null=True,
		blank=True,
		related_name="granted_subscription_accesses",
	)
	reason = models.TextField(blank=True)
	is_active = models.BooleanField(default=True)
	created_at = models.DateTimeField(auto_now_add=True)

	class Meta:
		ordering = ["-ends_at"]

	def __str__(self) -> str:
		return f"AccessGrant(user_id={self.user_id}, source={self.source}, ends_at={self.ends_at})"
