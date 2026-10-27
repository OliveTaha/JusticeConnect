from django.contrib import messages
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.db.models import Avg, Count, F, Q
from django.shortcuts import get_object_or_404, redirect, render

from notifications.models import Notification

from ..decorators import admin_required, role_required
from ..forms import ChangePasswordForm, ClientProfileForm, LawyerSearchForm, ProfileForm
from ..models import Account, Lawyer
from ..utils import paginate


@login_required
def lawyer_list(request):
    lawyers = (
        Lawyer.objects.filter(account__is_verified=True)
        .select_related("account__profile")
        .annotate(rating=Avg("reviews__rating"), review_total=Count("reviews", distinct=True))
    )

    q = request.GET.get("q", "").strip()
    if q:
        lawyers = lawyers.filter(Q(name__icontains=q) | Q(account__profile__specialization__icontains=q))

    sort = request.GET.get("sort", "rating")
    if sort == "experience":
        lawyers = lawyers.order_by("-account__profile__experience", "name")
    elif sort == "name":
        lawyers = lawyers.order_by("name")
    else:
        lawyers = lawyers.order_by(F("rating").desc(nulls_last=True), "name")

    context = {"page": paginate(request, lawyers, 9), "form": LawyerSearchForm(request.GET or None)}
    return render(request, "accounts/lawyer_list.html", context)


@login_required
def lawyer_detail(request, pk):
    lawyer = get_object_or_404(Lawyer, pk=pk)
    context = {
        "lawyer": lawyer,
        "profile": lawyer.account.profile.view_profile(),
        "reviews": lawyer.reviews.select_related("client"),
    }
    return render(request, "accounts/lawyer_detail.html", context)


@role_required(Account.LAWYER)
def profile_edit(request):
    form = ProfileForm(request.POST or None, request.FILES or None, instance=request.user.profile)
    if form.is_valid():
        form.save()
        messages.success(request, "Profile updated.")
        return redirect("accounts:lawyer_detail", pk=request.user.lawyer.pk)
    context = {
        "form": form, "title": "Edit profile", "multipart": True,
        "cancel_url": "accounts:lawyer_detail", "cancel_arg": request.user.lawyer.pk,
    }
    return render(request, "form_page.html", context)


@role_required(Account.CLIENT)
def client_profile_edit(request):
    form = ClientProfileForm(request.POST or None, instance=request.user.client)
    if form.is_valid():
        form.save()
        messages.success(request, "Your details are saved.")
        return redirect("accounts:dashboard")
    context = {"form": form, "title": "My details", "cancel_url": "accounts:dashboard"}
    return render(request, "form_page.html", context)


@login_required
def change_password(request):
    form = ChangePasswordForm(request.user, request.POST or None)
    if form.is_valid():
        user = form.save()
        update_session_auth_hash(request, user)  # keep the user logged in
        messages.success(request, "Password changed.")
        return redirect("accounts:dashboard")
    context = {"form": form, "title": "Change password", "cancel_url": "accounts:dashboard"}
    return render(request, "form_page.html", context)


# ---------- admin: approve lawyers ----------


@admin_required
def approvals(request):
    pending = Lawyer.objects.filter(account__is_verified=False).select_related("account")
    return render(request, "accounts/approvals.html", {"pending": pending})


@admin_required
def lawyer_verify(request, pk):
    lawyer = get_object_or_404(Lawyer, pk=pk)
    if request.method == "POST":
        lawyer.account.verify_account()
        Notification.send(lawyer.account, "Your account is verified. You can now request cases.")
        messages.success(request, f"{lawyer.name} is verified.")
    return redirect("accounts:approvals")


@admin_required
def lawyer_reject(request, pk):
    lawyer = get_object_or_404(Lawyer, pk=pk, account__is_verified=False)
    if request.method == "POST":
        lawyer.account.delete()  # removes the lawyer and the profile too
        messages.success(request, "Registration rejected and removed.")
    return redirect("accounts:approvals")
