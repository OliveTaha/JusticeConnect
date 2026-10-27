from django.db import models
from django.utils import timezone

from accounts.models import Account
from .courts import Court
from notifications.models import Notification


class Case(models.Model):
    REGISTERED = "registered"
    OPEN = "open"
    ASSIGNED = "assigned"
    CLOSED = "closed"
    STATUS_CHOICES = [
        (REGISTERED, "Waiting for consent"),
        (OPEN, "Open for lawyers"),
        (ASSIGNED, "Lawyer assigned"),
        (CLOSED, "Closed"),
    ]
    TYPE_CHOICES = [
        ("civil", "Civil"),
        ("criminal", "Criminal"),
        ("family", "Family"),
        ("property", "Property"),
        ("other", "Other"),
    ]

    case_number = models.CharField(max_length=50, unique=True)
    title = models.CharField(max_length=200)
    description = models.TextField()
    case_type = models.CharField(max_length=20, choices=TYPE_CHOICES, default="other")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=REGISTERED)
    court = models.ForeignKey(Court, on_delete=models.PROTECT, related_name="cases")
    client = models.ForeignKey("accounts.Client", on_delete=models.CASCADE, related_name="cases")
    assigned_lawyer = models.ForeignKey(
        "accounts.Lawyer", on_delete=models.SET_NULL, null=True, blank=True, related_name="assigned_cases"
    )
    consent = models.BooleanField(default=False)
    consent_date = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.case_number} - {self.title}"

    @property
    def progress(self):
        """The four steps of a case, marked done / current / todo (used by the step bar on the case page)."""
        keys = [key for key, label in self.STATUS_CHOICES]
        current = keys.index(self.status)
        steps = []
        for index, (key, label) in enumerate(self.STATUS_CHOICES):
            if index < current or self.status == self.CLOSED:
                state = "done"
            elif index == current:
                state = "current"
            else:
                state = "todo"
            steps.append({"label": label, "state": state})
        return steps

    def view_case(self):
        return self

    def log(self, text, user=None):
        # one line in the timeline of the case
        CaseEvent.objects.create(case=self, text=text, created_by=user)

    def confirm_case(self):
        # client gives consent, so verified lawyers can see the case now
        self.consent = True
        self.consent_date = timezone.now()
        self.status = self.OPEN
        self.save()
        self.log("The client gave consent. The case is open for lawyers.", self.client.account)

        Notification.send(
            self.client.account,
            f"Your consent for case {self.case_number} is saved. Lawyers can request it now.",
            case=self, type="case",
        )
        lawyers = Account.objects.filter(role=Account.LAWYER, is_verified=True)
        for lawyer_account in lawyers:
            Notification.send(lawyer_account, f"New case available: {self.title}", case=self, type="case")

    def assign_lawyer(self, lawyer):
        self.assigned_lawyer = lawyer
        self.status = self.ASSIGNED
        self.save()
        self.log(f"{lawyer.name} was selected as the lawyer.", self.client.account)
        Notification.send(lawyer.account, f"You are now the lawyer of case {self.case_number}.", case=self, type="case")
        Notification.send(self.client.account, f"{lawyer.name} is now your lawyer for case {self.case_number}.", case=self, type="case")

    def close_case(self):
        self.status = self.CLOSED
        self.save()
        self.log("The lawyer marked the case as closed.", self.assigned_lawyer.account)
        Notification.send(
            self.client.account,
            f"Case {self.case_number} is closed. Please rate your lawyer.",
            case=self, type="case",
        )


class CaseEvent(models.Model):
    """One line in the case timeline."""

    case = models.ForeignKey(Case, on_delete=models.CASCADE, related_name="events")
    text = models.CharField(max_length=255)
    created_by = models.ForeignKey(Account, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at", "-id"]

    def __str__(self):
        return self.text


class Hearing(models.Model):
    """A hearing date that court staff add to a case. The client and the lawyer can see it."""

    case = models.ForeignKey(Case, on_delete=models.CASCADE, related_name="hearings")
    title = models.CharField(max_length=150)
    scheduled_at = models.DateTimeField()
    room = models.CharField(max_length=50, blank=True)
    note = models.TextField(blank=True)
    created_by = models.ForeignKey(Account, on_delete=models.SET_NULL, null=True, blank=True)

    class Meta:
        ordering = ["scheduled_at"]

    def __str__(self):
        return f"{self.title} ({self.case.case_number})"

    @property
    def is_past(self):
        return self.scheduled_at < timezone.now()

    @classmethod
    def for_user(cls, user):
        """All hearings this user is allowed to see."""
        hearings = cls.objects.select_related("case", "case__court")
        if user.is_superuser:
            return hearings
        if user.role == Account.CLIENT and hasattr(user, "client"):
            return hearings.filter(case__client=user.client)
        if user.role == Account.LAWYER and hasattr(user, "lawyer"):
            return hearings.filter(case__assigned_lawyer=user.lawyer)
        if user.role == Account.COURT_STAFF and hasattr(user, "staff"):
            return hearings.filter(case__court=user.staff.court)
        return hearings.none()

    @classmethod
    def upcoming_for(cls, user):
        return cls.for_user(user).filter(scheduled_at__gte=timezone.now())

    def notify_people(self, text):
        accounts = [self.case.client.account]
        if self.case.assigned_lawyer:
            accounts.append(self.case.assigned_lawyer.account)
        for account in accounts:
            Notification.send(account, text, case=self.case, type="hearing")
