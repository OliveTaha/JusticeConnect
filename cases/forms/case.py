from django import forms

from accounts.forms import StyledForm, StyledModelForm

from cases.models import Case, Hearing


class CaseCreateForm(StyledModelForm):
    # client details, the court types them when registering the case
    client_name = forms.CharField(max_length=100)
    client_email = forms.EmailField()
    client_phone = forms.CharField(max_length=20, required=False)
    client_address = forms.CharField(max_length=200, required=False)

    class Meta:
        model = Case
        fields = ["case_number", "title", "description", "case_type"]
        widgets = {"description": forms.Textarea(attrs={"rows": 4})}


class CaseEditForm(StyledModelForm):
    class Meta:
        model = Case
        fields = ["title", "description", "case_type"]
        widgets = {"description": forms.Textarea(attrs={"rows": 4})}


class CaseFilterForm(StyledForm):
    q = forms.CharField(required=False, label="Search", widget=forms.TextInput(attrs={"placeholder": "Number, title or client"}))
    status = forms.ChoiceField(required=False, choices=[("", "Any status")] + Case.STATUS_CHOICES)
    case_type = forms.ChoiceField(required=False, label="Type", choices=[("", "Any type")] + Case.TYPE_CHOICES)


class HearingForm(StyledModelForm):
    def __init__(self, *args, court=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.court = court

    def clean_scheduled_at(self):
        moment = self.cleaned_data["scheduled_at"]
        if self.court and self.court.holidays.filter(date=moment.date()).exists():
            raise forms.ValidationError("The court is closed on this day.")
        return moment

    class Meta:
        model = Hearing
        fields = ["title", "scheduled_at", "room", "note"]
        widgets = {
            "scheduled_at": forms.DateTimeInput(attrs={"type": "datetime-local"}, format="%Y-%m-%dT%H:%M"),
            "note": forms.Textarea(attrs={"rows": 3}),
        }
