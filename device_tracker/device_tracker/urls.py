from django.urls import path, include


urlpatterns = [
    path("collector/api/v1/", include("collector.urls")),
]
