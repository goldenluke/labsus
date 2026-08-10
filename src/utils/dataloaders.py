# Arquivo: utils/dataloaders.py
# -*- coding: utf-8 -*-
import pandas as pd
from pathlib import Path # 1. Importa a classe Path, essencial para a correção

def filtrar_populacao(arquivo_populacao, uf, ano):
    """
    Função centralizada e flexível para carregar e preparar o DataFrame de população.

    Versão corrigida para aceitar objetos pathlib.Path como entrada, resolvendo
    o erro de tipo de parâmetro.
    """
    try:
        # ✅ --- CORREÇÃO APLICADA ---
        # Converte o input para um objeto Path para validação e leitura.
        caminho = Path(arquivo_populacao)

        # Valida se o arquivo realmente existe antes de tentar ler
        if not caminho.exists():
            print(f"❌ ERRO em filtrar_populacao: Arquivo não encontrado em '{caminho}'")
            return None

        # Lê o arquivo CSV usando o caminho validado
        df_pop = pd.read_csv(caminho, sep=';', dtype={'cod_mun_ibge_6': str, 'cod_mun_ibge_7': str})

        # Padroniza o nome da coluna de ano para 'ANO'
        if 'ano' in df_pop.columns:
            df_pop.rename(columns={'ano': 'ANO'}, inplace=True)

        if 'ANO' not in df_pop.columns:
            print(f"❌ ERRO em filtrar_populacao: Coluna 'ANO' não encontrada no arquivo de população.")
            return None

        # Garante que a coluna de ano seja numérica para a filtragem
        df_pop['ANO'] = pd.to_numeric(df_pop['ANO'], errors='coerce')

        # Filtra pela UF e Ano desejados
        df_pop_ano = df_pop[(df_pop['UF'] == uf) & (df_pop['ANO'] == ano)].copy()

        if df_pop_ano.empty:
            print(f"⚠️  Aviso em filtrar_populacao: Nenhum dado populacional encontrado para {uf}/{ano}.")
            return None

        # Define o código do município como índice para facilitar a junção (join)
        if 'cod_mun_ibge_6' in df_pop_ano.columns:
            df_pop_ano.set_index('cod_mun_ibge_6', inplace=True)
            return df_pop_ano
        else:
            print("❌ ERRO: Coluna 'cod_mun_ibge_6' não encontrada no arquivo de população.")
            return None

    except Exception as e:
        # Captura qualquer outro erro que possa ocorrer durante o processo
        print(f"❌ ERRO CRÍTICO em filtrar_populacao para {uf}/{ano}: {e}")
        return None


def carregar_nomes_municipios(arquivo_populacao) -> dict:
    """Carrega um mapa {cod_mun_ibge_6: nome_municipio} a partir do CSV de
    população estimada (mesma fonte usada por filtrar_populacao), para que
    as saídas dos módulos de modelagem mostrem o nome do município em vez
    de apenas o código IBGE cru."""
    caminho = Path(arquivo_populacao)
    if not caminho.exists():
        print(f"⚠️ Aviso: arquivo de população '{caminho}' não encontrado para mapear nomes de município.")
        return {}
    df_pop = pd.read_csv(caminho, sep=';', dtype={'cod_mun_ibge_6': str}, usecols=['cod_mun_ibge_6', 'municipio'])
    return df_pop.drop_duplicates(subset=['cod_mun_ibge_6']).set_index('cod_mun_ibge_6')['municipio'].to_dict()


def adicionar_nome_municipio(df: pd.DataFrame, coluna_codigo: str, arquivo_populacao, coluna_saida: str = 'municipio') -> pd.DataFrame:
    """Insere coluna_saida logo após coluna_codigo com o nome do município,
    mapeado a partir dos 6 primeiros dígitos de coluna_codigo. Usada para
    tornar tabelas municipais legíveis (nome ao lado do código, não só o
    código IBGE)."""
    mapa_nomes = carregar_nomes_municipios(arquivo_populacao)
    nomes = df[coluna_codigo].astype(str).str[:6].map(mapa_nomes)
    if coluna_saida in df.columns:
        df[coluna_saida] = nomes
    else:
        df.insert(df.columns.get_loc(coluna_codigo) + 1, coluna_saida, nomes)
    return df


