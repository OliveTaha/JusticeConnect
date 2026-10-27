from datetime import timedelta

from django.urls import reverse
from django.utils import timezone

from accounts.models import Account, Lawyer
from cases.models import Appointment, Case, CaseRequest, Message, Review, hide_contact_details
from .base import BaseTest


class LawyerRequestTest(BaseTest):
    def setUp(self):
        super().setUp()
        self.case.confirm_case()

    def second_lawyer(self):
        account = Account.objects.create_user(
            username="adv2", email="adv2@x.com", password="secret123", role=Account.LAWYER, is_verified=True)
        return Lawyer.objects.create(account=account, name="Adv Two", bar_id="B2")

    def test_verified_lawyer_sees_open_case(self):
        self.login(self.lawyer_account)
        self.assertContains(self.client.get(reverse("cases:available")), "Land dispute")

    def test_unverified_lawyer_cannot_see_open_cases(self):
        self.lawyer_account.is_verified = False
        self.lawyer_account.save()
        self.login(self.lawyer_account)
        self.assertEqual(self.client.get(reverse("cases:available")).status_code, 302)

    def test_request_sent_once(self):
        self.login(self.lawyer_account)
        url = reverse("cases:request_send", args=[self.case.pk])
        self.client.post(url, {"message": "I can help"})
        self.client.post(url, {"message": "again"})
        self.assertEqual(CaseRequest.objects.count(), 1)

    def test_withdraw(self):
        self.login(self.lawyer_account)
        self.client.post(reverse("cases:request_send", args=[self.case.pk]), {"message": ""})
        req = CaseRequest.objects.get()
        self.client.post(reverse("cases:request_withdraw", args=[req.pk]))
        req.refresh_from_db()
        self.assertEqual(req.status, CaseRequest.WITHDRAWN)

    def test_client_selects_one_lawyer_and_others_are_rejected(self):
        other = self.second_lawyer()
        first = CaseRequest.submit_request(self.case, self.lawyer)
        second = CaseRequest.submit_request(self.case, other)
        self.login(self.client_account)
        self.client.post(reverse("cases:request_accept", args=[first.pk]))
        self.case.refresh_from_db()
        first.refresh_from_db()
        second.refresh_from_db()
        self.assertEqual(self.case.status, Case.ASSIGNED)
        self.assertEqual(self.case.assigned_lawyer, self.lawyer)
        self.assertEqual(first.status, CaseRequest.ACCEPTED)
        self.assertEqual(second.status, CaseRequest.REJECTED)

    def test_client_can_reject(self):
        req = CaseRequest.submit_request(self.case, self.lawyer)
        self.login(self.client_account)
        self.client.post(reverse("cases:request_reject", args=[req.pk]))
        req.refresh_from_db()
        self.assertEqual(req.status, CaseRequest.REJECTED)

    def test_client_request_inbox(self):
        CaseRequest.submit_request(self.case, self.lawyer, "Hello")
        self.login(self.client_account)
        self.assertContains(self.client.get(reverse("cases:client_requests")), "Adv One")


class ChatTest(BaseTest):
    def setUp(self):
        super().setUp()
        self.case.confirm_case()
        self.req = CaseRequest.submit_request(self.case, self.lawyer)

    def test_contact_details_are_hidden(self):
        text = hide_contact_details("call me 01712345678 or mail a@b.com")
        self.assertNotIn("01712345678", text)
        self.assertNotIn("a@b.com", text)

    def test_message_is_saved_hidden_and_unread(self):
        self.login(self.lawyer_account)
        self.client.post(reverse("cases:chat", args=[self.req.pk]), {"body": "my mail a@b.com"})
        message = Message.objects.get()
        self.assertNotIn("a@b.com", message.body)
        self.assertFalse(message.is_read)
        self.assertEqual(self.req.unread_for_client, 1)

    def test_opening_chat_marks_read(self):
        Message.send(self.req, self.lawyer_account, "Hello")
        self.login(self.client_account)
        self.client.get(reverse("cases:chat", args=[self.req.pk]))
        self.assertEqual(self.req.unread_for_client, 0)

    def test_stranger_cannot_open_chat(self):
        stranger = Account.objects.create_user(username="s", email="s@x.com", password="secret123", role=Account.CLIENT)
        self.login(stranger)
        response = self.client.get(reverse("cases:chat", args=[self.req.pk]))
        self.assertRedirects(response, reverse("accounts:dashboard"))


