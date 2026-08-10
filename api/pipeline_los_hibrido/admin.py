from django.contrib import admin
from .models import LosHibridoTaskStatus

@admin.register(LosHibridoTaskStatus)
class LosHibridoTaskStatusAdmin(admin.ModelAdmin):
    list_display = ('task_id', 'user', 'status', 'departamento', 'previsao_dias', 'permanencia_classificada', 'created_at')
    list_filter = ('status', 'departamento')
    search_fields = ('task_id', 'user__username')
    readonly_fields = ('task_id', 'created_at', 'updated_at')
