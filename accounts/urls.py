from django.urls import path
from . import views
urlpatterns = [
    path('contact/<str:username>/', views.contact_candidate, name='accounts.contact_candidate'),
    path('signup', views.signup, name='accounts.signup'),
    path('login/', views.login, name='accounts.login'),
    path('logout/', views.logout, name='accounts.logout'),

    path('profile/me/', views.my_profile, name='accounts.my_profile'),
    path('profile/edit/', views.profile_edit, name='accounts.profile_edit'),
    path('profile/<str:username>/', views.profile_detail, name='accounts.profile_detail'),
    path('recruiter/search/', views.candidate_search, name='accounts.candidate_search'),
    
]
