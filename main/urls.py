from django.urls import path

from . import views


urlpatterns = [
    path('', views.index, name='index'),
    path('group/<uuid:token>/', views.group_stats, name='group_stats'),
    path('profile/<uuid:token>/', views.user_profile, name='user_profile'),
    path('api/generate-link/', views.generate_group_link, name='generate_group_link'),
    path('api/generate-profile-link/', views.generate_user_profile_link, name='generate_user_profile_link'),
]
