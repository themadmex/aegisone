from django.urls import include, path

from apps.core import views as core_views

# Django admin is intentionally not mounted (TRD: public admin disabled).
urlpatterns = [
    path("", core_views.home, name="home"),
    path("healthz", core_views.healthz, name="healthz"),
    path("help", core_views.information, {"section": "help"}, name="help"),
    path("privacy", core_views.information, {"section": "privacy"}, name="privacy"),
    path("pilot", core_views.information, {"section": "pilot"}, name="pilot"),
    path("", include("apps.accounts.urls")),
    path("", include("apps.workspaces.urls")),
    path("", include("apps.posture.urls")),
]

handler403 = "apps.core.views.forbidden"
handler404 = "apps.core.views.not_found"
handler500 = "apps.core.views.server_error"
