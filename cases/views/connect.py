from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from accounts.decorators import role_required
from accounts.models import Account
from accounts.utils import paginate

from cases.permissions import is_case_client, is_case_lawyer

from cases.forms import AppointmentForm, AvailableFilterForm, MessageForm, RequestForm
from cases.models import Appointment, Case, CaseRequest, Message


def when(moment):
    return timezone.localtime(moment).strftime("%d %b %Y, %H:%M")


# ---------- lawyer: find cases and send requests ----------

@role_required(Account.LAWYER)
def available_cases(request):
    lawyer = request.user.lawyer
    if not request.user.is_verified:
        messages.error(request, "Your account must be verified before you can see open cases.")
        return redirect("accounts:dashboard")

    cases = lawyer.view_cases().select_related("court", "client")
    q = request.GET.get("q", "").strip()
    if q:
        cases = cases.filter(Q(title__icontains=q) | Q(case_number__icontains=q))
    if request.GET.get("case_type"):
        cases = cases.filter(case_type=request.GET["case_type"])

    context = {
        "page": paginate(request, cases, 8),
        "form": AvailableFilterForm(request.GET or None),
        "requested_ids": set(lawyer.requests.values_list("case_id", flat=True)),
    }
    return render(request, "cases/available.html", context)


@role_required(Account.LAWYER)
def request_send(request, case_pk):
    case = get_object_or_404(Case, pk=case_pk)
    form = RequestForm(request.POST or None)
    if form.is_valid():
        try:
            request.user.lawyer.request_case(case, form.cleaned_data["message"].strip())
            messages.success(request, "Request sent to the client.")
        except ValueError as error:
            messages.error(request, str(error))
    return redirect("cases:detail", pk=case.pk)


@role_required(Account.LAWYER)
def my_requests(request):
    requests = request.user.lawyer.requests.select_related("case", "case__court")
    return render(request, "cases/my_requests.html", {"requests": requests})


@role_required(Account.CLIENT)
def client_requests(request):
    requests = CaseRequest.objects.filter(case__client=request.user.client).select_related("case", "lawyer")
    return render(request, "cases/client_requests.html", {"requests": requests})


@role_required(Account.LAWYER)
def request_withdraw(request, pk):
    case_request = get_object_or_404(CaseRequest, pk=pk, lawyer=request.user.lawyer)
    if request.method == "POST":
        try:
            case_request.withdraw()
            messages.success(request, "Request withdrawn.")
        except ValueError as error:
            messages.error(request, str(error))
    return redirect("cases:my_requests")


# ---------- client: select or reject ----------

@role_required(Account.CLIENT)
def request_accept(request, pk):
    client = request.user.client
    case_request = get_object_or_404(CaseRequest, pk=pk, case__client=client)
    if request.method == "POST":
        try:
            client.select_lawyer(case_request)
            messages.success(request, f"{case_request.lawyer.name} is now your lawyer.")
        except ValueError as error:
            messages.error(request, str(error))
    return redirect("cases:detail", pk=case_request.case.pk)


@role_required(Account.CLIENT)
def request_reject(request, pk):
    case_request = get_object_or_404(CaseRequest, pk=pk, case__client=request.user.client)
    if request.method == "POST" and case_request.status == CaseRequest.PENDING:
        case_request.reject()
        messages.success(request, "Request rejected.")
    return redirect("cases:detail", pk=case_request.case.pk)


# ---------- chat ----------

@login_required
def chat(request, pk):
    case_request = get_object_or_404(CaseRequest, pk=pk)
    user = request.user
    # only the client of the case and the lawyer who made the request can talk
    if user not in (case_request.lawyer.account, case_request.case.client.account):
        messages.error(request, "You cannot open this chat.")
        return redirect("accounts:dashboard")

    form = MessageForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        try:
            Message.send(case_request, user, form.cleaned_data["body"])
            return redirect("cases:chat", pk=case_request.pk)
        except ValueError as error:
            messages.error(request, str(error))

    # opening the chat marks the other person's messages as read
    case_request.messages.exclude(sender=user).filter(is_read=False).update(is_read=True)

    context = {
        "case_request": case_request,
        "chat_messages": case_request.messages.select_related("sender"),
        "other": case_request.other_account(user),
        "form": form,
    }
    return render(request, "cases/chat.html", context)


