# api/utils/modelagem_runner.py
"""
Motor genérico usado pelas 30 pipelines de "Modelagem Avançada"
(api/pipeline_<slug>/) para executar, sem duplicar código, os scripts de
R&D já validados em src/modelagem/*.py. Cada um desses scripts expõe um
main(args) que baixa dados do DATASUS, roda o modelo e salva CSV/PNG em
args.dir_saida — este módulo importa dinamicamente o script certo,
constrói um objeto de parâmetros equivalente ao que argparse geraria, e
registra os arquivos gerados como ManagedFile.
"""
import importlib
import os
from pathlib import Path
from types import SimpleNamespace

from django.conf import settings

EXTENSOES_REGISTRAVEIS = ('.csv', '.png', '.jpg', '.jpeg')

# Nem todo argparse.add_argument(..., default=...) dos scripts de R&D virou
# um campo exposto no formulário do frontend (ex.: caminhos de referência
# como o diretório de GeoJSON ou o CSV de população, que o usuário não deve
# precisar preencher). argparse preenche esses defaults sozinho; o
# SimpleNamespace usado aqui não, então cada um precisa ser replicado à mão
# — descoberto ao testar as 30 pipelines (vários davam AttributeError).
DEFAULTS_POR_MODULO = {
    'moran_autocorrelacao_mortalidade_infantil': {
        'geojson_dir': 'referencia/espaciais/geojson/municipios',
    },
    'lisa_clusters_agravos_sinan': {
        'populacao': 'referencia/populacao/populacao_estimada_completa_spline.csv',
        'geojson_dir': 'referencia/espaciais/geojson/municipios',
    },
    'hotspots_getis_ord_internacoes': {
        'populacao': 'referencia/populacao/populacao_estimada_completa_spline.csv',
        'geojson_dir': 'referencia/espaciais/geojson/municipios',
    },
    'moran_bivariado_ivs_mortalidade': {
        'geojson_dir': 'referencia/espaciais/geojson/municipios',
    },
    'gerar_painel_geografico': {
        'ivs_dir': 'referencia/ipea',
    },
    'binomial_negativa_determinantes_internacao': {
        'ivs_dir': 'referencia/ipea',
        'populacao': 'referencia/populacao/populacao_estimada_completa_spline.csv',
    },
    'decomposicao_sazonal_arboviroses': {
        'ordem': [1, 1, 1],
        'ordem_sazonal': [1, 1, 1],
    },
    'fluxo_partos_sinasc': {
        'municipios_csv': 'referencia/espaciais/csv/municipios.csv',
        'shapefile': 'referencia/espaciais/shapefiles/municipios/BR_Municipios_2022/BR_Municipios_2022.shp',
    },
    'fluxo_alta_complexidade_sia': {
        'municipios_csv': 'referencia/espaciais/csv/municipios.csv',
        'shapefile': 'referencia/espaciais/shapefiles/municipios/BR_Municipios_2022/BR_Municipios_2022.shp',
    },
    'difusao_espacial_surto_sinan': {
        'geojson_dir': 'referencia/espaciais/geojson/municipios',
        'municipios_csv': 'referencia/espaciais/csv/municipios.csv',
    },
    'desertos_assistenciais_cnes': {
        'municipios_csv': 'referencia/espaciais/csv/municipios.csv',
        'geojson_dir': 'referencia/espaciais/geojson/municipios',
    },
    'estimacao_bayesiana_pequenas_areas': {
        'populacao': 'referencia/populacao/populacao_estimada_completa_spline.csv',
    },
    'score_demanda_uti_neonatal': {
        'populacao': 'referencia/populacao/populacao_estimada_completa_spline.csv',
        'modelo_risco': 'outputs/risco_perinatal/modelo_risco_perinatal.joblib',
    },
    'modelo_risco_obito_materno': {
        'populacao': 'referencia/populacao/populacao_estimada_completa_spline.csv',
    },
    'modelo_risco_obito_neonatal_precoce_tardio': {
        'populacao': 'referencia/populacao/populacao_estimada_completa_spline.csv',
    },
    'modelo_risco_sifilis_congenita': {
        'populacao': 'referencia/populacao/populacao_estimada_completa_spline.csv',
    },
}


def montar_dir_saida(slug: str, task_id) -> Path:
    dir_saida = Path(settings.MEDIA_ROOT) / "processed_data" / slug / str(task_id)
    dir_saida.mkdir(parents=True, exist_ok=True)
    return dir_saida


