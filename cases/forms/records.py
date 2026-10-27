import os

from django import forms

from accounts.forms import StyledModelForm

from cases.models import CaseDocument, CaseNote, Review

ALLOWED_FILES = [".pdf", ".jpg", ".jpeg", ".png", ".doc", ".docx", ".txt"]
MAX_MB = 5


class DocumentForm(StyledModelForm):
    class Meta:
        model = CaseDocument
        fields = ["title", "file"]

    def clean_file(self):
        file = self.cleaned_data["file"]
        extension = os.path.splitext(file.name)[1].lower()
        if extension not in ALLOWED_FILES:
            raise forms.ValidationError("Only pdf, jpg, png, doc, docx and txt files are allowed.")
        if file.size > MAX_MB * 1024 * 1024:
            raise forms.ValidationError(f"The file is too big (max {MAX_MB} MB).")
        return file


