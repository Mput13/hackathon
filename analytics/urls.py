from django.urls import path
from . import views

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('compare/', views.compare_versions, name='compare'),
    path('issues/', views.issues_list, name='issues_list'),
]
