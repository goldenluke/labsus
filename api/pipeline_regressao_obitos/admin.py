from django.contrib import admin
from .models import RegressaoObitosTaskStatus

@admin.register(RegressaoObitosTaskStatus)
class RegressaoObitosTaskStatusAdmin(admin.ModelAdmin):
    list_display = ('task_id', 'user', 'status', 'created_at', 'output_file')
    list_filter = ('status', 'user', 'created_at')
    search_fields = ('task_id', 'user__username', 'diagnostico_cids')
    readonly_fields = ('task_id', 'created_at', 'updated_at', 'results_summary')
