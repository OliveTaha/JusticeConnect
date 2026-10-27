import re

from django.db import models
from django.utils import timezone

from accounts.models import Account
from .case import Case
from notifications.models import Notification

EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")
PHONE_RE = re.compile(r"\+?\d[\d\s().-]{6,}\d")


def hide_contact_details(text):
    """Before the client picks a lawyer, emails and phone numbers are hidden in the chat."""
    text = EMAIL_RE.sub("[hidden]", text)

    def mask(match):
        digits = sum(ch.isdigit() for ch in match.group(0))
        return "[hidden]" if digits >= 8 else match.group(0)

    return PHONE_RE.sub(mask, text)


class CaseRequest(models.Model):
    PENDING = "pending"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    WITHDRAWN = "withdrawn"
    STATUS_CHOICES = [
        (PENDING, "Pending"),
        (ACCEPTED, "Accepted"),
        (REJECTED, "Rejected"),
        (WITHDRAWN, "Withdrawn"),
    ]

    case = models.ForeignKey(Case, on_delete=models.CASCADE, related_name="requests")
    lawyer = models.ForeignKey("accounts.Lawyer", on_delete=models.CASCADE, related_name="requests")
    message = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=PENDING)
    requested_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-requested_at"]
        unique_together = ("case", "lawyer")

    def __str__(self):
        return f"{self.lawyer} -> {self.case.case_number}"

    @property
    def chat_open(self):
        return self.status in (self.PENDING, self.ACCEPTED)

    @property
    def unread_for_client(self):
        # messages from the lawyer that the client has not opened yet
        return self.messages.filter(sender=self.lawyer.account, is_read=False).count()

    @property
    def unread_for_lawyer(self):
        return self.messages.filter(sender=self.case.client.account, is_read=False).count()

    def other_account(self, user):
        """The person on the other side of the chat."""
        if user == self.lawyer.account:
            return self.case.client.account
        return self.lawyer.account

    @classmethod
    def submit_request(cls, case, lawyer, message=""):
        if not lawyer.account.is_verified:
            raise ValueError("Your account is not verified yet.")
        if case.status != Case.OPEN:
            raise ValueError("This case is not open for requests.")
        if cls.objects.filter(case=case, lawyer=lawyer).exists():
            raise ValueError("You already sent a request for this case.")

        request = cls.objects.create(case=case, lawyer=lawyer, message=message)
        case.log(f"{lawyer.name} sent a request for this case.", lawyer.account)
        Notification.send(
            case.client.account,
            f"{lawyer.name} wants to take your case {case.case_number}.",
            case=case, type="request",
        )
        return request

    def accept(self):
        # client picks this lawyer: assign him and reject everybody else
        if self.case.status != Case.OPEN or self.status != self.PENDING:
            raise ValueError("This request cannot be accepted any more.")
        self.status = self.ACCEPTED
        self.save()
        self.case.assign_lawyer(self.lawyer)

        others = self.case.requests.exclude(pk=self.pk).filter(status=self.PENDING)
        for other in others:
            other.reject()

    def reject(self):
        self.status = self.REJECTED
        self.save()
        Notification.send(
            self.lawyer.account,
            f"Your request for case {self.case.case_number} was not accepted.",
            case=self.case, type="request",
        )

    def withdraw(self):
        # the lawyer takes his own request back before the client decides
        if self.status != self.PENDING:
            raise ValueError("Only a pending request can be withdrawn.")
        self.status = self.WITHDRAWN
        self.save()
        Notification.send(
            self.case.client.account,
            f"{self.lawyer.name} withdrew the request for case {self.case.case_number}.",
            case=self.case, type="request",
        )


class Message(models.Model):
    request = models.ForeignKey(CaseRequest, on_delete=models.CASCADE, related_name="messages")
    sender = models.ForeignKey(Account, on_delete=models.CASCADE, related_name="sent_messages")
    body = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        return f"{self.sender}: {self.body[:30]}"

    @classmethod
    def send(cls, case_request, sender, body):
        body = body.strip()
        if not body:
            raise ValueError("Write a message first.")
        if not case_request.chat_open:
            raise ValueError("This chat is closed.")
        if case_request.status != CaseRequest.ACCEPTED:
            body = hide_contact_details(body)

        message = cls.objects.create(request=case_request, sender=sender, body=body)

        # one unread notification is enough, do not spam the other person
        recipient = case_request.other_account(sender)
        already = Notification.objects.filter(account=recipient, case=case_request.case, type="message", is_read=False)
        if not already.exists():
            Notification.send(recipient, f"New message about case {case_request.case.case_number}.", case=case_request.case, type="message")
        return message


class Appointment(models.Model):
    """A meeting between the client and the assigned lawyer. One side asks, the other side confirms or declines."""

    PENDING = "pending"
    CONFIRMED = "confirmed"
    DECLINED = "declined"
    STATUS_CHOICES = [
        (PENDING, "Waiting for answer"),
        (CONFIRMED, "Confirmed"),
        (DECLINED, "Declined"),
    ]

    case = models.ForeignKey(Case, on_delete=models.CASCADE, related_name="appointments")
    created_by = models.ForeignKey(Account, on_delete=models.CASCADE, related_name="appointments_made")
    purpose = models.CharField(max_length=150)
    scheduled_at = models.DateTimeField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=PENDING)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["scheduled_at"]

    def __str__(self):
        return f"{self.purpose} ({self.case.case_number})"

    @property
    def is_past(self):
        return self.scheduled_at < timezone.now()

    @property
    def other_account(self):
        """The person who has to answer."""
        if self.created_by == self.case.client.account:
            return self.case.assigned_lawyer.account
        return self.case.client.account

    def notify_other(self, text):
        Notification.send(self.other_account, text, case=self.case, type="appointment")

    def confirm(self):
        self.status = self.CONFIRMED
        self.save()
        Notification.send(self.created_by, f"Your appointment '{self.purpose}' was confirmed.", case=self.case, type="appointment")

    def decline(self):
        self.status = self.DECLINED
        self.save()
        Notification.send(self.created_by, f"Your appointment '{self.purpose}' was declined.", case=self.case, type="appointment")
