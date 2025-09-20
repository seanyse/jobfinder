from django.urls import path
from . import views
urlpatterns = [
    path('', views.index, name='jobs.index'),
    path('create/', views.create_job, name='jobs.create_job'),
]