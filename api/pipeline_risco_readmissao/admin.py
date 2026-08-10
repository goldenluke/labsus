from django.contrib import admin
from .models import ReadmissaoTaskStatus

@admin.register(ReadmissaoTaskStatus)
class ReadmissaoTaskStatusAdmin(admin.ModelAdmin):
    """
    Configuração da interface de administração para o modelo ReadmissaoTaskStatus.
    """
    list_display = ('task_id', 'user', 'status', 'risk_score', 'created_at', 'updated_at')
    list_filter = ('status', 'user', 'created_at')
    search_fields = ('task_id', 'user__username')

    # ⭐ CORREÇÃO: Removido 'results_summary' que não existe neste modelo.
    readonly_fields = ('task_id', 'created_at', 'updated_at', 'patient_data')