# ---------- appointments ----------

def appointments_of(user):
    appointments = Appointment.objects.select_related("case", "created_by")
    if user.role == Account.CLIENT and hasattr(user, "client"):
        return appointments.filter(case__client=user.client)
    if user.role == Account.LAWYER and hasattr(user, "lawyer"):
        return appointments.filter(case__assigned_lawyer=user.lawyer)
    return appointments.none()


@login_required
def appointment_list(request):
    appointments = appointments_of(request.user)
    context = {
        "to_answer": [a for a in appointments if a.status == Appointment.PENDING and a.other_account == request.user],
        "appointments": appointments,
    }
    return render(request, "cases/appointment_list.html", context)


@login_required
def appointment_add(request, case_pk):
    case = get_object_or_404(Case, pk=case_pk)
    user = request.user
    if not (is_case_client(user, case) or is_case_lawyer(user, case)):
        messages.error(request, "Only the client and the lawyer of the case can make appointments.")
        return redirect("accounts:dashboard")
    if case.status != Case.ASSIGNED:
        messages.error(request, "Appointments are possible while a lawyer is working on the case.")
        return redirect("cases:detail", pk=case.pk)

    form = AppointmentForm(request.POST or None)
    if form.is_valid():
        appointment = form.save(commit=False)
        appointment.case = case
        appointment.created_by = user
        appointment.save()
        appointment.notify_other(f"{user.display_name} asked for an appointment on {when(appointment.scheduled_at)}: {appointment.purpose}.")
        messages.success(request, "Appointment request sent.")
        return redirect("cases:appointment_list")
    context = {"form": form, "title": "New appointment", "subtitle": f"Case {case.case_number}",
               "cancel_url": "cases:detail", "cancel_arg": case.pk}
    return render(request, "form_page.html", context)


@login_required
def appointment_edit(request, pk):
    appointment = get_object_or_404(Appointment, pk=pk, created_by=request.user)
    if appointment.status != Appointment.PENDING:
        messages.error(request, "Only an appointment that is still waiting for an answer can be changed.")
        return redirect("cases:appointment_list")

    form = AppointmentForm(request.POST or None, instance=appointment)
    if form.is_valid():
        form.save()
        appointment.notify_other(f"{request.user.display_name} changed the appointment to {when(appointment.scheduled_at)}: {appointment.purpose}.")
        messages.success(request, "Appointment updated.")
        return redirect("cases:appointment_list")
    context = {"form": form, "title": "Edit appointment", "subtitle": f"Case {appointment.case.case_number}",
               "cancel_url": "cases:appointment_list"}
    return render(request, "form_page.html", context)


@login_required
def appointment_delete(request, pk):
    appointment = get_object_or_404(Appointment, pk=pk, created_by=request.user)
    if request.method == "POST":
        appointment.notify_other(f"{request.user.display_name} cancelled the appointment '{appointment.purpose}'.")
        appointment.delete()
        messages.success(request, "Appointment cancelled.")
        return redirect("cases:appointment_list")
    context = {"title": f"Cancel '{appointment.purpose}'?", "message": "The other person will be told.",
               "cancel_url": "cases:appointment_list"}
    return render(request, "confirm_delete.html", context)


@login_required
def appointment_respond(request, pk, answer):
    appointment = get_object_or_404(Appointment, pk=pk)
    if appointment.other_account != request.user or appointment.status != Appointment.PENDING:
        messages.error(request, "You cannot answer this appointment.")
        return redirect("cases:appointment_list")
    if request.method == "POST":
        if answer == "confirm":
            appointment.confirm()
            messages.success(request, "Appointment confirmed.")
        else:
            appointment.decline()
            messages.success(request, "Appointment declined.")
    return redirect("cases:appointment_list")
