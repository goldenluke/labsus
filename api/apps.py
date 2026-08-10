# api/apps.py

from django.apps import AppConfig

class ApiConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'api'

    def ready(self):
        """
        Este método é executado pelo Django quando o aplicativo 'api' está pronto.
        É o local perfeito para carregar os dados.
        """
        print("App 'api' pronto. A carregar dados GeoJSON para o cache...")

        # Registra os signal handlers (ex.: criação automática de Profile por usuário).
        from . import signals  # noqa: F401

        # Importamos as funções aqui dentro para garantir que tudo esteja pronto.
        # Note o '.' antes de dataloaders, indicando um import relativo.
        from .dataloaders import load_geojson_data
        from .cache import GEOJSON_CACHE

        # Carrega os dados e preenche o nosso dicionário de cache
        loaded_data = load_geojson_data()
        if loaded_data:
            GEOJSON_CACHE.update(loaded_data)
            print(f"{len(GEOJSON_CACHE)} arquivos GeoJSON carregados para o cache da API com sucesso.")
        else:
            print("AVISO: Nenhum dado GeoJSON foi carregado. Verifique os caminhos em api/dataloaders.py.")
