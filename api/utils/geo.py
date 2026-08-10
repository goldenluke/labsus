import pandas as pd
from django.conf import settings
from functools import lru_cache
from pathlib import Path

@lru_cache(max_size=1)
def get_municipality_mapping():
    """Retorna um dicionário {id7: {'nome': municipio, 'id6': id6}}"""
    # Caminho baseado na estrutura: /home/ld/cognisaude/referencia/...
    # settings.BASE_DIR costuma ser /home/ld/cognisaude/backend_project
    csv_path = Path(settings.BASE_DIR).parent / 'referencia' / 'populacao' / 'populacao_estimada_completa_spline.csv'

    try:
        df = pd.read_csv(csv_path, sep=';', dtype={'cod_mun_ibge_7': str, 'cod_mun_ibge_6': str})
        # Pegamos apenas a última ocorrência de cada município (ano mais recente)
        df_latest = df.drop_duplicates(subset=['cod_mun_ibge_7'], keep='last')

        mapping = {
            row['cod_mun_ibge_7']: {
                'nome': row['municipio'],
                'id6': row['cod_mun_ibge_6']
            }
            for _, row in df_latest.iterrows()
        }
        return mapping
    except Exception as e:
        print(f"Erro ao carregar mapeamento de municípios: {e}")
        return {}
