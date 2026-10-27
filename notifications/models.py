from django.conf import settings
from django.db import models


class Notification(models.Model):
    # which bootstrap icon to show for each type
    ICONS = {
        "case": "bi-folder2-open",
        "request": "bi-person-raised-hand",
        "message": "bi-chat-left-text",
        "hearing": "bi-calendar-event",
        "appointment": "bi-clock",
        "review": "bi-star",
        "info": "bi-info-circle",
    }

    account = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="notifications")
    case = models.ForeignKey("cases.Case", on_delete=models.CASCADE, null=True, blank=True)
    message = models.TextField()
    type = models.CharField(max_length=30, default="info")
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at", "-id"]

    def __str__(self):
        return f"{self.account} - {self.message[:30]}"

    @property
    def icon(self):
        return self.ICONS.get(self.type, self.ICONS["info"])

    @classmethod
    def send(cls, account, message, case=None, type="info"):
        return cls.objects.create(account=account, message=message, case=case, type=type)

    def mark_as_read(self):
        self.is_read = True
        self.save()
