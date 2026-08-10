from django.contrib import admin
from .models import PerinatalTaskStatus

@admin.register(PerinatalTaskStatus)
class PerinatalTaskStatusAdmin(admin.ModelAdmin):
    list_display = ('task_id', 'user', 'status', 'risk_score', 'risk_classification', 'created_at')
    list_filter = ('status', 'risk_classification', 'created_at')
    search_fields = ('task_id',)
    readonly_fields = ('task_id', 'created_at', 'updated_at', 'patient_data')
