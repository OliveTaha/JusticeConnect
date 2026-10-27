from django.urls import path

from . import views

app_name = "accounts"

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("register/", views.register, name="register"),
    path("login/", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),
    path("verify/<uuid:token>/", views.verify, name="verify"),
    path("lawyers/", views.lawyer_list, name="lawyer_list"),
    path("lawyers/<int:pk>/", views.lawyer_detail, name="lawyer_detail"),
    path("profile/edit/", views.profile_edit, name="profile_edit"),
    path("my-details/", views.client_profile_edit, name="client_profile_edit"),
    path("password/", views.change_password, name="change_password"),
    path("approvals/", views.approvals, name="approvals"),
    path("approvals/<int:pk>/verify/", views.lawyer_verify, name="lawyer_verify"),
    path("approvals/<int:pk>/reject/", views.lawyer_reject, name="lawyer_reject"),
]
