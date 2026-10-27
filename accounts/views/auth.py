from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.shortcuts import get_object_or_404, redirect, render

from ..forms import LawyerRegisterForm, LoginForm, SetPasswordForm
from ..models import Account, Lawyer, Profile


def register(request):
    # only lawyers register themselves. Clients are created by the court.
    form = LawyerRegisterForm(request.POST or None)
    if form.is_valid():
        data = form.cleaned_data
        account = Account.objects.create_user(
            username=data["username"],
            email=data["email"],
            password=data["password"],
            role=Account.LAWYER,
        )
        Lawyer.objects.create(account=account, name=data["name"], bar_id=data["bar_id"])
        Profile.objects.create(account=account, name=data["name"])
        messages.success(request, "Registered! You can log in now, but the admin must verify you before you can request cases.")
        return redirect("accounts:login")
    return render(request, "accounts/register.html", {"form": form})


def login_view(request):
    form = LoginForm(request.POST or None)
    if form.is_valid():
        email = form.cleaned_data["email"].lower()
        password = form.cleaned_data["password"]
        account = Account.objects.filter(email=email).first()
        user = None
        if account:
            user = authenticate(request, username=account.username, password=password)
        if user is None:
            messages.error(request, "Wrong email or password.")
        else:
            login(request, user)
            return redirect("accounts:dashboard")
    return render(request, "accounts/login.html", {"form": form})


def logout_view(request):
    if request.method == "POST":
        logout(request)
    return redirect("accounts:login")


def verify(request, token):
    # the client opens this link, sets a password and the account becomes verified
    account = get_object_or_404(Account, verify_token=token, role=Account.CLIENT)
    if account.is_verified:
        messages.info(request, "This account is already verified. Please log in.")
        return redirect("accounts:login")

    form = SetPasswordForm(request.POST or None)
    if form.is_valid():
        account.set_password(form.cleaned_data["password"])
        account.verify_account()
        messages.success(request, "Your account is verified. Please log in.")
        return redirect("accounts:login")
    return render(request, "accounts/verify.html", {"form": form, "account": account})


# ---------- dashboard ----------
