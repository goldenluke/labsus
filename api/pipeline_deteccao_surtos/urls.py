from django.urls import path
from . import views

urlpatterns = [
    path('trigger/', views.trigger_outbreak_detection, name='deteccao-surtos-trigger'),
    path('gravos/', views.list_gravos, name='deteccao-surtos-gravos'),
    path('tasks/', views.DeteccaoSurtosTaskListView.as_view(), name='deteccao-surtos-task-list'),
    path('tasks/<uuid:pk>/', views.DeteccaoSurtosTaskDetailView.as_view(), name='deteccao-surtos-task-detail'),
    path('tasks/<uuid:task_id>/status/', views.get_outbreak_task_status, name='deteccao-surtos-task-status'),
]