class CloseAndReviewTest(BaseTest):
    def setUp(self):
        super().setUp()
        self.case.confirm_case()
        req = CaseRequest.submit_request(self.case, self.lawyer)
        req.accept()
        self.case.refresh_from_db()

    def test_lawyer_closes_case(self):
        self.login(self.lawyer_account)
        self.client.post(reverse("cases:close", args=[self.case.pk]))
        self.case.refresh_from_db()
        self.assertEqual(self.case.status, Case.CLOSED)
        self.assertEqual(self.lawyer.solved_cases, 1)

    def test_client_cannot_close_case(self):
        self.login(self.client_account)
        self.client.post(reverse("cases:close", args=[self.case.pk]))
        self.case.refresh_from_db()
        self.assertEqual(self.case.status, Case.ASSIGNED)

    def test_review_crud_only_after_close(self):
        self.login(self.client_account)
        add = reverse("cases:review_add", args=[self.case.pk])
        self.client.post(add, {"rating": 5, "comment": "Great"})
        self.assertEqual(Review.objects.count(), 0)

        self.case.close_case()
        self.client.post(add, {"rating": 5, "comment": "Great"})
        review = Review.objects.get()
        self.assertEqual(self.lawyer.average_rating, 5)
        self.client.post(reverse("cases:review_edit", args=[review.pk]), {"rating": 3, "comment": "Ok"})
        review.refresh_from_db()
        self.assertEqual(review.rating, 3)
        self.client.post(reverse("cases:review_delete", args=[review.pk]))
        self.assertEqual(Review.objects.count(), 0)


class AppointmentTest(BaseTest):
    def setUp(self):
        super().setUp()
        self.case.confirm_case()
        CaseRequest.submit_request(self.case, self.lawyer).accept()
        self.when = (timezone.now() + timedelta(days=3)).strftime("%Y-%m-%dT11:00")

    def test_create_edit_delete_while_pending(self):
        self.login(self.client_account)
        self.client.post(reverse("cases:appointment_add", args=[self.case.pk]), {"purpose": "Discuss", "scheduled_at": self.when})
        appointment = Appointment.objects.get()
        self.assertEqual(appointment.status, Appointment.PENDING)
        self.client.post(reverse("cases:appointment_edit", args=[appointment.pk]), {"purpose": "New topic", "scheduled_at": self.when})
        appointment.refresh_from_db()
        self.assertEqual(appointment.purpose, "New topic")
        self.client.post(reverse("cases:appointment_delete", args=[appointment.pk]))
        self.assertEqual(Appointment.objects.count(), 0)

    def test_other_side_confirms_then_edit_is_blocked(self):
        self.login(self.client_account)
        self.client.post(reverse("cases:appointment_add", args=[self.case.pk]), {"purpose": "Discuss", "scheduled_at": self.when})
        appointment = Appointment.objects.get()
        self.client.logout()
        self.login(self.lawyer_account)
        self.client.post(reverse("cases:appointment_respond", args=[appointment.pk, "confirm"]))
        appointment.refresh_from_db()
        self.assertEqual(appointment.status, Appointment.CONFIRMED)
        self.client.logout()
        self.login(self.client_account)
        self.client.post(reverse("cases:appointment_edit", args=[appointment.pk]), {"purpose": "Changed", "scheduled_at": self.when})
        appointment.refresh_from_db()
        self.assertEqual(appointment.purpose, "Discuss")

    def test_past_time_is_rejected(self):
        self.login(self.client_account)
        past = (timezone.now() - timedelta(days=1)).strftime("%Y-%m-%dT11:00")
        self.client.post(reverse("cases:appointment_add", args=[self.case.pk]), {"purpose": "Old", "scheduled_at": past})
        self.assertEqual(Appointment.objects.count(), 0)
