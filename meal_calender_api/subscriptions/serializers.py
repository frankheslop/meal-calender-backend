from rest_framework import serializers

from .models import AccessGrant, SubscriptionPlan


class SubscriptionPlanSerializer(serializers.ModelSerializer):
    class Meta:
        model = SubscriptionPlan
        fields = (
            "code",
            "display_name",
            "amount_cents",
            "currency",
            "billing_interval",
            "trial_days",
        )


class CheckoutSessionCreateSerializer(serializers.Serializer):
    plan_code = serializers.CharField(max_length=50)
    success_url = serializers.URLField()
    cancel_url = serializers.URLField()


class PortalSessionCreateSerializer(serializers.Serializer):
    return_url = serializers.URLField()


class SubscriptionStatusSerializer(serializers.Serializer):
    entitlement_active = serializers.BooleanField()
    status = serializers.CharField()
    reason_code = serializers.CharField(allow_null=True)
    plan_code = serializers.CharField(allow_null=True)
    trial_end_at = serializers.DateTimeField(allow_null=True)
    grace_end_at = serializers.DateTimeField(allow_null=True)
    grandfather_end_at = serializers.DateTimeField(allow_null=True)
    current_period_end_at = serializers.DateTimeField(allow_null=True)
    access_expires_at = serializers.DateTimeField(allow_null=True)
    next_action = serializers.DictField()


class AdminAccessGrantCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = AccessGrant
        fields = ("user", "source", "starts_at", "ends_at", "reason")

    def validate(self, attrs):
        starts_at = attrs["starts_at"]
        ends_at = attrs["ends_at"]
        if ends_at <= starts_at:
            raise serializers.ValidationError({"ends_at": "ends_at must be after starts_at"})
        return attrs
