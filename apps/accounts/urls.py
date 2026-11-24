from django.urls import path

from . import views

app_name = "accounts"

urlpatterns = [
    path("signin", views.sign_in, name="sign_in"),
    path("signout", views.sign_out, name="sign_out"),
    path("signin/verify", views.mfa_step, name="mfa"),
    path("profile", views.profile, name="profile"),
    path("profile/password", views.change_password, name="change_password"),
    path("recovery", views.recovery_request, name="recovery"),
    path("recovery/<str:token>", views.recovery_confirm, name="recovery_confirm"),
    path("invite/<str:token>", views.accept_invite, name="accept_invite"),
]
