from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("tracker.urls")),
]

# Custom 500 page (used when DEBUG is off): shows the request_id as a reference code.
handler500 = "tracker.views.server_error"
