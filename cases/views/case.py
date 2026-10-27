from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone

from accounts.decorators import court_staff_required, role_required
from accounts.models import Account, Client
from accounts.utils import paginate
from notifications.models import Notification

from cases.forms import CaseCreateForm, CaseEditForm, CaseFilterForm, HearingForm
from cases.models import Case, Hearing
from cases.permissions import can_add_document, can_view, is_case_client, is_case_lawyer, is_case_staff


def when(moment):
    return timezone.localtime(moment).strftime("%d %b %Y, %H:%M")


# ---------- cases: list, detail ----------

@login_required
def case_list(request):
    user = request.user
    if user.is_superuser:
        cases, title = Case.objects.all(), "All cases"
    elif user.role == Account.COURT_STAFF and hasattr(user, "staff"):
        cases, title = Case.objects.filter(court=user.staff.court), "Cases of my court"
    elif user.role == Account.CLIENT and hasattr(user, "client"):
        cases, title = user.client.view_cases(), "My cases"
    elif user.role == Account.LAWYER and hasattr(user, "lawyer"):
        cases, title = user.lawyer.assigned_cases.all(), "My cases"
    else:
        return redirect("accounts:dashboard")

    # search and filters
    q = request.GET.get("q", "").strip()
    if q:
        cases = cases.filter(Q(case_number__icontains=q) | Q(title__icontains=q) | Q(client__name__icontains=q))
    if request.GET.get("status"):
        cases = cases.filter(status=request.GET["status"])
    if request.GET.get("case_type"):
        cases = cases.filter(case_type=request.GET["case_type"])

    context = {
        "page": paginate(request, cases.select_related("court", "client", "assigned_lawyer"), 8),
        "form": CaseFilterForm(request.GET or None),
        "title": title,
    }
    return render(request, "cases/list.html", context)


@login_required
def case_detail(request, pk):
    case = get_object_or_404(Case, pk=pk)
    user = request.user
    if not can_view(user, case):
        messages.error(request, "You cannot open this case.")
        return redirect("accounts:dashboard")

    is_staff = is_case_staff(user, case)
    is_client = is_case_client(user, case)
    is_lawyer = is_case_lawyer(user, case)

    verify_link = None
    if is_staff and not case.client.account.is_verified:
        # the court sends this link to the client
        verify_link = request.build_absolute_uri(reverse("accounts:verify", args=[case.client.account.verify_token]))

    my_request = None
    if user.role == Account.LAWYER and hasattr(user, "lawyer"):
        my_request = case.requests.filter(lawyer=user.lawyer).first()

    context = {
        "case": case,
        "steps": case.progress,
        "events": case.events.select_related("created_by"),
        "hearings": case.hearings.all(),
        "is_staff": is_staff,
        "is_client": is_client,
        "is_lawyer": is_lawyer,
        "can_add_document": can_add_document(user, case),
        "verify_link": verify_link,
        "my_request": my_request,
        "review": getattr(case, "review", None),
        "appointments": case.appointments.all() if (is_client or is_lawyer) else [],
        "notes": case.notes.filter(author=user),
    }
    return render(request, "cases/detail.html", context)


# ---------- court staff: create, edit, delete ----------

@court_staff_required
def case_create(request):
    staff = request.user.staff
    form = CaseCreateForm(request.POST or None)
    if form.is_valid():
        data = form.cleaned_data
        email = data["client_email"].lower()

        # find the client account, or make a new one
        account = Account.objects.filter(email=email).first()
        if account is None:
            account = Account.objects.create_user(username=email, email=email, role=Account.CLIENT)
        if account.role != Account.CLIENT:
            form.add_error("client_email", "This email belongs to a lawyer or court staff account.")
            return render(request, "form_page.html", {"form": form, "title": "Register case", "cancel_url": "cases:list"})

        client, _ = Client.objects.get_or_create(
            account=account,
            defaults={"name": data["client_name"], "phone": data["client_phone"], "address": data["client_address"]},
        )

        case = form.save(commit=False)
        case.court = staff.court
        case.client = client
        case.save()
        case.log(f"Case registered by {staff.name}.", request.user)

        if account.is_verified:
            Notification.send(account, f"A new case {case.case_number} was registered for you. Please give your consent.", case=case, type="case")
        else:
            link = request.build_absolute_uri(reverse("accounts:verify", args=[account.verify_token]))
            Notification.send(account, f"A case {case.case_number} was registered for you. Verify your account: {link}", case=case, type="case")

        messages.success(request, "Case registered.")
        return redirect("cases:detail", pk=case.pk)
    context = {"form": form, "title": "Register case", "subtitle": f"This case will be filed under {staff.court.name}.", "cancel_url": "cases:list"}
    return render(request, "form_page.html", context)