def processar_agravo_sinan_generico(
    ufs, anos, arquivo_populacao, dis_code, nome_indicador,
    coluna_filtro=None, codigos_confirmados=None, divisor=100000, **kwargs
):
    """
    Processa um agravo genérico do SINAN por UF/ano: baixa o arquivo do agravo
    (`dis_code`), opcionalmente restringe aos casos cujo `coluna_filtro` esteja
    em `codigos_confirmados` (ex.: CLASSI_FIN em ['1']), conta os casos por
    município de RESIDÊNCIA (ID_MN_RESI) e calcula a taxa por `divisor`
    habitantes (padrão: por 100.000).

    Se `coluna_filtro` for None (ou não existir no arquivo baixado), conta
    todas as notificações do agravo sem filtro adicional — apropriado para
    agravos sem etapa de confirmação/descarte (ex.: acidentes de trabalho,
    violência), já que o próprio `dis_code` do SINAN já restringe ao agravo.

    Compartilhada por todos os módulos de `src/features/*.py` que modelam um
    único agravo do SINAN como indicador de incidência/notificação por
    município — evita duplicar a mesma lógica de download/filtro/agregação
    em dezenas de arquivos quase idênticos.
    """
    from pysus.online_data.SINAN import SINAN

    resultados = []

    try:
        sinan_db = SINAN().load()
    except Exception as e:
        print(f"❌ Erro crítico ao carregar o banco de dados do SINAN: {e}")
        return pd.DataFrame()

    col_casos = f"casos_{dis_code.lower()}"

    for uf in ufs:
        for ano in anos:
            print(f"\n=== Processando {nome_indicador} ({dis_code}) em {uf}/{ano} ===")

            df_base = filtrar_populacao(arquivo_populacao=arquivo_populacao, uf=uf, ano=ano)
            if df_base is None:
                continue

            try:
                files = sinan_db.get_files(dis_code=dis_code, year=ano)
                if not files:
                    raise FileNotFoundError(f"Nenhum arquivo SINAN/{dis_code} encontrado para o ano {ano}")

                downloaded = sinan_db.download(files)

                df_sinan = pd.DataFrame()
                if isinstance(downloaded, list):
                    df_sinan = pd.concat([p.to_dataframe() for p in downloaded], ignore_index=True)
                elif hasattr(downloaded, "to_dataframe"):
                    df_sinan = downloaded.to_dataframe()

                if df_sinan.empty:
                    raise ValueError(f"DataFrame do SINAN/{dis_code} está vazio após o download.")

                if "ID_MN_RESI" not in df_sinan.columns:
                    raise KeyError("Coluna 'ID_MN_RESI' não encontrada nos dados do SINAN.")

                if coluna_filtro and codigos_confirmados and coluna_filtro in df_sinan.columns:
                    valores = df_sinan[coluna_filtro].astype(str).str.strip().str.rstrip(".0")
                    codigos_str = [str(c) for c in codigos_confirmados]
                    df_filtrado = df_sinan[valores.isin(codigos_str)]
                else:
                    df_filtrado = df_sinan

                uf_code_str = df_base.index.str[:2].unique()[0]
                df_uf = df_filtrado[df_filtrado["ID_MN_RESI"].astype(str).str.startswith(uf_code_str)]

                casos = df_uf.groupby("ID_MN_RESI").size().rename(col_casos)
                casos.index = casos.index.astype(str).str[:6]
                print(f"    -> {casos.sum()} casos de {nome_indicador} encontrados em {uf}/{ano}.")

            except Exception as e:
                print(f"⚠️ Erro ao processar {dis_code} para {uf}/{ano}: {e}")
                casos = pd.Series(dtype=int, name=col_casos)

            df = df_base.join(casos, how="left")
            df[col_casos] = df[col_casos].fillna(0).astype(int)
            df[nome_indicador] = df.apply(
                lambda r: (r[col_casos] / r.populacao * divisor) if r.populacao > 0 else 0, axis=1
            )
            df["UF"] = uf
            resultados.append(df.reset_index())

    if resultados:
        df_final = pd.concat(resultados, ignore_index=True)
        print(f"\n✅ {nome_indicador} processado com sucesso.")
        return df_final
    else:
        print(f"⚠️ Nenhum dado de {nome_indicador} foi processado.")
        return pd.DataFrame()




### DASHBOARD

import json
from pathlib import Path

# O diretório base é a raiz do projeto (sobe 2 níveis a partir de src/utils)
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# Define os caminhos aqui para serem usados pelas funções
CAMINHO_RESULTADOS_CLUSTER = BASE_DIR / "dados/processados/clusters/cluster_results.csv"
CAMINHO_MUNICIPIOS_CSV = BASE_DIR / "referencia/espaciais/csv/municipios.csv"
CAMINHO_ESTADOS_CSV = BASE_DIR / "referencia/espaciais/csv/estados.csv"
CAMINHO_GEOJSON_BASE = BASE_DIR / "referencia/espaciais/geojson/municipios"

