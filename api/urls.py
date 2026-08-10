# === Início do arquivo: api/urls.py ===

from django.urls import path, include
from .views import (
    ManagedFileListCreateAPIView,
    ManagedFileDataAPIView,
    ManagedFileDetailAPIView,
    set_csrf_cookie,
    get_geojson_for_uf,
    save_archetype_csv,
    GoogleLoginView,
)

urlpatterns = [
    # Rota para listar todos os arquivos (GET) ou criar um novo (POST)
    path('files/', ManagedFileListCreateAPIView.as_view(), name='file-list-create'),

    # Rota para um arquivo específico: obter detalhes (GET), atualizar (PUT/PATCH), ou excluir (DELETE)
    path('files/<int:pk>/', ManagedFileDetailAPIView.as_view(), name='file-detail'),

    # Rota para obter o conteúdo de dados (JSON) de um arquivo específico
    path('files/<int:pk>/data/', ManagedFileDataAPIView.as_view(), name='file-data-detail'),

    # Rotas de Autenticação e CSRF
    path('auth/google/', GoogleLoginView.as_view(), name='google_login'),
    path('auth/', include('dj_rest_auth.urls')),
    path('auth/registration/', include('dj_rest_auth.registration.urls')),
    path('csrf/', set_csrf_cookie, name='set-csrf-cookie'),

    # Rotas para dados geoespaciais e utilidades
    path('geojson/<str:uf>/', get_geojson_for_uf, name='get-geojson-for-uf'),
    path('archetypes/save/', save_archetype_csv, name='save-archetype-csv'),
]
