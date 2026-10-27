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


class ReviewForm(StyledModelForm):
    rating = forms.TypedChoiceField(
        coerce=int,
        choices=[(5, "5 - Excellent"), (4, "4 - Good"), (3, "3 - Fair"), (2, "2 - Poor"), (1, "1 - Very poor")],
    )

    class Meta:
        model = Review
        fields = ["rating", "comment"]
        widgets = {"comment": forms.Textarea(attrs={"rows": 4, "placeholder": "How was your experience? (optional)"})}


class NoteForm(StyledModelForm):
    class Meta:
        model = CaseNote
        fields = ["text"]
        labels = {"text": "Your private note"}
        widgets = {"text": forms.Textarea(attrs={"rows": 4})}
