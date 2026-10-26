import uuid

from django.contrib.auth.models import AbstractUser
from django.db import models
from django.db.models import Avg


class Account(AbstractUser):
    CLIENT = "client"
    LAWYER = "lawyer"
    COURT_STAFF = "court_staff"
    ROLE_CHOICES = [
        (CLIENT, "Client"),
        (LAWYER, "Lawyer"),
        (COURT_STAFF, "Court Staff"),
    ]

    email = models.EmailField(unique=True)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default=CLIENT)
    is_verified = models.BooleanField(default=False)
    # clients get a link with this token to set their password
    verify_token = models.UUIDField(default=uuid.uuid4, editable=False)

    def __str__(self):
        return self.username