GEOJSON_PATHS = {
    'AC': 'geojs-12-mun', 'AL': 'geojs-27-mun', 'AP': 'geojs-16-mun', 'AM': 'geojs-13-mun',
    'BA': 'geojs-29-mun', 'CE': 'geojs-23-mun', 'DF': 'geojs-53-mun', 'ES': 'geojs-32-mun',
    'GO': 'geojs-52-mun', 'MA': 'geojs-21-mun', 'MT': 'geojs-51-mun', 'MS': 'geojs-50-mun',
    'MG': 'geojs-31-mun', 'PA': 'geojs-15-mun', 'PB': 'geojs-25-mun', 'PR': 'geojs-41-mun',
    'PE': 'geojs-26-mun', 'PI': 'geojs-22-mun', 'RJ': 'geojs-33-mun', 'RN': 'geojs-24-mun',
    'RS': 'geojs-43-mun', 'RO': 'geojs-11-mun', 'RR': 'geojs-14-mun', 'SC': 'geojs-42-mun',
    'SP': 'geojs-35-mun', 'SE': 'geojs-28-mun', 'TO': 'geojs-17-mun',
    'BR': 'geojs-100-mun'
}

UF_SETTINGS_HEURISTICS = {
    'RO': {"scale": 1.03}, 'AC': {"scale": 1.03}, 'AM': {"scale": 0.59}, 'RR': {"scale": 1.03},
    'PA': {"scale": 0.74}, 'AP': {"scale": 1.48}, 'TO': {"scale": 1.18}, 'MA': {"scale": 1.03},
    'PI': {"scale": 1.03}, 'CE': {"scale": 1.48}, 'RN': {"scale": 2.21}, 'PB': {"scale": 2.21},
    'PE': {"scale": 1.77}, 'AL': {"scale": 2.95}, 'SE': {"scale": 3.69}, 'BA': {"scale": 0.88},
    'MG': {"scale": 1.03}, 'ES': {"scale": 2.66}, 'RJ': {"scale": 2.95}, 'SP': {"scale": 1.33},
    'PR': {"scale": 1.33}, 'SC': {"scale": 1.48}, 'RS': {"scale": 1.03}, 'MS': {"scale": 1.03},
    'MT': {"scale": 0.74}, 'GO': {"scale": 1.03}, 'DF': {"scale": 7.38},
}

def load_cluster_data():
    """Carrega e prepara os dados de clusters, municípios e estados."""
    try:
        df_clusters = pd.read_csv(CAMINHO_RESULTADOS_CLUSTER, sep=';', dtype={'cod_mun_ibge_6': str, 'cod_mun_ibge_7': str})
        df_clusters['perfil'] = df_clusters['perfil'].str.capitalize()

        df_municipios_coords = pd.read_csv(CAMINHO_MUNICIPIOS_CSV, dtype={'codigo_ibge': str})
        df_municipios_coords_slim = df_municipios_coords[['codigo_ibge', 'latitude', 'longitude', 'codigo_uf']].rename(
            columns={'codigo_ibge': 'cod_mun_ibge_7', 'codigo_uf': 'UF_municipio'})

        df_clusters = pd.merge(df_clusters, df_municipios_coords_slim, on='cod_mun_ibge_7', how='left')
        df_clusters['UF'] = df_clusters['UF'].fillna(df_clusters['UF_municipio'])
        df_clusters.drop(columns=['UF_municipio'], inplace=True)

        df_estados_coords = pd.read_csv(CAMINHO_ESTADOS_CSV, dtype={'codigo_uf': str, 'uf': str})

        return df_clusters, df_estados_coords

    except FileNotFoundError as e:
        print(f"ERRO CRÍTICO: Arquivo de dados não encontrado: {e}.")
        return pd.DataFrame(), pd.DataFrame()

def load_geojson_data():
    """Carrega todos os arquivos GeoJSON para um dicionário."""
    geojsons_por_uf = {}
    if not CAMINHO_GEOJSON_BASE.exists():
        print(f"ERRO CRÍTICO: Pasta de GeoJSON '{CAMINHO_GEOJSON_BASE}' não encontrada.")
        return {}

    for uf, nome_arquivo in GEOJSON_PATHS.items():
        caminho_completo = (CAMINHO_GEOJSON_BASE / nome_arquivo).with_suffix('.json')
        if caminho_completo.exists():
            try:
                with open(caminho_completo, 'r', encoding='utf-8') as f:
                    geojsons_por_uf[uf] = json.load(f)
            except Exception as e:
                print(f"ERRO ao carregar GeoJSON '{caminho_completo}': {e}")
    return geojsons_por_uf

def get_state_view_config(df_estados_coords):
    """Cria a configuração de visualização do mapa para cada estado."""
    config = {'BR': {"center": {"lat": -14.2350, "lon": -51.9253}, "projection_scale": 1.1}}
    if not df_estados_coords.empty:
        for _, row in df_estados_coords.iterrows():
            uf, lat, lon = row['uf'], row['latitude'], row['longitude']
            settings = UF_SETTINGS_HEURISTICS.get(uf, {'scale': 10.0})
            config[uf] = {"center": {"lat": lat, "lon": lon}, "projection_scale": settings['scale']}
    return config
