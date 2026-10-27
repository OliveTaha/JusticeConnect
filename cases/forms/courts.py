from django import forms

from accounts.forms import StyledForm, StyledModelForm
from accounts.models import Account

from cases.models import Area, Court, CourtHoliday, CourtStaff


class AreaForm(StyledModelForm):
    class Meta:
        model = Area
        fields = ["name"]


class CourtForm(StyledModelForm):
    class Meta:
        model = Court
        fields = ["name", "address", "area"]


class StaffCreateForm(StyledForm):
    """Makes the login account and the CourtStaff row together."""

    username = forms.CharField(max_length=150)
    email = forms.EmailField()
    password = forms.CharField(widget=forms.PasswordInput, min_length=6)
    name = forms.CharField(max_length=100, label="Full name")
    designation = forms.CharField(max_length=100, required=False)
    court = forms.ModelChoiceField(queryset=Court.objects.all())

    def clean_username(self):
        username = self.cleaned_data["username"]
        if Account.objects.filter(username=username).exists():
            raise forms.ValidationError("This username is already taken.")
        return username

    def clean_email(self):
        email = self.cleaned_data["email"].lower()
        if Account.objects.filter(email=email).exists():
            raise forms.ValidationError("This email is already registered.")
        return email


class StaffEditForm(StyledModelForm):
    class Meta:
        model = CourtStaff
        fields = ["name", "designation", "court"]


class HolidayForm(StyledModelForm):
    class Meta:
        model = CourtHoliday
        fields = ["date", "reason"]
        widgets = {"date": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d")}
