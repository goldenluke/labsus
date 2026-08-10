from django.urls import path
from . import views

urlpatterns = [
    path('trigger/', views.trigger_fluxo_pacientes_pipeline, name='fluxo-pacientes-trigger'),
    path('tasks/', views.FluxoPacientesTaskListView.as_view(), name='fluxo-pacientes-task-list'),
    path('tasks/<uuid:task_id>/status/', views.get_fluxo_pacientes_task_status, name='fluxo-pacientes-task-status'),
]
