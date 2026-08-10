from django.urls import path
from . import views

urlpatterns = [
    path('facility/<str:cnes>/', views.facility_vitals, name='registros-vitais-facility'),
    path('summary/', views.summary, name='registros-vitais-summary'),
]
