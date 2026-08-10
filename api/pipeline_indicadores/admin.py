# api/pipeline_indicadores/admin.py

from django.contrib import admin
from .models import IntegracaoTaskStatus # Importe o modelo

@admin.register(IntegracaoTaskStatus)
class IntegracaoTaskStatusAdmin(admin.ModelAdmin):
    list_display = ('task_id', 'user', 'status', 'created_at', 'output_file')
    list_filter = ('status', 'created_at', 'user')
    search_fields = ('task_id', 'user__username', 'input_files')
    readonly_fields = ('task_id', 'created_at', 'updated_at')
    fieldsets = (
        (None, {
            'fields': ('task_id', 'user', 'status', 'message', 'input_files', 'output_file')
        }),
        ('Datas', {
            'fields': ('created_at', 'updated_at')
        })
    )
