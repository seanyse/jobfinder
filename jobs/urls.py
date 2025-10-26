from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='jobs.index'),
    path('create/', views.create_job, name='jobs.create_job'),
    path('<int:job_id>/', views.job_detail, name='jobs.detail'),
    path('<int:job_id>/edit/', views.edit_job, name='jobs.edit_job'),
    path('<int:job_id>/delete/', views.delete_job, name='jobs.delete_job'),
    path('map/', views.job_map, name='jobs.map'),
    
    # Application URLs
    path('<int:job_id>/apply/', views.apply_to_job, name='jobs.apply'),
    path('<int:job_id>/track/', views.track_status, name='jobs.track_status'),
    path('my-applications/', views.my_applications, name='jobs.my_applications'),
    path('manage-applications/', views.manage_applications, name='jobs.manage_applications'),
    path('applications/<int:application_id>/update/', views.update_application_status, name='jobs.update_application_status'),
]
