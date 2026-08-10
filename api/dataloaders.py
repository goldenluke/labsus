import json
import logging
from pathlib import Path
import pandas as pd
from django.conf import settings

# Inicializa o logger
logger = logging.getLogger(__name__)

# --- INÍCIO DO CÓDIGO DE DEBUG ---
print("\n--- DEBUG DE CAMINHOS (dataloaders.py) ---")
print(f"[1] settings.BASE_DIR aponta para: {settings.BASE_DIR}")

# A linha abaixo é a nossa principal suspeita.
# Ela assume que a pasta 'cognisaude' está um nível acima da pasta 'backend_project'
BASE_DIR_CALCULADO = settings.BASE_DIR.parent
print(f"[2] BASE_DIR (pai) calculado é: {BASE_DIR_CALCULADO}")

CAMINHO_GEOJSON_BASE = BASE_DIR_CALCULADO / "referencia/espaciais/geojson/municipios"
print(f"[3] Caminho final para GeoJSONs é: {CAMINHO_GEOJSON_BASE}")
print(f"[4] A pasta neste caminho existe? -> {CAMINHO_GEOJSON_BASE.exists()}")
print("--- FIM DO DEBUG ---\n")
# --- FIM DO CÓDIGO DE DEBUG ---

GEOJSON_PATHS = {
    'AC': 'geojs-12-mun.json', 'AL': 'geojs-27-mun.json', 'AP': 'geojs-16-mun.json', 'AM': 'geojs-13-mun.json',
    'BA': 'geojs-29-mun.json', 'CE': 'geojs-23-mun.json', 'DF': 'geojs-53-mun.json', 'ES': 'geojs-32-mun.json',
    'GO': 'geojs-52-mun.json', 'MA': 'geojs-21-mun.json', 'MT': 'geojs-51-mun.json', 'MS': 'geojs-50-mun.json',
    'MG': 'geojs-31-mun.json', 'PA': 'geojs-15-mun.json', 'PB': 'geojs-25-mun.json', 'PR': 'geojs-41-mun.json',
    'PE': 'geojs-26-mun.json', 'PI': 'geojs-22-mun.json', 'RJ': 'geojs-33-mun.json', 'RN': 'geojs-24-mun.json',
    'RS': 'geojs-43-mun.json', 'RO': 'geojs-11-mun.json', 'RR': 'geojs-14-mun.json', 'SC': 'geojs-42-mun.json',
    'SP': 'geojs-35-mun.json', 'SE': 'geojs-28-mun.json', 'TO': 'geojs-17-mun.json',
    'BR': 'geojs-100-mun.json'
}

def load_geojson_data():
    geojsons_por_uf = {}
    if not CAMINHO_GEOJSON_BASE.exists():
        logger.error(f"CRÍTICO: A pasta base de GeoJSON não foi encontrada: {CAMINHO_GEOJSON_BASE}")
        return {}

    for uf, nome_arquivo in GEOJSON_PATHS.items():
        caminho_completo = CAMINHO_GEOJSON_BASE / nome_arquivo
        if caminho_completo.is_file():
            try:
                with open(caminho_completo, 'r', encoding='utf-8') as f:
                    geojsons_por_uf[uf] = json.load(f)
            except Exception as e:
                logger.error(f"Erro ao carregar o arquivo {caminho_completo}: {e}")
        else:
            logger.warning(f"Arquivo GeoJSON não encontrado para a UF '{uf}': {caminho_completo}")

    return geojsons_por_uf
