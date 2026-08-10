# api/admin.py

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User
from .models import ManagedFile, Profile # Importe ManagedFile

# Register your models here.


class ProfileInline(admin.StackedInline):
    model = Profile
    can_delete = False
    verbose_name_plural = "Acesso à BPHO/PopulationSpace"


class CustomUserAdmin(UserAdmin):
    inlines = (ProfileInline,)
    list_display = UserAdmin.list_display + ('has_bpho_access',)

    def has_bpho_access(self, obj):
        return getattr(obj.profile, 'has_bpho_access', False)
    has_bpho_access.boolean = True
    has_bpho_access.short_description = "Acesso BPHO"


admin.site.unregister(User)
admin.site.register(User, CustomUserAdmin)


@admin.register(ManagedFile)
class ManagedFileAdmin(admin.ModelAdmin):
    # Campos a serem exibidos na lista do admin
    list_display = ('filename', 'uploader', 'uploaded_at', 'file_type')
    # Campos que podem ser editados no formulário de detalhes
    fields = ('filename', 'description', 'file_type', 'file', 'uploader')
    # Adicionar filtros por tipo de arquivo
    list_filter = ('file_type', 'uploader')
    # Adicionar busca
    search_fields = ('filename', 'description', 'uploader__username')
