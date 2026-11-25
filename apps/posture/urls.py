from django.urls import path

from . import domains, reports, views

app_name = "posture"

urlpatterns = [
    path("assessment", views.assessment_home, name="assessment"),
    path("assessment/start", views.assessment_start, name="assessment_start"),
    path("assessment/<uuid:assessment_id>/question/<str:key>", views.question, name="question"),
    path("assessment/<uuid:assessment_id>/review", views.assessment_review, name="assessment_review"),
    path("assessment/<uuid:assessment_id>/submit", views.assessment_submit, name="assessment_submit"),
    path("actions", views.actions, name="actions"),
    path("actions/<uuid:action_id>", views.action_detail, name="action_detail"),
    path("reports", reports.reports, name="reports"),
    path("reports/preview", reports.report_preview, name="report_preview"),
    path("reports/<uuid:report_id>", reports.report_detail, name="report"),
    path("reports/<uuid:report_id>/revoke", reports.report_revoke, name="report_revoke"),
    path("settings/data", reports.data_requests, name="data_requests"),
    path("settings/data/<uuid:request_id>/export", reports.data_export, name="data_export"),
    path("domains", domains.domain_list, name="domains"),
    path("domains/<uuid:domain_id>", domains.domain_detail, name="domain_detail"),
    path("domains/<uuid:domain_id>/revoke", domains.domain_revoke, name="domain_revoke"),
]
