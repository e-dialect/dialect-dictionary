from django.conf import settings
from django.contrib import admin
from django.db import connection
from django.http import JsonResponse
from django.urls import include, path, re_path
from django.views.static import serve
from django.views.decorators.http import require_GET
from .import_media import dictionary_media, dictionary_legacy_file


@require_GET
def health(request):
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
    except Exception:
        return JsonResponse({"status": "unavailable"}, status=503)
    return JsonResponse(
        {
            "status": "ok",
            "name": settings.SITE_CONFIG["name"],
            "dialect": settings.SITE_CONFIG["dialect"],
        }
    )


@require_GET
def site_config(request):
    return JsonResponse(settings.SITE_CONFIG)


admin.site.site_header = settings.SITE_CONFIG["name"]
admin.site.site_title = settings.SITE_CONFIG["shortName"]
urlpatterns = [
    path("healthz", health),
    path("site-config", site_config),
    re_path(r"^media/(?P<path>.*)$", dictionary_media),
    re_path(r"^static/(?P<path>.*)$", serve, {"document_root": settings.STATIC_ROOT}),
    path("files/<type>/<id>/<Y>/<M>/<D>/<X>", dictionary_legacy_file),
    path("", include("HinghwaDict.urls")),
]
