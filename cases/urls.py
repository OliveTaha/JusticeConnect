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
]
