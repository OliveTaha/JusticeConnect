from django.urls import path

from . import views

app_name = "cases"

urlpatterns = [
    # for cases
    path("cases/", views.case_list, name="list"),
    path("cases/new/", views.case_create, name="create"),
    path("cases/<int:pk>/", views.case_detail, name="detail"),
    path("cases/<int:pk>/edit/", views.case_edit, name="edit"),
    path("cases/<int:pk>/delete/", views.case_delete, name="delete"),
    path("cases/<int:pk>/consent/", views.case_consent, name="consent"),
    path("cases/<int:pk>/close/", views.case_close, name="close"),
    path("schedule/", views.schedule, name="schedule"),
    path("cases/<int:case_pk>/hearings/add/", views.hearing_add, name="hearing_add"),
    path("hearings/<int:pk>/edit/", views.hearing_edit, name="hearing_edit"),
    path("hearings/<int:pk>/delete/", views.hearing_delete, name="hearing_delete"),

    # areas, courts, staff, report
    path("areas/", views.area_list, name="area_list"),
    path("areas/new/", views.area_create, name="area_create"),
    path("areas/<int:pk>/edit/", views.area_edit, name="area_edit"),
    path("areas/<int:pk>/delete/", views.area_delete, name="area_delete"),
    path("courts/", views.court_list, name="court_list"),
    path("courts/new/", views.court_create, name="court_create"),
    path("courts/<int:pk>/edit/", views.court_edit, name="court_edit"),
    path("courts/<int:pk>/delete/", views.court_delete, name="court_delete"),
    path("staff/", views.staff_list, name="staff_list"),
    path("staff/new/", views.staff_create, name="staff_create"),
    path("staff/<int:pk>/edit/", views.staff_edit, name="staff_edit"),
    path("staff/<int:pk>/delete/", views.staff_delete, name="staff_delete"),
    path("report/", views.court_report, name="court_report"),
    path("holidays/", views.holiday_list, name="holiday_list"),
    path("holidays/new/", views.holiday_add, name="holiday_add"),
    path("holidays/<int:pk>/edit/", views.holiday_edit, name="holiday_edit"),
    path("holidays/<int:pk>/delete/", views.holiday_delete, name="holiday_delete"),

    # lawyer requests, chat, appointments
    path("open-cases/", views.available_cases, name="available"),
    path("cases/<int:case_pk>/request/", views.request_send, name="request_send"),
    path("my-requests/", views.my_requests, name="my_requests"),
    path("lawyer-requests/", views.client_requests, name="client_requests"),
    path("requests/<int:pk>/accept/", views.request_accept, name="request_accept"),
    path("requests/<int:pk>/reject/", views.request_reject, name="request_reject"),
    path("requests/<int:pk>/withdraw/", views.request_withdraw, name="request_withdraw"),
    path("requests/<int:pk>/chat/", views.chat, name="chat"),
    path("appointments/", views.appointment_list, name="appointment_list"),
    path("cases/<int:case_pk>/appointments/new/", views.appointment_add, name="appointment_add"),
    path("appointments/<int:pk>/edit/", views.appointment_edit, name="appointment_edit"),
    path("appointments/<int:pk>/delete/", views.appointment_delete, name="appointment_delete"),
    path("appointments/<int:pk>/<str:answer>/", views.appointment_respond, name="appointment_respond"),

    # documents and reviews
    path("cases/<int:case_pk>/documents/add/", views.document_add, name="document_add"),
    path("documents/<int:pk>/", views.document_download, name="document_download"),
    path("documents/<int:pk>/edit/", views.document_edit, name="document_edit"),
    path("documents/<int:pk>/delete/", views.document_delete, name="document_delete"),
    path("cases/<int:case_pk>/notes/add/", views.note_add, name="note_add"),
    path("notes/<int:pk>/edit/", views.note_edit, name="note_edit"),
    path("notes/<int:pk>/delete/", views.note_delete, name="note_delete"),
    path("cases/<int:case_pk>/review/", views.review_add, name="review_add"),
    path("reviews/<int:pk>/edit/", views.review_edit, name="review_edit"),
    path("reviews/<int:pk>/delete/", views.review_delete, name="review_delete"),
]
