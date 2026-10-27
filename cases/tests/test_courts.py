from datetime import timedelta

from django.urls import reverse
from django.utils import timezone

from cases.models import Area, Court, CourtHoliday, CourtStaff
from .base import BaseTest


class AreaCourtStaffTest(BaseTest):
    def setUp(self):
        super().setUp()
        self.admin = self.make_admin()
        self.login(self.admin)

    def make_admin(self):
        from accounts.models import Account
        return Account.objects.create_superuser(username="boss", email="boss@x.com", password="secret123")

    def test_area_crud(self):
        self.client.post(reverse("cases:area_create"), {"name": "Sylhet"})
        area = Area.objects.get(name="Sylhet")
        self.client.post(reverse("cases:area_edit", args=[area.pk]), {"name": "Sylhet City"})
        area.refresh_from_db()
        self.assertEqual(area.name, "Sylhet City")
        self.client.post(reverse("cases:area_delete", args=[area.pk]))
        self.assertFalse(Area.objects.filter(pk=area.pk).exists())

    def test_area_with_courts_cannot_be_deleted(self):
        self.client.post(reverse("cases:area_delete", args=[self.court.area.pk]))
        self.assertTrue(Area.objects.filter(pk=self.court.area.pk).exists())

    def test_court_crud(self):
        area = self.court.area
        self.client.post(reverse("cases:court_create"), {"name": "New Court", "address": "Here", "area": area.pk})
        court = Court.objects.get(name="New Court")
        self.client.post(reverse("cases:court_edit", args=[court.pk]), {"name": "Renamed", "address": "Here", "area": area.pk})
        court.refresh_from_db()
        self.assertEqual(court.name, "Renamed")
        self.client.post(reverse("cases:court_delete", args=[court.pk]))
        self.assertFalse(Court.objects.filter(pk=court.pk).exists())

    def test_court_staff_create_makes_account(self):
        data = {"username": "newstaff", "email": "ns@x.com", "password": "secret123",
                "name": "New Staff", "designation": "Clerk", "court": self.court.pk}
        self.client.post(reverse("cases:staff_create"), data)
        self.assertTrue(CourtStaff.objects.filter(name="New Staff", court=self.court).exists())

    def test_non_admin_cannot_open_area_list(self):
        self.client.logout()
        self.login(self.client_account)
        response = self.client.get(reverse("cases:area_list"))
        self.assertNotEqual(response.status_code, 200)


class HolidayTest(BaseTest):
    def setUp(self):
        super().setUp()
        self.login(self.staff_account)
        self.day = (timezone.now() + timedelta(days=10)).date()

    def test_holiday_crud(self):
        self.client.post(reverse("cases:holiday_add"), {"date": self.day, "reason": "Eid"})
        holiday = CourtHoliday.objects.get(court=self.court)
        self.client.post(reverse("cases:holiday_edit", args=[holiday.pk]), {"date": self.day, "reason": "Eid ul Fitr"})
        holiday.refresh_from_db()
        self.assertEqual(holiday.reason, "Eid ul Fitr")
        self.client.post(reverse("cases:holiday_delete", args=[holiday.pk]))
        self.assertEqual(CourtHoliday.objects.count(), 0)

    def test_same_day_twice_is_rejected(self):
        CourtHoliday.objects.create(court=self.court, date=self.day, reason="Eid")
        self.client.post(reverse("cases:holiday_add"), {"date": self.day, "reason": "Again"})
        self.assertEqual(CourtHoliday.objects.count(), 1)

    def test_hearing_on_holiday_is_rejected(self):
        CourtHoliday.objects.create(court=self.court, date=self.day, reason="Eid")
        data = {"title": "First hearing", "scheduled_at": f"{self.day}T10:00", "room": "1", "note": ""}
        response = self.client.post(reverse("cases:hearing_add", args=[self.case.pk]), data)
        self.assertContains(response, "The court is closed on this day.")
        self.assertEqual(self.case.hearings.count(), 0)

    def test_other_court_staff_cannot_edit_holiday(self):
        holiday = CourtHoliday.objects.create(court=self.court, date=self.day, reason="Eid")
        self.client.logout()
        self.login(self.client_account)
        self.client.post(reverse("cases:holiday_delete", args=[holiday.pk]))
        self.assertTrue(CourtHoliday.objects.filter(pk=holiday.pk).exists())
