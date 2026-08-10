from django.contrib import admin
from .models import FluxoPacientesTaskStatus

@admin.register(FluxoPacientesTaskStatus)
class FluxoPacientesTaskStatusAdmin(admin.ModelAdmin):
    # ⭐ REMOVIDO 'diagnostico_nome' ⭐
    list_display = ('task_id', 'user', 'status', 'created_at')
    list_filter = ('status', 'user')
    search_fields = ('task_id', 'user__username', 'diagnostico_cids')
