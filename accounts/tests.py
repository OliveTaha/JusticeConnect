import io
import shutil
import tempfile

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse

from PIL import Image

from .models import Account, Client, Lawyer, Profile


class RegisterLoginTest(TestCase):
    def test_lawyer_register_creates_lawyer_and_profile(self):
        data = {
            "username": "adv1", "email": "adv@x.com", "name": "Adv One", "bar_id": "B1",
            "password": "secret123", "confirm_password": "secret123",
        }
        self.client.post(reverse("accounts:register"), data)
        account = Account.objects.get(username="adv1")
        self.assertEqual(account.role, Account.LAWYER)
        self.assertFalse(account.is_verified)
        self.assertTrue(Lawyer.objects.filter(account=account, bar_id="B1").exists())
        self.assertTrue(Profile.objects.filter(account=account).exists())

    def test_register_rejects_different_passwords(self):
        data = {
            "username": "adv1", "email": "adv@x.com", "name": "Adv", "bar_id": "B1",
            "password": "secret123", "confirm_password": "other123",
        }
        self.client.post(reverse("accounts:register"), data)
        self.assertEqual(Account.objects.count(), 0)

    def test_login_with_email(self):
        Account.objects.create_user(username="u1", email="u1@x.com", password="secret123")
        response = self.client.post(reverse("accounts:login"), {"email": "u1@x.com", "password": "secret123"})
        self.assertRedirects(response, reverse("accounts:dashboard"))

    def test_login_wrong_password(self):
        Account.objects.create_user(username="u1", email="u1@x.com", password="secret123")
        response = self.client.post(reverse("accounts:login"), {"email": "u1@x.com", "password": "wrong"})
        self.assertEqual(response.status_code, 200)

    def test_dashboard_needs_login(self):
        response = self.client.get(reverse("accounts:dashboard"))
        self.assertEqual(response.status_code, 302)


class VerifyTest(TestCase):
    def test_client_sets_password_and_gets_verified(self):
        account = Account.objects.create_user(username="c@x.com", email="c@x.com", role=Account.CLIENT)
        Client.objects.create(account=account, name="Client")
        url = reverse("accounts:verify", args=[account.verify_token])

        self.client.post(url, {"password": "clientpw1", "confirm_password": "clientpw1"})

        account.refresh_from_db()
        self.assertTrue(account.is_verified)
        self.assertTrue(account.check_password("clientpw1"))


class ProfileTest(TestCase):
    def setUp(self):
        account = Account.objects.create_user(
            username="adv", email="adv@x.com", password="secret123", role=Account.LAWYER, is_verified=True
        )
        self.lawyer = Lawyer.objects.create(account=account, name="Adv", bar_id="B1")
        Profile.objects.create(account=account, name="Adv")
        self.client.login(username="adv", password="secret123")

    def test_edit_profile(self):
        data = {"specialization": "Family law", "experience": 5, "bio": "Hello"}
        self.client.post(reverse("accounts:profile_edit"), data)
        profile = Profile.objects.get(account=self.lawyer.account)
        self.assertEqual(profile.specialization, "Family law")
        self.assertEqual(profile.experience, 5)

    def test_lawyer_detail_page(self):
        response = self.client.get(reverse("accounts:lawyer_detail", args=[self.lawyer.pk]))
        self.assertContains(response, "B1")


def make_image(name="me.png"):
    buffer = io.BytesIO()
    Image.new("RGB", (10, 10), "red").save(buffer, "PNG")
    return SimpleUploadedFile(name, buffer.getvalue(), content_type="image/png")


class ProfilePhotoTest(TestCase):
    def setUp(self):
        # uploaded photos go to a temporary folder while testing
        folder = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, folder)
        override = override_settings(MEDIA_ROOT=folder)
        override.enable()
        self.addCleanup(override.disable)

        account = Account.objects.create_user(
            username="adv", email="adv@x.com", password="secret123", role=Account.LAWYER, is_verified=True
        )
        self.lawyer = Lawyer.objects.create(account=account, name="Adv", bar_id="B1")
        Profile.objects.create(account=account, name="Adv")
        self.client.login(username="adv", password="secret123")
        self.url = reverse("accounts:profile_edit")

    def test_upload_photo(self):
        data = {"specialization": "", "experience": 0, "bio": "", "photo": make_image()}
        self.client.post(self.url, data)
        profile = Profile.objects.get(account=self.lawyer.account)
        self.assertTrue(profile.photo.name.startswith("profiles/"))

    def test_photo_is_shown_on_profile_page(self):
        data = {"specialization": "", "experience": 0, "bio": "", "photo": make_image()}
        self.client.post(self.url, data)
        response = self.client.get(reverse("accounts:lawyer_detail", args=[self.lawyer.pk]))
        self.assertContains(response, "<img")

    def test_remove_photo(self):
        self.client.post(self.url, {"specialization": "", "experience": 0, "bio": "", "photo": make_image()})
        self.client.post(self.url, {"specialization": "", "experience": 0, "bio": "", "photo-clear": "on"})
        profile = Profile.objects.get(account=self.lawyer.account)
        self.assertFalse(profile.photo)

    def test_non_image_is_rejected(self):
        fake = SimpleUploadedFile("fake.png", b"not an image", content_type="image/png")
        self.client.post(self.url, {"specialization": "", "experience": 0, "bio": "", "photo": fake})
        profile = Profile.objects.get(account=self.lawyer.account)
        self.assertFalse(profile.photo)
