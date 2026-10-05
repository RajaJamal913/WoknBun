from django.conf import settings
from rest_framework import permissions

POS_ROLES = ("cashier", "kitchen", "manager", "admin")
CASHIER_ROLES = ("cashier", "manager", "admin")
MANAGER_ROLES = ("manager", "admin")


def staff_role(user):
    """The user's POS role, or None if they aren't POS staff at all."""
    if not user or not user.is_authenticated:
        return None
    if user.is_superuser:
        return "admin"
    profile = getattr(user, "staff_profile", None)  # None if no profile exists
    return profile.role if profile else None


def is_manager(user):
    return staff_role(user) in MANAGER_ROLES


class IsPOSStaff(permissions.BasePermission):
    """Any staff member with a StaffProfile (cashier, kitchen, manager, admin)."""
    message = "This account is not set up as POS staff."

    def has_permission(self, request, view):
        return staff_role(request.user) in POS_ROLES


class IsCashierOrAbove(permissions.BasePermission):
    """Can take money: cashier, manager, admin (not kitchen)."""
    message = "Your role is not allowed to do this."

    def has_permission(self, request, view):
        return staff_role(request.user) in CASHIER_ROLES


class IsManager(permissions.BasePermission):
    message = "A manager is required for this action."

    def has_permission(self, request, view):
        return staff_role(request.user) in MANAGER_ROLES


class CanRefund(permissions.BasePermission):
    message = "Your role is not allowed to issue refunds."

    def has_permission(self, request, view):
        return staff_role(request.user) in settings.POS_REFUND_ROLES


def _role_in(setting_name, default):
    return lambda user: staff_role(user) in getattr(settings, setting_name, default)


# Who may open the dashboard / the detailed reports. Override in settings.py:
#   POS_DASHBOARD_ROLES = ("cashier", "kitchen", "manager", "admin")   # default: all staff
#   POS_REPORT_ROLES    = ("manager", "admin")                         # default: managers
can_view_dashboard = _role_in("POS_DASHBOARD_ROLES", POS_ROLES)
can_view_reports = _role_in("POS_REPORT_ROLES", MANAGER_ROLES)
can_take_orders = lambda user: staff_role(user) in CASHIER_ROLES


class CanViewDashboard(permissions.BasePermission):
    message = "Your role is not allowed to view the dashboard."

    def has_permission(self, request, view):
        return can_view_dashboard(request.user)


class CanViewReports(permissions.BasePermission):
    message = "Your role is not allowed to view reports."

    def has_permission(self, request, view):
        return can_view_reports(request.user)


def owns_shift(user, shift):
    """A cashier may act only on their own shift; managers on any."""
    return is_manager(user) or shift.cashier_id == user.id