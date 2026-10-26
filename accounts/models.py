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

class Client(models.Model):
    account = models.OneToOneField(Account, on_delete=models.CASCADE, related_name="client")
    name = models.CharField(max_length=100)
    phone = models.CharField(max_length=20, blank=True)
    address = models.CharField(max_length=200, blank=True)

    def __str__(self):
        return self.name

    def view_cases(self):
        return self.cases.all()

    def confirm_case(self, case):
        # only the owner of the case can give consent
        if case.client != self:
            raise PermissionError("This is not your case.")
        case.confirm_case()

    def select_lawyer(self, case_request):
        if case_request.case.client != self:
            raise PermissionError("This is not your case.")
        case_request.accept()

        class Lawyer(models.Model):
            account = models.OneToOneField(Account, on_delete=models.CASCADE, related_name="lawyer")
            name = models.CharField(max_length=100)
            bar_id = models.CharField(max_length=50, unique=True)

            def __str__(self):
                return self.name

            def view_cases(self):
                from cases.models import Case

                # open cases = client already gave consent and no lawyer yet
                return Case.objects.filter(status=Case.OPEN)

            def request_case(self, case, message=""):
                from cases.models import CaseRequest

                return CaseRequest.submit_request(case, self, message)

            @property
            def average_rating(self):
                average = self.reviews.aggregate(avg=Avg("rating"))["avg"]
                return round(average, 1) if average else None

            @property
            def solved_cases(self):
                return self.assigned_cases.filter(status="closed").count()