def executar_modulo_modelagem(nome_modulo: str, parametros: dict, dir_saida: Path):
    """Importa src.modelagem.<nome_modulo> e chama seu main(args)."""
    modulo = importlib.import_module(f"src.modelagem.{nome_modulo}")
    parametros_completos = dict(DEFAULTS_POR_MODULO.get(nome_modulo, {}))
    parametros_completos.update(parametros)
    parametros_completos['dir_saida'] = str(dir_saida)
    namespace = SimpleNamespace(**parametros_completos)
    modulo.main(namespace)


ARQUIVO_POPULACAO_PADRAO = 'referencia/populacao/populacao_estimada_completa_spline.csv'


def executar_indice_composto(nome_indice: str, parametros: dict, dir_saida: Path):
    """Importa src.indices.<nome_indice> e chama seu processar_dados(...) —
    equivalente a executar_modulo_modelagem(), mas para os índices de 2ª
    camada (src/indices/), que expõem processar_dados(ufs, anos,
    arquivo_populacao, ...) retornando um DataFrame em vez de main(args)
    escrevendo arquivos em disco. Este runner salva o DataFrame retornado
    como CSV em dir_saida, no mesmo padrão dos demais módulos."""
    modulo = importlib.import_module(f"src.indices.{nome_indice}")
    ufs = parametros.get('ufs')
    anos = parametros.get('anos')
    arquivo_populacao = Path(settings.BASE_DIR) / parametros.get('arquivo_populacao', ARQUIVO_POPULACAO_PADRAO)

    df_resultado = modulo.processar_dados(ufs=ufs, anos=anos, arquivo_populacao=arquivo_populacao)
    if df_resultado is None or df_resultado.empty:
        raise RuntimeError(
            f"O índice '{nome_indice}' não retornou nenhum resultado para os parâmetros informados. "
            "Verifique se há dados publicados no DATASUS para as UFs/anos escolhidos."
        )

    # Enriquece com latitude/longitude para o dashboard poder desenhar o mapa
    # sem precisar de um join separado no frontend — feito aqui, uma vez,
    # em vez de em cada um dos 10 módulos de índice.
    if 'cod_mun_ibge_6' in df_resultado.columns:
        import pandas as pd
        caminho_municipios = Path(settings.BASE_DIR) / 'referencia/espaciais/csv/municipios.csv'
        if caminho_municipios.exists():
            df_municipios = pd.read_csv(caminho_municipios, dtype={'codigo_ibge': str})
            df_municipios['cod_mun_ibge_6'] = df_municipios['codigo_ibge'].str[:6]
            df_resultado = df_resultado.merge(
                df_municipios[['cod_mun_ibge_6', 'latitude', 'longitude']],
                on='cod_mun_ibge_6', how='left',
            )

    caminho_csv = Path(dir_saida) / f"{nome_indice}.csv"
    df_resultado.to_csv(caminho_csv, index=False, sep=';', encoding='utf-8-sig')
    return df_resultado


EXTENSOES_IMAGEM = ('.png', '.jpg', '.jpeg')


def registrar_arquivos_gerados(dir_saida: Path, task_id, user, file_type, ManagedFile):
    """Varre dir_saida por CSV/PNG gerados e registra cada um como ManagedFile,
    com uma descrição legível (nome do modelo + tipo de arquivo) para
    identificação fácil no Banco de Dados (CSV Manager)."""
    arquivos_criados = []
    tipo_legivel = getattr(file_type, 'label', str(file_type))
    for caminho in sorted(Path(dir_saida).rglob('*')):
        if caminho.is_file() and caminho.suffix.lower() in EXTENSOES_REGISTRAVEIS:
            caminho_relativo = os.path.relpath(caminho, settings.MEDIA_ROOT)
            eh_imagem = caminho.suffix.lower() in EXTENSOES_IMAGEM
            nome_legivel = caminho.stem.replace('_', ' ').title()
            descricao = f"{tipo_legivel} — {'imagem' if eh_imagem else 'CSV'}: {nome_legivel}"
            managed_file = ManagedFile.objects.create(
                uploader=user,
                file=caminho_relativo,
                filename=caminho.name,
                description=descricao,
                file_type=file_type,
                task_id=task_id,
            )
            arquivos_criados.append(managed_file)
    return arquivos_criados


def resolver_arquivo_referenciado(file_id, ManagedFile):
    """Resolve o ID de um ManagedFile já existente (ex.: um painel de
    indicadores gerado anteriormente) para o caminho absoluto em disco,
    para ser passado como parâmetro (ex.: --painel-csv) ao script de R&D."""
    if not file_id:
        return None
    managed_file = ManagedFile.objects.get(pk=file_id)
    return managed_file.file.path