@court_staff_required
def case_edit(request, pk):
    case = get_object_or_404(Case, pk=pk, court=request.user.staff.court)
    if case.status not in (Case.REGISTERED, Case.OPEN):
        messages.error(request, "A case with a lawyer cannot be edited.")
        return redirect("cases:detail", pk=case.pk)

    form = CaseEditForm(request.POST or None, instance=case)
    if form.is_valid():
        form.save()
        case.log("Case details were updated.", request.user)
        messages.success(request, "Case updated.")
        return redirect("cases:detail", pk=case.pk)
    context = {"form": form, "title": f"Edit case {case.case_number}", "cancel_url": "cases:detail", "cancel_arg": case.pk}
    return render(request, "form_page.html", context)


@court_staff_required
def case_delete(request, pk):
    case = get_object_or_404(Case, pk=pk, court=request.user.staff.court)
    if case.status not in (Case.REGISTERED, Case.OPEN):
        messages.error(request, "A case with a lawyer cannot be deleted.")
        return redirect("cases:detail", pk=case.pk)

    if request.method == "POST":
        case.delete()
        messages.success(request, "Case deleted.")
        return redirect("cases:list")
    context = {"title": f"Delete case {case.case_number}?", "message": case.title,
               "cancel_url": "cases:detail", "cancel_arg": case.pk}
    return render(request, "confirm_delete.html", context)


# ---------- client consent, lawyer closes ----------

@role_required(Account.CLIENT)
def case_consent(request, pk):
    client = request.user.client
    case = get_object_or_404(Case, pk=pk, client=client)
    if request.method == "POST":
        if case.consent:
            messages.info(request, "You already gave consent.")
        else:
            client.confirm_case(case)
            messages.success(request, "Consent saved. Lawyers can request your case now.")
    return redirect("cases:detail", pk=case.pk)


@role_required(Account.LAWYER)
def case_close(request, pk):
    case = get_object_or_404(Case, pk=pk, assigned_lawyer=request.user.lawyer)
    if request.method == "POST" and case.status == Case.ASSIGNED:
        case.close_case()
        messages.success(request, "Case closed.")
    return redirect("cases:detail", pk=case.pk)


# ---------- hearings ----------

@court_staff_required
def hearing_add(request, case_pk):
    case = get_object_or_404(Case, pk=case_pk, court=request.user.staff.court)
    if case.status == Case.CLOSED:
        messages.error(request, "This case is closed.")
        return redirect("cases:detail", pk=case.pk)

    form = HearingForm(request.POST or None, court=case.court)
    if form.is_valid():
        hearing = form.save(commit=False)
        hearing.case = case
        hearing.created_by = request.user
        hearing.save()
        case.log(f"Hearing added: {hearing.title} on {when(hearing.scheduled_at)}.", request.user)
        hearing.notify_people(f"New hearing for case {case.case_number}: {hearing.title} on {when(hearing.scheduled_at)}.")
        messages.success(request, "Hearing added.")
        return redirect("cases:detail", pk=case.pk)
    context = {"form": form, "title": "Add hearing", "subtitle": f"Case {case.case_number}", "cancel_url": "cases:detail", "cancel_arg": case.pk}
    return render(request, "form_page.html", context)


@court_staff_required
def hearing_edit(request, pk):
    hearing = get_object_or_404(Hearing, pk=pk, case__court=request.user.staff.court)
    form = HearingForm(request.POST or None, instance=hearing, court=hearing.case.court)
    if form.is_valid():
        form.save()
        hearing.case.log(f"Hearing changed: {hearing.title} is now on {when(hearing.scheduled_at)}.", request.user)
        hearing.notify_people(f"Hearing changed for case {hearing.case.case_number}: {hearing.title} is now on {when(hearing.scheduled_at)}.")
        messages.success(request, "Hearing updated.")
        return redirect("cases:detail", pk=hearing.case.pk)
    context = {"form": form, "title": "Edit hearing", "subtitle": f"Case {hearing.case.case_number}",
               "cancel_url": "cases:detail", "cancel_arg": hearing.case.pk}
    return render(request, "form_page.html", context)


@court_staff_required
def hearing_delete(request, pk):
    hearing = get_object_or_404(Hearing, pk=pk, case__court=request.user.staff.court)
    case = hearing.case
    if request.method == "POST":
        hearing.notify_people(f"Hearing cancelled for case {case.case_number}: {hearing.title}.")
        case.log(f"Hearing cancelled: {hearing.title}.", request.user)
        hearing.delete()
        messages.success(request, "Hearing deleted.")
        return redirect("cases:detail", pk=case.pk)
    context = {"title": f"Delete hearing {hearing.title}?", "message": "The client and the lawyer will be told.",
               "cancel_url": "cases:detail", "cancel_arg": case.pk}
    return render(request, "confirm_delete.html", context)


@login_required
def schedule(request):
    hearings = Hearing.for_user(request.user)
    now = timezone.now()
    context = {
        "upcoming": hearings.filter(scheduled_at__gte=now),
        "past": hearings.filter(scheduled_at__lt=now).order_by("-scheduled_at")[:10],
    }
    return render(request, "cases/schedule.html", context)
