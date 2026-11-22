from django.urls import path

from . import views

app_name = "workspaces"

urlpatterns = [
    path("", views.overview, name="overview"),
    path("workspaces/switch", views.switch, name="switch"),
    path("settings/members", views.members, name="members"),
    path("settings/members/invite", views.invite, name="invite"),
    path("settings/members/invitations/<uuid:invitation_id>/resend", views.resend_invite, name="resend_invite"),
    path("settings/members/invitations/<uuid:invitation_id>/cancel", views.cancel_invite, name="cancel_invite"),
    path("settings/members/<uuid:membership_id>/remove", views.remove_member, name="remove_member"),
]
