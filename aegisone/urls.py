from django.urls import include, path

from apps.core import views as core_views

# Django admin is intentionally not mounted (TRD: public admin disabled).
urlpatterns = [
    path("healthz", core_views.healthz, name="healthz"),
    path("", include("apps.accounts.urls")),
    path("", include("apps.workspaces.urls")),
]

handler403 = "apps.core.views.forbidden"
handler404 = "apps.core.views.not_found"
handler500 = "apps.core.views.server_error"
