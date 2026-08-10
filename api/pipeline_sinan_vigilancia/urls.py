from django.urls import path
from . import views

urlpatterns = [
    path('bases/', views.bases_disponiveis, name='sinan-vigilancia-bases'),
    path('summary/', views.summary, name='sinan-vigilancia-summary'),
    path('agravo/<str:code>/', views.agravo_lookup, name='sinan-vigilancia-agravo'),
]
