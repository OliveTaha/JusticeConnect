from django import forms
from django.contrib.auth.forms import PasswordChangeForm

from .models import Account, Client, Lawyer, Profile


class StyleMixin:
    """Gives every field the bootstrap class that fits its widget."""

    def style_fields(self):
        for field in self.fields.values():
            if isinstance(field.widget, forms.Select):
                field.widget.attrs["class"] = "form-select"
            elif isinstance(field.widget, forms.CheckboxInput):
                field.widget.attrs["class"] = "form-check-input"
            else:
                field.widget.attrs["class"] = "form-control"


class StyledForm(StyleMixin, forms.Form):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.style_fields()


class StyledModelForm(StyleMixin, forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.style_fields()


class LawyerRegisterForm(StyledForm):
    username = forms.CharField(max_length=150)
    email = forms.EmailField()
    name = forms.CharField(max_length=100, label="Full name")
    bar_id = forms.CharField(max_length=50, label="Bar ID")
    password = forms.CharField(widget=forms.PasswordInput, min_length=6)
    confirm_password = forms.CharField(widget=forms.PasswordInput)

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

    def clean_bar_id(self):
        bar_id = self.cleaned_data["bar_id"]
        if Lawyer.objects.filter(bar_id=bar_id).exists():
            raise forms.ValidationError("This Bar ID is already registered.")
        return bar_id

    def clean(self):
        data = super().clean()
        if data.get("password") != data.get("confirm_password"):
            self.add_error("confirm_password", "Passwords do not match.")
        return data


class LoginForm(StyledForm):
    email = forms.EmailField()
    password = forms.CharField(widget=forms.PasswordInput)


class SetPasswordForm(StyledForm):
    password = forms.CharField(widget=forms.PasswordInput, min_length=6)
    confirm_password = forms.CharField(widget=forms.PasswordInput)

    def clean(self):
        data = super().clean()
        if data.get("password") != data.get("confirm_password"):
            self.add_error("confirm_password", "Passwords do not match.")
        return data


class ChangePasswordForm(StyleMixin, PasswordChangeForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.style_fields()


class ProfileForm(StyledModelForm):
    class Meta:
        model = Profile
        fields = ["specialization", "experience", "bio", "photo"]
        widgets = {"bio": forms.Textarea(attrs={"rows": 4})}


class ClientProfileForm(StyledModelForm):
    class Meta:
        model = Client
        fields = ["name", "phone", "address"]


class LawyerSearchForm(StyledForm):
    q = forms.CharField(required=False, label="Search", widget=forms.TextInput(attrs={"placeholder": "Name or specialization"}))
    sort = forms.ChoiceField(
        required=False,
        choices=[("rating", "Best rated"), ("experience", "Most experienced"), ("name", "Name")],
    )
