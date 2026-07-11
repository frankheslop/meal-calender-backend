from rest_framework.permissions import BasePermission

from .services import compute_entitlement_snapshot


class HasActiveSubscription(BasePermission):
    message = "Active subscription required"

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False

        snapshot = compute_entitlement_snapshot(request.user)
        return snapshot["entitlement_active"]
