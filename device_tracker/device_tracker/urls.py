from django.contrib import admin
from django.urls import path, include


urlpatterns = [
    path("collector/api/v1/", include("collector.urls")),
    path("admin-panel/", admin.site.urls),
]
