from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import FileResponse
from django.shortcuts import get_object_or_404, redirect, render

from accounts.decorators import role_required
from accounts.models import Account

from cases.permissions import can_add_document, can_view, is_case_staff
from notifications.models import Notification

from cases.forms import DocumentForm, NoteForm, ReviewForm
from cases.models import Case, CaseDocument, CaseNote, Review


def can_change_document(user, document):
    # only the uploader or the court staff of the case can edit or delete a document
    return document.uploaded_by == user or is_case_staff(user, document.case)


# ---------- documents (media CRUD) ----------

@login_required
def document_add(request, case_pk):
    case = get_object_or_404(Case, pk=case_pk)
    if not can_add_document(request.user, case):
        messages.error(request, "You cannot upload documents to this case.")
        return redirect("cases:detail", pk=case.pk)

    form = DocumentForm(request.POST or None, request.FILES or None)
    if form.is_valid():
        document = form.save(commit=False)
        document.case = case
        document.uploaded_by = request.user
        document.save()
        case.log(f"Document added: {document.title}.", request.user)
        messages.success(request, "Document uploaded.")
        return redirect("cases:detail", pk=case.pk)
    context = {
        "form": form, "title": "Upload document", "multipart": True,
        "subtitle": f"Case {case.case_number}. Allowed: pdf, jpg, png, doc, docx, txt (max 5 MB).",
        "cancel_url": "cases:detail", "cancel_arg": case.pk,
    }
    return render(request, "form_page.html", context)


@login_required
def document_download(request, pk):
    document = get_object_or_404(CaseDocument, pk=pk)
    if not can_view(request.user, document.case):
        messages.error(request, "You cannot open this document.")
        return redirect("accounts:dashboard")
    return FileResponse(document.file.open("rb"), as_attachment=True, filename=document.filename)


@login_required
def document_edit(request, pk):
    document = get_object_or_404(CaseDocument, pk=pk)
    if not can_change_document(request.user, document):
        messages.error(request, "You cannot change this document.")
        return redirect("cases:detail", pk=document.case.pk)

    old_file = document.file
    form = DocumentForm(request.POST or None, request.FILES or None, instance=document)
    if form.is_valid():
        form.save()
        if "file" in form.changed_data:
            old_file.delete(save=False)  # remove the replaced file from the disk
        messages.success(request, "Document updated.")
        return redirect("cases:detail", pk=document.case.pk)
    context = {
        "form": form, "title": "Edit document", "multipart": True,
        "subtitle": f"Case {document.case.case_number}. Choose a new file only if you want to replace the old one.",
        "cancel_url": "cases:detail", "cancel_arg": document.case.pk,
    }
    return render(request, "form_page.html", context)


@login_required
def document_delete(request, pk):
    document = get_object_or_404(CaseDocument, pk=pk)
    if not can_change_document(request.user, document):
        messages.error(request, "You cannot delete this document.")
        return redirect("cases:detail", pk=document.case.pk)

    if request.method == "POST":
        case_pk = document.case.pk
        document.file.delete(save=False)
        document.delete()
        messages.success(request, "Document deleted.")
        return redirect("cases:detail", pk=case_pk)
    context = {"title": f"Delete {document.title}?", "message": "The file will be removed from the server.",
               "cancel_url": "cases:detail", "cancel_arg": document.case.pk}
    return render(request, "confirm_delete.html", context)


# ---------- reviews ----------

@role_required(Account.CLIENT)
def review_add(request, case_pk):
    client = request.user.client
    case = get_object_or_404(Case, pk=case_pk, client=client)
    if case.status != Case.CLOSED or case.assigned_lawyer is None:
        messages.error(request, "You can rate the lawyer after the case is closed.")
        return redirect("cases:detail", pk=case.pk)
    if hasattr(case, "review"):
        return redirect("cases:review_edit", pk=case.review.pk)

    form = ReviewForm(request.POST or None)
    if form.is_valid():
        review = form.save(commit=False)
        review.case = case
        review.lawyer = case.assigned_lawyer
        review.client = client
        review.save()
        Notification.send(review.lawyer.account, f"You got a {review.rating}-star review for case {case.case_number}.", case=case, type="review")
        messages.success(request, "Thank you for your review.")
        return redirect("cases:detail", pk=case.pk)
    context = {"form": form, "title": "Rate your lawyer", "subtitle": f"{case.assigned_lawyer.name}, case {case.case_number}",
               "cancel_url": "cases:detail", "cancel_arg": case.pk}
    return render(request, "form_page.html", context)


@role_required(Account.CLIENT)
def review_edit(request, pk):
    review = get_object_or_404(Review, pk=pk, client=request.user.client)
    form = ReviewForm(request.POST or None, instance=review)
    if form.is_valid():
        form.save()
        messages.success(request, "Review updated.")
        return redirect("cases:detail", pk=review.case.pk)
    context = {"form": form, "title": "Edit your review", "subtitle": f"{review.lawyer.name}, case {review.case.case_number}",
               "cancel_url": "cases:detail", "cancel_arg": review.case.pk}
    return render(request, "form_page.html", context)


@role_required(Account.CLIENT)
def review_delete(request, pk):
    review = get_object_or_404(Review, pk=pk, client=request.user.client)
    if request.method == "POST":
        case_pk = review.case.pk
        review.delete()
        messages.success(request, "Review deleted.")
        return redirect("cases:detail", pk=case_pk)
    context = {"title": "Delete your review?", "message": "The rating will no longer count for the lawyer.",
               "cancel_url": "cases:detail", "cancel_arg": review.case.pk}
    return render(request, "confirm_delete.html", context)


# ---------- private notes ----------

@login_required
def note_add(request, case_pk):
    case = get_object_or_404(Case, pk=case_pk)
    if not can_view(request.user, case):
        messages.error(request, "You cannot open this case.")
        return redirect("accounts:dashboard")
    form = NoteForm(request.POST or None)
    if form.is_valid():
        note = form.save(commit=False)
        note.case = case
        note.author = request.user
        note.save()
        messages.success(request, "Note saved.")
        return redirect("cases:detail", pk=case.pk)
    context = {"form": form, "title": "Add note", "subtitle": f"Case {case.case_number}. Only you can see it.",
               "cancel_url": "cases:detail", "cancel_arg": case.pk}
    return render(request, "form_page.html", context)


@login_required
def note_edit(request, pk):
    note = get_object_or_404(CaseNote, pk=pk, author=request.user)
    form = NoteForm(request.POST or None, instance=note)
    if form.is_valid():
        form.save()
        messages.success(request, "Note updated.")
        return redirect("cases:detail", pk=note.case.pk)
    context = {"form": form, "title": "Edit note", "subtitle": "Only you can see it.",
               "cancel_url": "cases:detail", "cancel_arg": note.case.pk}
    return render(request, "form_page.html", context)


@login_required
def note_delete(request, pk):
    note = get_object_or_404(CaseNote, pk=pk, author=request.user)
    case_pk = note.case.pk
    if request.method == "POST":
        note.delete()
        messages.success(request, "Note deleted.")
        return redirect("cases:detail", pk=case_pk)
    context = {"title": "Delete this note?", "message": note.text[:80],
               "cancel_url": "cases:detail", "cancel_arg": case_pk}
    return render(request, "confirm_delete.html", context)
