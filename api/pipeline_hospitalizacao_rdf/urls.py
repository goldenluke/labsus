from django.urls import path
from . import views

urlpatterns = [
    path('trigger/', views.trigger_hospitalizacao_rdf_pipeline, name='hospitalizacao-rdf-trigger'),
    path('tasks/', views.HospitalizacaoRDFTaskListView.as_view(), name='hospitalizacao-rdf-task-list'),
    path('tasks/<uuid:pk>/', views.HospitalizacaoRDFTaskDetailView.as_view(), name='hospitalizacao-rdf-task-detail'),
    path('tasks/<uuid:task_id>/status/', views.get_hospitalizacao_rdf_task_status, name='hospitalizacao-rdf-task-status'),
]
