from django.db import connection
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render
from django.views.decorators.http import require_GET


@require_GET
def healthz(request):
    """Minimal liveness and database reachability. Reveals no versions or config."""
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
        return JsonResponse({"status": "ok"})
    except Exception:  # noqa: BLE001 - any database failure means unhealthy
        return JsonResponse({"status": "unavailable"}, status=503)


def rate_limited(request, exception=None):
    return render(request, "errors/429.html", status=429, headers={"Retry-After": "60"})


def forbidden(request, exception=None):
    return render(request, "errors/403.html", status=403)


def not_found(request, exception=None):
    return render(request, "errors/404.html", status=404)


def server_error(request):
    # Rendered without context processors that could touch the database.
    from django.template import loader

    return HttpResponse(loader.get_template("errors/500.html").render(), status=500)
