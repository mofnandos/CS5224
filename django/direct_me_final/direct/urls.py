from django.urls import path
from . import views

urlpatterns = [
    path('', views.locations, name="locations"),
    path('route/', views.get_direction, name="get_direction"),
]