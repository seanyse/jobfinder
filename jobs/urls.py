from django.urls import path
from . import views
urlpatterns = [
    path('', views.index, name='jobs.index'),
    path('create/', views.create_job, name='jobs.create_job'),
    path('<int:job_id>/edit/', views.edit_job, name='jobs.edit_job'),
    path('<int:job_id>/delete/', views.delete_job, name='jobs.delete_job'),
]