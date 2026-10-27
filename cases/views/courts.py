from django.contrib import messages
from django.db.models import Count, ProtectedError
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from accounts.decorators import admin_required, court_staff_required
from accounts.models import Account, Lawyer
from cases.models import Case, Hearing

from cases.forms import AreaForm, CourtForm, HolidayForm, StaffCreateForm, StaffEditForm
from cases.models import Area, Court, CourtHoliday, CourtStaff


# ---------- areas ----------

@admin_required
def area_list(request):
    areas = Area.objects.annotate(court_total=Count("courts"))
    return render(request, "cases/area_list.html", {"areas": areas})


@admin_required
def area_create(request):
    form = AreaForm(request.POST or None)
    if form.is_valid():
        form.save()
        messages.success(request, "Area added.")
        return redirect("cases:area_list")
    return render(request, "form_page.html", {"form": form, "title": "Add area", "cancel_url": "cases:area_list"})


@admin_required
def area_edit(request, pk):
    area = get_object_or_404(Area, pk=pk)
    form = AreaForm(request.POST or None, instance=area)
    if form.is_valid():
        form.save()
        messages.success(request, "Area updated.")
        return redirect("cases:area_list")
    return render(request, "form_page.html", {"form": form, "title": "Edit area", "cancel_url": "cases:area_list"})


@admin_required
def area_delete(request, pk):
    area = get_object_or_404(Area, pk=pk)
    if request.method == "POST":
        try:
            area.delete()
            messages.success(request, "Area deleted.")
        except ProtectedError:
            messages.error(request, "This area still has courts. Move or delete them first.")
        return redirect("cases:area_list")
    context = {"title": f"Delete area {area.name}?", "cancel_url": "cases:area_list"}
    return render(request, "confirm_delete.html", context)


# ---------- courts ----------

@admin_required
def court_list(request):
    courts = Court.objects.select_related("area").annotate(case_total=Count("cases", distinct=True), staff_total=Count("staff_members", distinct=True))
    return render(request, "cases/court_list.html", {"courts": courts})


@admin_required
def court_create(request):
    form = CourtForm(request.POST or None)
    if form.is_valid():
        form.save()
        messages.success(request, "Court added.")
        return redirect("cases:court_list")
    return render(request, "form_page.html", {"form": form, "title": "Add court", "cancel_url": "cases:court_list"})


@admin_required
def court_edit(request, pk):
    court = get_object_or_404(Court, pk=pk)
    form = CourtForm(request.POST or None, instance=court)
    if form.is_valid():
        form.save()
        messages.success(request, "Court updated.")
        return redirect("cases:court_list")
    return render(request, "form_page.html", {"form": form, "title": "Edit court", "cancel_url": "cases:court_list"})


@admin_required
def court_delete(request, pk):
    court = get_object_or_404(Court, pk=pk)
    if request.method == "POST":
        try:
            court.delete()
            messages.success(request, "Court deleted.")
        except ProtectedError:
            messages.error(request, "This court still has cases or staff, so it cannot be deleted.")
        return redirect("cases:court_list")
    context = {"title": f"Delete {court.name}?", "cancel_url": "cases:court_list"}
    return render(request, "confirm_delete.html", context)


# ---------- court staff ----------

@admin_required
def staff_list(request):
    staff = CourtStaff.objects.select_related("court", "account")
    return render(request, "cases/staff_list.html", {"staff": staff})


@admin_required
def staff_create(request):
    form = StaffCreateForm(request.POST or None)
    if form.is_valid():
        data = form.cleaned_data
        account = Account.objects.create_user(
            username=data["username"], email=data["email"], password=data["password"],
            role=Account.COURT_STAFF, is_verified=True,
        )
        CourtStaff.objects.create(
            account=account, court=data["court"], name=data["name"], designation=data["designation"],
        )
        messages.success(request, "Court staff account created.")
        return redirect("cases:staff_list")
    return render(request, "form_page.html", {"form": form, "title": "Add court staff", "cancel_url": "cases:staff_list"})


