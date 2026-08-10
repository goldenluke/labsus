from django.urls import path
from . import views

urlpatterns = [
    path('facility/<str:cnes>/', views.facility_validity, name='cnes-validity-facility'),
    path('summary/', views.summary, name='cnes-validity-summary'),
]
