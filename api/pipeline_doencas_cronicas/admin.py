from django.contrib import admin
from .models import DoencasCronicasTaskStatus

@admin.register(DoencasCronicasTaskStatus)
class DoencasCronicasTaskStatusAdmin(admin.ModelAdmin):
    list_display = ('task_id', 'user', 'status', 'uf', 'cid_doenca', 'ano_snapshot', 'n_pacientes_coorte', 'roc_auc', 'created_at')
    list_filter = ('status', 'uf', 'cid_doenca', 'created_at')
    search_fields = ('task_id',)
    readonly_fields = ('task_id', 'created_at', 'updated_at')
