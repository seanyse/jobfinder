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
    path('profile/update-commute-radius', views.update_commute_radius, name='accounts.update_commute_radius'),
    
    # Saved search URLs
    path('recruiter/search/save/', views.save_candidate_search, name='accounts.save_search'),
    path('recruiter/saved-searches/', views.saved_searches_list, name='accounts.saved_searches'),
    path('recruiter/saved-searches/<int:search_id>/', views.saved_search_detail, name='accounts.saved_search_detail'),
    path('recruiter/saved-searches/<int:search_id>/delete/', views.delete_saved_search, name='accounts.delete_saved_search'),
    path('recruiter/saved-searches/<int:search_id>/toggle/', views.toggle_saved_search_active, name='accounts.toggle_saved_search'),
    
    # Messaging URLs
    path('messages/', views.conversations_list, name='accounts.conversations_list'),
    path('messages/<int:conversation_id>/', views.conversation_detail, name='accounts.conversation_detail'),
    path('messages/start/<int:candidate_id>/', views.start_conversation, name='accounts.start_conversation'),
    path('messages/start/<int:candidate_id>/job/<int:job_id>/', views.start_conversation_with_job, name='accounts.start_conversation_with_job'),
]
