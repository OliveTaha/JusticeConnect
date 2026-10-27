from django.test import TestCase

from accounts.models import Account, Client, Lawyer
from cases.models import Area, Case, Court, CourtStaff


class BaseTest(TestCase):
    """Makes one court, one staff, one client, one verified lawyer and one case."""

    def setUp(self):
        area = Area.objects.create(name="Dhaka")
        self.court = Court.objects.create(name="Dhaka Court", address="Old Dhaka", area=area)

        self.staff_account = Account.objects.create_user(
            username="staff", email="staff@x.com", password="secret123", role=Account.COURT_STAFF, is_verified=True)
        CourtStaff.objects.create(account=self.staff_account, court=self.court, name="Clerk", designation="Clerk")

        self.client_account = Account.objects.create_user(
            username="cl", email="cl@x.com", password="secret123", role=Account.CLIENT, is_verified=True)
        self.client_profile = Client.objects.create(account=self.client_account, name="Rahim")

        self.lawyer_account = Account.objects.create_user(
            username="adv", email="adv@x.com", password="secret123", role=Account.LAWYER, is_verified=True)
        self.lawyer = Lawyer.objects.create(account=self.lawyer_account, name="Adv One", bar_id="B1")

        self.case = Case.objects.create(
            case_number="C-1", title="Land dispute", description="Text", court=self.court, client=self.client_profile)

    def login(self, account):
        self.client.login(username=account.username, password="secret123")
