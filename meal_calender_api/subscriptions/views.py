from django.conf import settings
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAdminUser, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import SubscriptionPlan
from .serializers import (
    AdminAccessGrantCreateSerializer,
    CheckoutSessionCreateSerializer,
    PortalSessionCreateSerializer,
    SubscriptionPlanSerializer,
    SubscriptionStatusSerializer,
)
from .services import (
    SubscriptionServiceError,
    compute_entitlement_snapshot,
    create_checkout_session,
    create_portal_session,
    process_webhook_event,
)


class SubscriptionPlanListView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        plans = SubscriptionPlan.objects.filter(is_active=True).order_by("amount_cents")
        serializer = SubscriptionPlanSerializer(plans, many=True)
        return Response({"plans": serializer.data}, status=status.HTTP_200_OK)


class CreateCheckoutSessionView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = CheckoutSessionCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        plan_code = serializer.validated_data["plan_code"]
        success_url = serializer.validated_data["success_url"]
        cancel_url = serializer.validated_data["cancel_url"]

        try:
            plan = SubscriptionPlan.objects.get(code=plan_code, is_active=True)
        except SubscriptionPlan.DoesNotExist:
            return Response(
                {"code": "invalid_plan", "message": "Invalid or inactive plan"}, status=400
            )

        try:
            checkout_session = create_checkout_session(request.user, plan, success_url, cancel_url)
        except SubscriptionServiceError as exc:
            return Response({"code": "stripe_unavailable", "message": str(exc)}, status=503)

        return Response(
            {
                "checkout_url": checkout_session.get("url"),
                "session_id": checkout_session.get("id"),
                "expires_at": checkout_session.get("expires_at"),
            },
            status=status.HTTP_201_CREATED,
        )


class CreatePortalSessionView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = PortalSessionCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            portal_session = create_portal_session(
                request.user,
                serializer.validated_data["return_url"],
            )
        except SubscriptionServiceError as exc:
            return Response({"code": "portal_unavailable", "message": str(exc)}, status=400)

        return Response({"portal_url": portal_session.get("url")}, status=status.HTTP_201_CREATED)


class SubscriptionStatusView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        snapshot = compute_entitlement_snapshot(request.user)
        serializer = SubscriptionStatusSerializer(snapshot)
        return Response(serializer.data, status=status.HTTP_200_OK)


class StripeWebhookView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        payload = request.body
        sig_header = request.headers.get("Stripe-Signature")

        if not sig_header:
            return Response(
                {"code": "missing_signature", "message": "Missing Stripe-Signature"}, status=400
            )

        if not settings.STRIPE_WEBHOOK_SECRET:
            return Response(
                {"code": "webhook_not_configured", "message": "Webhook secret is not configured"},
                status=503,
            )

        try:
            import stripe
        except ImportError:
            return Response(
                {"code": "stripe_unavailable", "message": "stripe package is not installed"},
                status=503,
            )

        try:
            event = stripe.Webhook.construct_event(
                payload=payload, sig_header=sig_header, secret=settings.STRIPE_WEBHOOK_SECRET
            )
        except ValueError:
            return Response({"code": "invalid_payload", "message": "Invalid payload"}, status=400)
        except stripe.error.SignatureVerificationError:
            return Response(
                {"code": "invalid_signature", "message": "Invalid signature"}, status=400
            )

        process_webhook_event(event)
        return Response({"ok": True}, status=status.HTTP_200_OK)


class AdminAccessGrantCreateView(APIView):
    permission_classes = [IsAdminUser]

    def post(self, request):
        serializer = AdminAccessGrantCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        grant = serializer.save(granted_by=request.user)
        return Response(
            {
                "grant_id": grant.id,
                "user_id": grant.user_id,
                "source": grant.source,
                "starts_at": grant.starts_at,
                "ends_at": grant.ends_at,
                "created_at": grant.created_at,
            },
            status=status.HTTP_201_CREATED,
        )
