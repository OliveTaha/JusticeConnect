from django.urls import path

from . import views

app_name = "cases"

urlpatterns = [
    # cases
    path("cases/", views.case_list, name="list"),
    path("cases/new/", views.case_create, name="create"),
    path("cases/<int:pk>/", views.case_detail, name="detail"),

]
