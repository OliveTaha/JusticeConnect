from django import forms
from django.utils import timezone

from accounts.forms import StyledForm, StyledModelForm

from cases.models import Appointment, Case


class RequestForm(StyledForm):
    message = forms.CharField(
        required=False, label="Message to the client",
        widget=forms.Textarea(attrs={"rows": 3, "placeholder": "Tell the client why you are a good fit (optional)"}),
    )


class MessageForm(StyledForm):
    body = forms.CharField(label="", widget=forms.Textarea(attrs={"rows": 2, "placeholder": "Write a message..."}))


class AvailableFilterForm(StyledForm):
    q = forms.CharField(required=False, label="Search", widget=forms.TextInput(attrs={"placeholder": "Title or case number"}))
    case_type = forms.ChoiceField(required=False, label="Type", choices=[("", "Any type")] + Case.TYPE_CHOICES)


class AppointmentForm(StyledModelForm):
    class Meta:
        model = Appointment
        fields = ["purpose", "scheduled_at"]
        widgets = {
            "scheduled_at": forms.DateTimeInput(attrs={"type": "datetime-local"}, format="%Y-%m-%dT%H:%M"),
        }

    def clean_scheduled_at(self):
        scheduled_at = self.cleaned_data["scheduled_at"]
        if scheduled_at < timezone.now():
            raise forms.ValidationError("Pick a time in the future.")
        return scheduled_at
