from django.urls import path
from . import views
urlpatterns = [
    path('', views.index, name='home.index'),
    path('about', views.about, name="home.about"),

    path('jobs/map/', views.jobs_map, name='jobs.map'),      # UI page
    path("api/jobs/", views.jobs_geojson, name="api.jobs"),
]
