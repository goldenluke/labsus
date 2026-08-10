# api/pipeline_predicao_internacoes/admin.py

from django.contrib import admin
from .models import PredictionTaskStatus

@admin.register(PredictionTaskStatus)
class PredictionTaskStatusAdmin(admin.ModelAdmin):
    list_display = ('task_id', 'user', 'status', 'created_at', 'output_file', 'meses_previsao')
    list_filter = ('status', 'created_at', 'user', 'meses_previsao')
    search_fields = ('task_id', 'user__username', 'cid_codes', 'ufs')
    readonly_fields = ('task_id', 'created_at', 'updated_at')
    fieldsets = (
        (None, {
            'fields': ('task_id', 'user', 'status', 'message', 'output_file')
        }),
        ('Parâmetros da Predição', {
            'fields': ('ufs', 'anos_historico', 'cid_codes', 'meses_previsao')
        }),
        ('Datas', {
            'fields': ('created_at', 'updated_at')
        })
    )
