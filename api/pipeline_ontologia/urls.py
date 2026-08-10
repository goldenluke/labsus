from django.urls import path
from . import views

urlpatterns = [
    path('sparql/', views.sparql_proxy, name='ontologia-sparql-proxy'),
    path('classes/', views.classes_catalog, name='ontologia-classes-catalog'),
    path('stats/', views.store_stats, name='ontologia-store-stats'),
    path('chat/', views.chat_bpho, name='ontologia-chat'),
]
