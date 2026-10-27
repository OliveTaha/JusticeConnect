import shutil
import tempfile

from django.core.files.storage import FileSystemStorage
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse

from cases.models import CaseDocument
from .base import BaseTest


class DocumentTest(BaseTest):
    def setUp(self):
        super().setUp()
        # the file field picks its storage when the app loads, so swap it for a temp folder
        self.folder = tempfile.mkdtemp()
        field = CaseDocument._meta.get_field("file")
        old_storage = field.storage
        field.storage = FileSystemStorage(location=self.folder)
        self.addCleanup(setattr, field, "storage", old_storage)
        self.addCleanup(shutil.rmtree, self.folder, True)

    def upload(self, name="paper.pdf", content=b"data"):
        return self.client.post(
            reverse("cases:document_add", args=[self.case.pk]),
            {"title": "Paper", "file": SimpleUploadedFile(name, content)},
        )

    def test_upload_download_edit_delete(self):
        self.login(self.client_account)
        self.upload()
        document = CaseDocument.objects.get()
        response = self.client.get(reverse("cases:document_download", args=[document.pk]))
        self.assertEqual(b"".join(response.streaming_content), b"data")

        self.client.post(reverse("cases:document_edit", args=[document.pk]),
                         {"title": "Renamed", "file": SimpleUploadedFile("new.pdf", b"new")})
        document.refresh_from_db()
        self.assertEqual(document.title, "Renamed")

        self.client.post(reverse("cases:document_delete", args=[document.pk]))
        self.assertEqual(CaseDocument.objects.count(), 0)

    def test_bad_extension_is_rejected(self):
        self.login(self.client_account)
        self.upload(name="virus.exe")
        self.assertEqual(CaseDocument.objects.count(), 0)

    def test_big_file_is_rejected(self):
        self.login(self.client_account)
        self.upload(content=b"x" * (5 * 1024 * 1024 + 1))
        self.assertEqual(CaseDocument.objects.count(), 0)

    def test_stranger_cannot_download(self):
        self.login(self.client_account)
        self.upload()
        document = CaseDocument.objects.get()
        self.client.logout()
        self.login(self.lawyer_account)
        response = self.client.get(reverse("cases:document_download", args=[document.pk]))
        self.assertEqual(response.status_code, 302)
