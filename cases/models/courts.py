from django.db import models

from accounts.models import Account


class Area(models.Model):
    name = models.CharField(max_length=100, unique=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name

    @staticmethod
    def create_area(name):
        return Area.objects.create(name=name)

    def update_area(self, name):
        self.name = name
        self.save()


class Court(models.Model):
    name = models.CharField(max_length=150)
    address = models.CharField(max_length=200)
    area = models.ForeignKey(Area, on_delete=models.PROTECT, related_name="courts")

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return f"{self.name} ({self.area})"

    def manage_cases(self):
        return self.cases.all()


class CourtStaff(models.Model):
    """A court staff account works for exactly one court and only sees that court's cases."""

    account = models.OneToOneField(Account, on_delete=models.CASCADE, related_name="staff")
    court = models.ForeignKey(Court, on_delete=models.PROTECT, related_name="staff_members")
    name = models.CharField(max_length=100)
    designation = models.CharField(max_length=100, blank=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return f"{self.name} ({self.court.name})"


class CourtHoliday(models.Model):
    """A day when the court is closed. No hearing can be set on this day."""

    court = models.ForeignKey(Court, on_delete=models.CASCADE, related_name="holidays")
    date = models.DateField()
    reason = models.CharField(max_length=150)

    class Meta:
        ordering = ["date"]
        unique_together = ("court", "date")

    def __str__(self):
        return f"{self.reason} ({self.date})"
