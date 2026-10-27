from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from cases.models import Case, Hearing
from cases.models import CaseRequest

from ..models import Account, Lawyer


@login_required
def dashboard(request):
    user = request.user
    stats = []  # list of (label, number) shown at the top

    if user.is_superuser:
        stats = [
            ("Lawyers waiting for approval", Lawyer.objects.filter(account__is_verified=False).count()),
            ("Verified lawyers", Lawyer.objects.filter(account__is_verified=True).count()),
            ("Total cases", Case.objects.count()),
            ("Closed cases", Case.objects.filter(status=Case.CLOSED).count()),
        ]
    elif user.role == Account.COURT_STAFF and hasattr(user, "staff"):
        cases = Case.objects.filter(court=user.staff.court)
        stats = [
            ("Cases in my court", cases.count()),
            ("Waiting for consent", cases.filter(status=Case.REGISTERED).count()),
            ("Open for lawyers", cases.filter(status=Case.OPEN).count()),
            ("Closed", cases.filter(status=Case.CLOSED).count()),
        ]
    elif user.role == Account.CLIENT and hasattr(user, "client"):
        cases = user.client.cases
        stats = [
            ("My cases", cases.count()),
            ("Waiting for my consent", cases.filter(consent=False).count()),
            ("Requests to review", CaseRequest.objects.filter(case__client=user.client, status=CaseRequest.PENDING, case__status=Case.OPEN).count()),
            ("Closed", cases.filter(status=Case.CLOSED).count()),
        ]
    elif user.role == Account.LAWYER and hasattr(user, "lawyer"):
        lawyer = user.lawyer
        open_cases = Case.objects.filter(status=Case.OPEN).count() if user.is_verified else 0
        stats = [
            ("Open cases", open_cases),
            ("My pending requests", lawyer.requests.filter(status=CaseRequest.PENDING).count()),
            ("Running cases", lawyer.assigned_cases.filter(status=Case.ASSIGNED).count()),
            ("Closed", lawyer.assigned_cases.filter(status=Case.CLOSED).count()),
        ]

    context = {
        "stats": stats,
        "hearings": Hearing.upcoming_for(user)[:4],
        "notifications": user.notifications.all()[:5],
    }
    return render(request, "accounts/dashboard.html", context)


# ---------- lawyers ----------
