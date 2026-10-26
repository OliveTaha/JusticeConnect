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

