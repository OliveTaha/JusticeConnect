from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from accounts.models import Account, Client, Lawyer, Profile
from cases.models import (Appointment, Area, Case, CaseRequest, Court, CourtStaff, Hearing,
                         CourtHoliday, Message, Review)


def make_lawyer(username, name, bar_id, specialization, experience, bio=""):
    account = Account.objects.create_user(
        username=username, email=f"{username}@example.com", password="Lawyer@12345",
        role=Account.LAWYER, is_verified=True,
    )
    lawyer = Lawyer.objects.create(account=account, name=name, bar_id=bar_id)
    Profile.objects.create(account=account, name=name, specialization=specialization, experience=experience, bio=bio)
    return lawyer


def make_client(username, name, phone):
    account = Account.objects.create_user(
        username=username, email=f"{username}@example.com", password="Client@12345",
        role=Account.CLIENT, is_verified=True,
    )
    return Client.objects.create(account=account, name=name, phone=phone, address="Dhaka")


class Command(BaseCommand):
    help = "Adds demo areas, courts, an admin, court staff and lawyers. Use --sample to add example cases too."

    def add_arguments(self, parser):
        parser.add_argument("--sample", action="store_true", help="also add example clients and cases")

    def handle(self, *args, **options):
        if Account.objects.filter(username="admin").exists():
            self.stdout.write("Demo data already exists.")
            return

        Account.objects.create_superuser(username="admin", email="admin@example.com", password="Admin@12345")

        dhaka = Area.objects.create(name="Dhaka")
        ctg = Area.objects.create(name="Chattogram")
        Area.objects.create(name="Rajshahi")
        dhaka_court = Court.objects.create(name="Dhaka District Court", address="Old Dhaka", area=dhaka)
        Court.objects.create(name="Chattogram District Court", address="Court Hill", area=ctg)

        staff_account = Account.objects.create_user(
            username="court", email="court@example.com", password="Court@12345",
            role=Account.COURT_STAFF, is_verified=True,
        )
        CourtStaff.objects.create(account=staff_account, court=dhaka_court, name="Kamal Hossain", designation="Court clerk")

        today = timezone.localdate()
        CourtHoliday.objects.create(court=dhaka_court, date=today + timedelta(days=12), reason="Public holiday")
        CourtHoliday.objects.create(court=dhaka_court, date=today + timedelta(days=30), reason="Court vacation")

        demo = make_lawyer("lawyer", "Demo Lawyer", "BAR-001", "Civil law", 5, "Handles civil and contract cases.")
        if options["sample"]:
            self.add_sample(dhaka_court, demo)

        self.stdout.write(self.style.SUCCESS("Demo data added."))
        self.stdout.write("Admin:       admin@example.com / Admin@12345")
        self.stdout.write("Court staff: court@example.com / Court@12345")
        self.stdout.write("Lawyer:      lawyer@example.com / Lawyer@12345")
        if options["sample"]:
            self.stdout.write("Client:      client@example.com / Client@12345")

    def add_sample(self, court, demo_lawyer):
        nusrat = make_lawyer("nusrat", "Nusrat Jahan", "BAR-014", "Family and property law", 9, "Nine years in district courts, mostly family and land matters.")
        imran = make_lawyer("imran", "Imran Hossain", "BAR-022", "Criminal law", 12, "Criminal defence and bail hearings.")
        rahim = make_client("client", "Rahim Uddin", "01711000000")
        salma = make_client("salma", "Salma Begum", "01811000000")
        staff = court.staff_members.first().account
        now = timezone.now()

        # 1. a running case with a lawyer, a hearing and an appointment
        land = Case.objects.create(case_number="DC-2026-014", title="Land boundary dispute in Savar", description="Neighbour built a wall 2 feet inside our plot. Survey papers attached.", case_type="property", court=court, client=rahim)
        land.log("Case registered by Kamal Hossain.", staff)
        land.confirm_case()
        request = CaseRequest.submit_request(land, nusrat, "I have handled three boundary cases in Savar.")
        Message.send(request, nusrat.account, "Hello, I read the case summary. Can you share the survey map?")
        Message.send(request, rahim.account, "Yes, I will upload it today.")
        request.accept()
        Hearing.objects.create(case=land, title="First hearing", scheduled_at=now + timedelta(days=6, hours=3), room="Room 4", created_by=staff)
        Appointment.objects.create(case=land, created_by=rahim.account, purpose="Go through the survey map", scheduled_at=now + timedelta(days=2, hours=1))

        # 2. an open case with two requests
        tenant = Case.objects.create(case_number="DC-2026-021", title="Tenant eviction notice", description="Landlord sent an eviction notice without the 3 month period.", case_type="civil", court=court, client=rahim)
        tenant.log("Case registered by Kamal Hossain.", staff)
        tenant.confirm_case()
        CaseRequest.submit_request(tenant, demo_lawyer, "I can start with a legal reply to the notice.")
        CaseRequest.submit_request(tenant, imran, "")

        # 3. waiting for the client
        inherit = Case.objects.create(case_number="DC-2026-027", title="Inheritance share of agricultural land", description="Three brothers, one has sold land without the others.", case_type="family", court=court, client=rahim)
        inherit.log("Case registered by Kamal Hossain.", staff)

        # 4. a closed case with a review
        cheque = Case.objects.create(case_number="DC-2026-009", title="Cheque dishonour complaint", description="Cheque of 2,50,000 BDT returned by the bank.", case_type="criminal", court=court, client=salma)
        cheque.log("Case registered by Kamal Hossain.", staff)
        cheque.confirm_case()
        CaseRequest.submit_request(cheque, imran, "").accept()
        cheque.close_case()
        Review.objects.create(case=cheque, lawyer=imran, client=salma, rating=5, comment="Clear updates after every hearing.")
        Hearing.objects.create(case=cheque, title="Final hearing", scheduled_at=now - timedelta(days=12), room="Room 2", created_by=staff)
