from django.contrib import admin

from .models import (Appointment, Area, Case, CaseDocument, CaseEvent, CaseNote, CaseRequest,
                     Court, CourtHoliday, CourtStaff, Hearing, Message, Review)


@admin.register(Case)
class CaseAdmin(admin.ModelAdmin):
    list_display = ("case_number", "title", "court", "status", "assigned_lawyer")
    list_filter = ("status", "case_type", "court")
    search_fields = ("case_number", "title")


for model in (Area, Court, CourtStaff, CourtHoliday, CaseEvent, Hearing, CaseRequest,
              Message, Appointment, CaseDocument, CaseNote, Review):
    admin.site.register(model)
