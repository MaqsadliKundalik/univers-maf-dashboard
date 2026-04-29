from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('group/<uuid:token>/', views.group_stats, name='group_stats'),
    path('api/generate-link/', views.generate_group_link, name='generate_group_link'),
]
