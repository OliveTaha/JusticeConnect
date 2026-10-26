from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("accounts.urls")),
    path("", include("cases.urls")),
    path("notifications/", include("notifications.urls")),
]

# profile photos are served by django while developing
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
