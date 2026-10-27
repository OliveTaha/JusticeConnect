from django.test import TestCase
from django.urls import reverse

from accounts.models import Account
from .models import Notification


class NotificationTest(TestCase):
    def setUp(self):
        self.account = Account.objects.create_user(username="u1", email="u1@x.com", password="secret123")
        self.client.login(username="u1", password="secret123")

    def test_send_and_list(self):
        Notification.send(self.account, "Hello there")
        response = self.client.get(reverse("notifications:list"))
        self.assertContains(response, "Hello there")

    def test_open_marks_as_read(self):
        note = Notification.send(self.account, "Read me")
        self.client.get(reverse("notifications:open", args=[note.pk]))
        note.refresh_from_db()
        self.assertTrue(note.is_read)

    def test_cannot_open_other_users_notification(self):
        other = Account.objects.create_user(username="u2", email="u2@x.com", password="secret123")
        note = Notification.send(other, "Not yours")
        response = self.client.get(reverse("notifications:open", args=[note.pk]))
        self.assertEqual(response.status_code, 404)

    def test_mark_all_read(self):
        Notification.send(self.account, "One")
        Notification.send(self.account, "Two")
        self.client.post(reverse("notifications:mark_all_read"))
        self.assertEqual(Notification.objects.filter(account=self.account, is_read=False).count(), 0)

    def test_delete_and_clear_read(self):
        first = Notification.send(self.account, "One")
        second = Notification.send(self.account, "Two")
        self.client.post(reverse("notifications:delete", args=[first.pk]))
        self.assertFalse(Notification.objects.filter(pk=first.pk).exists())
        second.mark_as_read()
        self.client.post(reverse("notifications:clear_read"))
        self.assertEqual(Notification.objects.count(), 0)

    def test_sidebar_shows_unread_count(self):
        Notification.send(self.account, "One")
        Notification.send(self.account, "Two")
        response = self.client.get(reverse("accounts:dashboard"))
        self.assertContains(response, '<span class="count">2</span>')
