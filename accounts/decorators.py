from functools import wraps

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect


def deny(request):
    messages.error(request, "You are not allowed to open that page.")
    return redirect("accounts:dashboard")


def role_required(role):
    """Only let users with this role open the view."""

    def decorator(view):
        @wraps(view)
        def wrapper(request, *args, **kwargs):
            if request.user.role != role:
                return deny(request)
            return view(request, *args, **kwargs)

        return login_required(wrapper)

    return decorator


def admin_required(view):
    """Only the superuser (admin) can open the view."""

    @wraps(view)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_superuser:
            return deny(request)
        return view(request, *args, **kwargs)

    return login_required(wrapper)


def court_staff_required(view):
    """Court staff who are linked to a court (CourtStaff row exists)."""

    @wraps(view)
    def wrapper(request, *args, **kwargs):
        user = request.user
        if user.role != "court_staff" or not hasattr(user, "staff"):
            return deny(request)
        return view(request, *args, **kwargs)

    return login_required(wrapper)