@admin_required
def staff_edit(request, pk):
    member = get_object_or_404(CourtStaff, pk=pk)
    form = StaffEditForm(request.POST or None, instance=member)
    if form.is_valid():
        form.save()
        messages.success(request, "Court staff updated.")
        return redirect("cases:staff_list")
    return render(request, "form_page.html", {"form": form, "title": "Edit court staff", "cancel_url": "cases:staff_list"})


@admin_required
def staff_delete(request, pk):
    member = get_object_or_404(CourtStaff, pk=pk)
    if request.method == "POST":
        member.account.delete()  # the CourtStaff row goes with it
        messages.success(request, "Court staff removed.")
        return redirect("cases:staff_list")
    context = {"title": f"Remove {member.name}?", "cancel_url": "cases:staff_list",
               "message": "The login account of this staff member will be deleted."}
    return render(request, "confirm_delete.html", context)


# ---------- report for court staff ----------

def count_bars(cases, choices, field):
    """Makes (label, count, percent) rows for the bars in the report."""
    total = cases.count() or 1
    rows = []
    for key, label in choices:
        count = cases.filter(**{field: key}).count()
        rows.append({"key": key, "label": label, "count": count, "percent": round(count * 100 / total)})
    return rows


@court_staff_required
def court_report(request):
    court = request.user.staff.court
    cases = Case.objects.filter(court=court)
    context = {
        "court": court,
        "total": cases.count(),
        "status_bars": count_bars(cases, Case.STATUS_CHOICES, "status"),
        "type_bars": count_bars(cases, Case.TYPE_CHOICES, "case_type"),
        "recent": cases.select_related("client")[:5],
        "hearings": Hearing.objects.filter(case__court=court, scheduled_at__gte=timezone.now()).select_related("case")[:5],
        "lawyers": Lawyer.objects.filter(assigned_cases__court=court).annotate(total=Count("assigned_cases")).order_by("-total")[:5],
    }
    return render(request, "cases/report.html", context)


# ---------- court holidays ----------

@court_staff_required
def holiday_list(request):
    court = request.user.staff.court
    today = timezone.localdate()
    context = {
        "court": court,
        "upcoming": court.holidays.filter(date__gte=today),
        "past": court.holidays.filter(date__lt=today).order_by("-date")[:10],
    }
    return render(request, "cases/holiday_list.html", context)


@court_staff_required
def holiday_add(request):
    court = request.user.staff.court
    form = HolidayForm(request.POST or None)
    if form.is_valid():
        holiday = form.save(commit=False)
        holiday.court = court
        if court.holidays.filter(date=holiday.date).exists():
            form.add_error("date", "This day is already marked as a holiday.")
        else:
            holiday.save()
            messages.success(request, "Holiday added.")
            return redirect("cases:holiday_list")
    context = {"form": form, "title": "Add court holiday", "cancel_url": "cases:holiday_list"}
    return render(request, "form_page.html", context)


@court_staff_required
def holiday_edit(request, pk):
    holiday = get_object_or_404(CourtHoliday, pk=pk, court=request.user.staff.court)
    form = HolidayForm(request.POST or None, instance=holiday)
    if form.is_valid():
        clash = holiday.court.holidays.filter(date=form.cleaned_data["date"]).exclude(pk=holiday.pk)
        if clash.exists():
            form.add_error("date", "This day is already marked as a holiday.")
        else:
            form.save()
            messages.success(request, "Holiday updated.")
            return redirect("cases:holiday_list")
    context = {"form": form, "title": "Edit court holiday", "cancel_url": "cases:holiday_list"}
    return render(request, "form_page.html", context)


@court_staff_required
def holiday_delete(request, pk):
    holiday = get_object_or_404(CourtHoliday, pk=pk, court=request.user.staff.court)
    if request.method == "POST":
        holiday.delete()
        messages.success(request, "Holiday deleted.")
        return redirect("cases:holiday_list")
    context = {"title": f"Delete {holiday.reason}?", "message": "Hearings can be set on this day again.",
               "cancel_url": "cases:holiday_list"}
    return render(request, "confirm_delete.html", context)
