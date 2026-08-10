# api/pipeline_kmeans/admin.py

from django.contrib import admin
from .models import KMeansTaskStatus

@admin.register(KMeansTaskStatus)
class KMeansTaskStatusAdmin(admin.ModelAdmin):
    list_display = ('task_id', 'user', 'status', 'n_clusters', 'created_at', 'output_file')
    list_filter = ('status', 'n_clusters', 'created_at', 'user')
    search_fields = ('task_id', 'user__username', 'input_file__filename', 'output_file__filename')
    readonly_fields = ('task_id', 'created_at', 'updated_at')
    fieldsets = (
        (None, {
            'fields': ('task_id', 'user', 'status', 'message', 'input_file', 'output_file')
        }),
        ('Configuração do K-Means', {
            'fields': ('n_clusters', 'features_for_clustering')
        }),
        ('Datas', {
            'fields': ('created_at', 'updated_at')
        })
    )
