from datetime import timedelta

from django.urls import reverse
from django.utils import timezone

from accounts.models import Account
from cases.models import Case, CaseNote, Hearing
from notifications.models import Notification
from .base import BaseTest


class CaseCrudTest(BaseTest):
    def test_staff_registers_case_and_client_account_is_made(self):
        self.login(self.staff_account)
        data = {"case_number": "C-2", "title": "Theft", "description": "Details", "case_type": "criminal",
                "client_name": "Karim", "client_email": "karim@x.com"}
        self.client.post(reverse("cases:create"), data)
        case = Case.objects.get(case_number="C-2")
        self.assertEqual(case.court, self.court)
        self.assertEqual(case.status, Case.REGISTERED)
        self.assertEqual(case.client.account.role, Account.CLIENT)
        self.assertFalse(case.client.account.is_verified)

    def test_staff_edits_and_deletes_case(self):
        self.login(self.staff_account)
        self.client.post(reverse("cases:edit", args=[self.case.pk]),
                         {"title": "New title", "description": "Text", "case_type": "civil"})
        self.case.refresh_from_db()
        self.assertEqual(self.case.title, "New title")
        self.client.post(reverse("cases:delete", args=[self.case.pk]))
        self.assertFalse(Case.objects.filter(pk=self.case.pk).exists())

    def test_client_only_sees_own_cases(self):
        self.login(self.client_account)
        response = self.client.get(reverse("cases:list"))
        self.assertContains(response, "Land dispute")
        other = Account.objects.create_user(username="o", email="o@x.com", password="secret123", role=Account.CLIENT)
        from accounts.models import Client
        Client.objects.create(account=other, name="Other")
        self.client.logout()
        self.login(other)
        self.assertNotContains(self.client.get(reverse("cases:list")), "Land dispute")

    def test_lawyer_cannot_open_registered_case(self):
        self.login(self.lawyer_account)
        response = self.client.get(reverse("cases:detail", args=[self.case.pk]))
        self.assertRedirects(response, reverse("accounts:dashboard"))

    def test_search_filter(self):
        self.login(self.staff_account)
        self.assertContains(self.client.get(reverse("cases:list"), {"q": "Land"}), "Land dispute")
        self.assertNotContains(self.client.get(reverse("cases:list"), {"q": "zzz"}), "Land dispute")


class ConsentFlowTest(BaseTest):
    def test_client_consent_opens_case_and_notifies_lawyers(self):
        self.login(self.client_account)
        self.client.post(reverse("cases:consent", args=[self.case.pk]))
        self.case.refresh_from_db()
        self.assertTrue(self.case.consent)
        self.assertEqual(self.case.status, Case.OPEN)
        self.assertTrue(Notification.objects.filter(account=self.lawyer_account, case=self.case).exists())

    def test_other_client_cannot_give_consent(self):
        other = Account.objects.create_user(username="o", email="o@x.com", password="secret123", role=Account.CLIENT)
        from accounts.models import Client
        Client.objects.create(account=other, name="Other")
        self.login(other)
        self.client.post(reverse("cases:consent", args=[self.case.pk]))
        self.case.refresh_from_db()
        self.assertFalse(self.case.consent)


class HearingTest(BaseTest):
    def test_hearing_crud_and_notification(self):
        self.login(self.staff_account)
        when = (timezone.now() + timedelta(days=5)).strftime("%Y-%m-%dT10:00")
        self.client.post(reverse("cases:hearing_add", args=[self.case.pk]),
                         {"title": "First", "scheduled_at": when, "room": "2", "note": ""})
        hearing = Hearing.objects.get(case=self.case)
        self.assertTrue(Notification.objects.filter(account=self.client_account).exists())
        self.client.post(reverse("cases:hearing_edit", args=[hearing.pk]),
                         {"title": "Second", "scheduled_at": when, "room": "3", "note": ""})
        hearing.refresh_from_db()
        self.assertEqual(hearing.title, "Second")
        self.client.post(reverse("cases:hearing_delete", args=[hearing.pk]))
        self.assertEqual(Hearing.objects.count(), 0)

    def test_schedule_page_for_client(self):
        Hearing.objects.create(case=self.case, title="Visible", scheduled_at=timezone.now() + timedelta(days=2))
        self.login(self.client_account)
        self.assertContains(self.client.get(reverse("cases:schedule")), "Visible")


class NoteTest(BaseTest):
    def test_note_is_private_to_author(self):
        self.case.confirm_case()
        self.login(self.client_account)
        self.client.post(reverse("cases:note_add", args=[self.case.pk]), {"text": "my secret thought"})
        note = CaseNote.objects.get()
        self.assertContains(self.client.get(reverse("cases:detail", args=[self.case.pk])), "my secret thought")

        self.client.logout()
        self.login(self.staff_account)
        self.assertNotContains(self.client.get(reverse("cases:detail", args=[self.case.pk])), "my secret thought")
        self.client.post(reverse("cases:note_delete", args=[note.pk]))
        self.assertEqual(CaseNote.objects.count(), 1)

    def test_author_can_edit_and_delete(self):
        self.login(self.client_account)
        self.client.post(reverse("cases:note_add", args=[self.case.pk]), {"text": "one"})
        note = CaseNote.objects.get()
        self.client.post(reverse("cases:note_edit", args=[note.pk]), {"text": "two"})
        note.refresh_from_db()
        self.assertEqual(note.text, "two")
        self.client.post(reverse("cases:note_delete", args=[note.pk]))
        self.assertEqual(CaseNote.objects.count(), 0)
