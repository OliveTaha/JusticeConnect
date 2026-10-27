from django.urls import path

from . import views

app_name = "cases"

urlpatterns = [
    # cases
    path("cases/", views.case_list, name="list"),
    path("cases/new/", views.case_create, name="create"),
    path("cases/<int:pk>/", views.case_detail, name="detail"),
    path("cases/<int:pk>/consent/", views.case_consent, name="consent"),
    path("cases/<int:pk>/close/", views.case_close, name="close"),
    path("schedule/", views.schedule, name="schedule"),
    path("cases/<int:case_pk>/hearings/add/", views.hearing_add, name="hearing_add"),
    path("hearings/<int:pk>/edit/", views.hearing_edit, name="hearing_edit"),
    path("hearings/<int:pk>/delete/", views.hearing_delete, name="hearing_delete"),
    path("areas/", views.area_list, name="area_list"),
    path("areas/new/", views.area_create, name="area_create"),
    path("areas/<int:pk>/edit/", views.area_edit, name="area_edit"),
    path("areas/<int:pk>/delete/", views.area_delete, name="area_delete"),
    path("courts/", views.court_list, name="court_list"),
    path("courts/new/", views.court_create, name="court_create"),
    path("courts/<int:pk>/edit/", views.court_edit, name="court_edit"),
    path("courts/<int:pk>/delete/", views.court_delete, name="court_delete"),
    path("staff/", views.staff_list, name="staff_list"),
]
