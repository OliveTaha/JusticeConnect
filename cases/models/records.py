import os

from django.conf import settings
from django.core.files.storage import FileSystemStorage
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

from accounts.models import Account
from .case import Case


def private_storage():
    # case documents are not public, they are served by a view that checks the user
    return FileSystemStorage(location=settings.PRIVATE_MEDIA_ROOT)


class CaseDocument(models.Model):
    case = models.ForeignKey(Case, on_delete=models.CASCADE, related_name="documents")
    uploaded_by = models.ForeignKey(Account, on_delete=models.SET_NULL, null=True, related_name="documents")
    title = models.CharField(max_length=100)
    file = models.FileField(upload_to="case_documents/", storage=private_storage)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-uploaded_at"]

    def __str__(self):
        return self.title

    @property
    def filename(self):
        return os.path.basename(self.file.name)

    @property
    def extension(self):
        return os.path.splitext(self.file.name)[1].lower().lstrip(".")


class Review(models.Model):
    """The client rates the lawyer after the case is closed. One review for each case."""

    case = models.OneToOneField(Case, on_delete=models.CASCADE, related_name="review")
    lawyer = models.ForeignKey("accounts.Lawyer", on_delete=models.CASCADE, related_name="reviews")
    client = models.ForeignKey("accounts.Client", on_delete=models.CASCADE, related_name="reviews")
    rating = models.PositiveSmallIntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])
    comment = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.rating}/5 for {self.lawyer.name}"


class CaseNote(models.Model):
    """A private note about a case. Only the person who wrote it can see it."""

    case = models.ForeignKey(Case, on_delete=models.CASCADE, related_name="notes")
    author = models.ForeignKey(Account, on_delete=models.CASCADE, related_name="case_notes")
    text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at"]

    def __str__(self):
        return self.text[:40]
