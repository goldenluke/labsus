# -*- coding: utf-8 -*-
"""
======================================================================
  ORQUESTRADOR K-MEANS PERSONALIZADO COM LEITURA DE INDICADORES DE CSV
======================================================================
Este script orquestra uma pipeline de dados que inclui:
1. Carregamento dos indicadores de saúde de um arquivo CSV fornecido.
2. Aplicação do algoritmo K-Means nos dados carregados.
3. Classificação dos clusters encontrados com base em arquétipos definidos pelo usuário.
4. Salvamento dos resultados do agrupamento e classificação.

Permite alta customização através de argumentos de linha de comando.
"""
import pandas as pd
from pathlib import Path
import argparse
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import KMeans
from scipy.spatial.distance import euclidean
import warnings
import numpy as np # Importado para uso geral, embora np.random.rand() não seja mais usado diretamente

# Suprimir avisos específicos do scikit-learn sobre o número de iterações do KMeans
warnings.filterwarnings("ignore", category=UserWarning, module="sklearn.cluster._kmeans")

# --- Cores para os Perfis (fallback se não carregado do arquivo) ---
# Este dicionário será usado como fallback se o arquivo de arquétipos não fornecer cores.
CORES_PERFIS_DEFAULT = {
    "Vulnerabilidade Social/Sanitária": "#d73027",
    "Sobrecarga de Doenças Crônicas": "#fc8d59",
    "Atenção Primária Insuficiente": "#4575b4",
    "Atenção Primária Efetiva": "#1a9850",
    "Perfil Desconhecido": "#cccccc" # Cor padrão para clusters não mapeados
}


def carregar_arquetipos(archetypes_path: Path, indicator_columns: list) -> tuple[dict, dict]:
    """
    Carrega arquétipos de um arquivo CSV e os converte para um formato de dicionário
    de Pandas Series, garantindo que as colunas correspondam aos indicadores.
    Também extrai as cores dos perfis, se a coluna 'Cor_Hex' estiver presente.
    """
    print(f"\n--- Carregando arquétipos de: {archetypes_path} ---")
    if not archetypes_path.exists():
        print(f"❌ ERRO: Arquivo de arquétipos não encontrado em '{archetypes_path}'.")
        return {}, {}

    try:
        df_arquetipos = pd.read_csv(archetypes_path)
        arquetipos = {}
        cores_perfis_dict = {} # Novo dicionário para as cores
        perfil_col = df_arquetipos.columns[0]

        # Verifica se a coluna 'Cor_Hex' existe no arquivo
        has_color_col = 'Cor_Hex' in df_arquetipos.columns

        # Validação das colunas de indicadores
        arquetipo_cols_data = [col for col in df_arquetipos.columns if col != perfil_col and col != 'Cor_Hex']
        if not all(ind in arquetipo_cols_data for ind in indicator_columns):
            missing_cols = [ind for ind in indicator_columns if ind not in arquetipo_cols_data]
            print(f"❌ ERRO: O arquivo de arquétipos não contém todas as colunas de indicadores esperadas para o agrupamento. Faltam: {missing_cols}")
            print(f"  Colunas de dados no arquivo de arquétipos: {arquetipo_cols_data}")
            print(f"  Colunas de indicadores para agrupamento: {indicator_columns}")
            return {}, {}

        for index, row in df_arquetipos.iterrows():
            perfil_nome = str(row[perfil_col]) # Garante que o nome do perfil seja string

            # Seleciona apenas as colunas de indicadores que serão usadas no agrupamento
            # Garante que a ordem das colunas seja a mesma esperada
            arquetipos[perfil_nome] = pd.Series(row[indicator_columns].values, index=indicator_columns)

            if has_color_col:
                cores_perfis_dict[perfil_nome] = str(row['Cor_Hex']) # Garante que a cor seja string
            else:
                # Se a coluna de cor não existir, atribui uma cor padrão temporária ou deixa para o fallback
                cores_perfis_dict[perfil_nome] = "#cccccc" # Cor padrão, será sobrescrita se o fallback for usado

        if not has_color_col:
            print("⚠️ Aviso: Coluna 'Cor_Hex' não encontrada no arquivo de arquétipos. Cores padrão internas serão usadas.")

        print(f"✅ Arquétipos e cores carregados com sucesso. Perfis encontrados: {list(arquetipos.keys())}")
        return arquetipos, cores_perfis_dict
    except Exception as e:
        print(f"❌ Erro ao carregar ou processar o arquivo de arquétipos: {e}")
        return {}, {}


def classificar_perfis_por_similaridade(perfil_df: pd.DataFrame, arquetipos: dict) -> dict:
    """
    Classifica cada cluster encontrado medindo sua distância euclidiana
    para um conjunto de arquétipos pré-definidos.
    Os arquétipos (perfis de referência) e os perfis de cluster (perfil_df)
    devem estar na mesma escala (e.g., padronizados).
    """
    mapeamento = {}
    if not arquetipos:
        print("⚠️ Nenhum arquétipo fornecido para classificação. Clusters não serão nomeados.")
        return {i: "Perfil Desconhecido" for i in perfil_df.index}

    indicadores_presentes_no_cluster = perfil_df.columns.tolist()

    # Filtra os arquétipos para conter apenas os indicadores presentes nos clusters
    arquetipos_filtrados = {}
    for nome, perfil_serie in arquetipos.items():
        # Garante que a ordem das colunas no arquétipo seja a mesma das features
        # e que o perfil_serie seja uma Pandas Series com o índice correto.
        # A validação de colunas já ocorreu em `carregar_arquetipos`.
        if not isinstance(perfil_serie, pd.Series):
            print(f"⚠️ Aviso: Arquétipo '{nome}' não é uma Pandas Series. Pulando na classificação.")
            continue

        # Garante que as colunas do perfil_serie estejam alinhadas com as do perfil_df
        # e que os valores sejam convertidos para numpy array para euclidean distance
        try:
            aligned_values = perfil_serie[indicadores_presentes_no_cluster].values
            arquetipos_filtrados[nome] = aligned_values
        except KeyError as ke:
            print(f"⚠️ Aviso: Coluna '{ke}' faltando no arquétipo '{nome}' durante a classificação. Pulando.")
            continue


    if not arquetipos_filtrados:
        print("❌ Nenhum arquétipo válido para comparação após filtragem. Clusters não serão nomeados.")
        return {i: "Perfil Desconhecido" for i in perfil_df.index}

    for i, row in perfil_df.iterrows():
        distancias = {}
        for nome_arquetipo, valores_arquetipo in arquetipos_filtrados.items():
            # Calcula a distância euclidiana entre o centro do cluster e o arquétipo
            distancias[nome_arquetipo] = euclidean(row.values, valores_arquetipo)

        if distancias:
            perfil_mais_proximo = min(distancias, key=distancias.get)
            mapeamento[i] = perfil_mais_proximo
        else:
            mapeamento[i] = "Perfil Desconhecido"
    return mapeamento


def carregar_e_preparar_dados_indicadores(input_csv_path: Path, ufs: list, anos: list, indicadores_selecionados: list) -> pd.DataFrame:
    """
    Carrega o DataFrame de indicadores de um arquivo CSV e aplica filtros.
    """
    print(f"\n--- Carregando dados de indicadores de: {input_csv_path} ---")
    if not input_csv_path.exists():
        print(f"❌ ERRO: Arquivo de dados de indicadores não encontrado em '{input_csv_path}'.")
        return pd.DataFrame()

    try:
        # Assumindo que o CSV usa ';' como separador, como no seu exemplo
        df_painel = pd.read_csv(input_csv_path, sep=';', dtype={'cod_mun_ibge_6': str, 'cod_mun_ibge_7': str})
        print(f"✅ Dados de indicadores carregados com sucesso. Shape: {df_painel.shape}")

        # Filtra por UF e Ano, se fornecidos
        if ufs:
            df_painel = df_painel[df_painel['UF'].isin(ufs)]
            print(f"  -> Dados filtrados por UFs ({ufs}). Novo shape: {df_painel.shape}")
        if anos:
            df_painel = df_painel[df_painel['ANO'].isin(anos)]
            print(f"  -> Dados filtrados por Anos ({anos}). Novo shape: {df_painel.shape}")

        # Identifica as colunas de indicadores a serem usadas para o clustering
        # Se 'indicadores_selecionados' for fornecido, usa-os. Caso contrário, tenta inferir.
        if indicadores_selecionados:
            # Verifica se as colunas selecionadas existem no DataFrame
            missing_indicators = [ind for ind in indicadores_selecionados if ind not in df_painel.columns]
            if missing_indicators:
                print(f"❌ ERRO: Os seguintes indicadores selecionados não foram encontrados no CSV: {missing_indicators}")
                # Remove os indicadores ausentes para continuar, ou você pode optar por abortar
                indicadores_selecionados = [ind for ind in indicadores_selecionados if ind in df_painel.columns]
                if not indicadores_selecionados:
                    print("❌ ERRO: Nenhuma coluna de indicador válida para processar após a filtragem.")
                    return pd.DataFrame()

            # Garante que apenas as colunas numéricas selecionadas sejam mantidas
            numeric_selected_indicators = [col for col in indicadores_selecionados if pd.api.types.is_numeric_dtype(df_painel[col])]
            if not numeric_selected_indicators:
                print("❌ ERRO: Nenhuma coluna de indicador numérica válida encontrada entre as selecionadas.")
                return pd.DataFrame()

            # Mantém apenas as colunas essenciais e os indicadores selecionados
            cols_to_keep = ['cod_mun_ibge_6', 'ANO', 'UF', 'municipio'] + numeric_selected_indicators
            df_painel = df_painel[cols_to_keep].copy()
            print(f"  -> Usando indicadores selecionados: {numeric_selected_indicators}")

        else:
            # Tenta identificar automaticamente as colunas de indicadores (todas as maiúsculas e numéricas, exceto chaves)
            # Isso é uma heurística e pode precisar de ajuste dependendo do seu CSV
            all_numeric_cols = df_painel.select_dtypes(include=np.number).columns.tolist()
            potential_indicators = [col for col in all_numeric_cols if col.isupper() and col not in ['ANO', 'MES']] # MES se existir

            # Remove colunas que são IDs ou não são indicadores reais
            if 'populacao' in potential_indicators: potential_indicators.remove('populacao')
            if 'cod_mun_ibge_7' in potential_indicators: potential_indicators.remove('cod_mun_ibge_7')
            if 'TX_MAL_DEFINIDAS_P10K' in potential_indicators: potential_indicators.remove('TX_MAL_DEFINIDAS_P10K') # Exemplo de remoção específica

            if not potential_indicators:
                print("❌ ERRO: Nenhuma coluna de indicador numérica foi identificada automaticamente. Por favor, especifique-as com '--indicadores'.")
                return pd.DataFrame()

            # Mantém apenas as colunas essenciais e os indicadores identificados
            cols_to_keep = ['cod_mun_ibge_6', 'ANO', 'UF', 'municipio'] + potential_indicators
            df_painel = df_painel[cols_to_keep].copy()
            print(f"  -> Usando indicadores identificados automaticamente: {potential_indicators}")


        # Remove linhas com valores ausentes nos indicadores selecionados
        # Esta é uma etapa crucial antes do K-Means
        df_painel.dropna(subset=df_painel.columns.difference(['cod_mun_ibge_6', 'ANO', 'UF', 'municipio']), inplace=True)
        print(f"  -> Linhas com valores ausentes nos indicadores removidas. Novo shape: {df_painel.shape}")

        if df_painel.empty:
            print("❌ ERRO: DataFrame vazio após filtragem e remoção de NaNs. Nenhuma análise será realizada.")
            return pd.DataFrame()

        return df_painel

    except Exception as e:
        print(f"❌ Erro ao carregar ou preparar o arquivo de indicadores: {e}")
        return pd.DataFrame()


def executar_kmeans_personalizado(df_painel: pd.DataFrame, num_clusters: int, output_dir: Path, arquetipos: dict = None, cores_perfis: dict = None):
    """
    Executa o algoritmo K-Means em um DataFrame de indicadores.
    Salva os dados com os rótulos de cluster e os centros dos clusters.
    Se arquétipos forem fornecidos, classifica os clusters.
    """
    print(f"\n--- Executando K-Means com k={num_clusters} ---")

    # Garante que o diretório de saída exista
    output_dir.mkdir(parents=True, exist_ok=True)

    # Identifica colunas para agrupamento (todas as numéricas, exceto chaves)
    # As colunas 'cod_mun_ibge_6', 'ANO', 'UF', 'municipio' já devem ter sido tratadas
    # na função `carregar_e_preparar_dados_indicadores`.
    # Aqui, pegamos todas as colunas numéricas restantes.
    features_para_cluster = df_painel.select_dtypes(include=np.number).copy()

    if features_para_cluster.empty:
        print("❌ ERRO: Nenhuma coluna numérica válida encontrada para o agrupamento.")
        return

    # Padronização dos dados
    print("🔄 Padronizando os dados (StandardScaler)...")
    scaler = StandardScaler()
    scaled_features = scaler.fit_transform(features_para_cluster)
    df_scaled = pd.DataFrame(scaled_features, columns=features_para_cluster.columns, index=df_painel.index)
    print("✅ Dados padronizados com sucesso.")

    # Execução do K-Means
    try:
        if len(df_scaled) < num_clusters:
            print(f"❌ ERRO: Número de amostras ({len(df_scaled)}) é menor que o número de clusters ({num_clusters}). Agrupamento não pode ser realizado.")
            return

        kmeans = KMeans(n_clusters=num_clusters, random_state=42, n_init=10)
        df_painel['cluster_num'] = kmeans.fit_predict(df_scaled) # Renomeado para evitar conflito com 'cluster' final
        print("✅ K-Means executado com sucesso.")

        # Obtém os centros dos clusters (em escala original e padronizada)
        cluster_centers_scaled = pd.DataFrame(kmeans.cluster_centers_, columns=features_para_cluster.columns)
        cluster_centers_original_scale = pd.DataFrame(scaler.inverse_transform(kmeans.cluster_centers_), columns=features_para_cluster.columns)
        cluster_centers_original_scale.index.name = 'cluster_id'
        print("\nCentros dos Clusters (escala original):")
        print(cluster_centers_original_scale)

        # --- Classificação dos Clusters com Arquétipos (se fornecidos) ---
        if arquetipos:
            print("\n--- Classificando clusters com arquétipos ---")
            # Padroniza os arquétipos para a mesma escala dos centros de cluster
            # Importante: O scaler deve ser o mesmo usado para os dados
            arquetipos_scaled = {}
            for nome_arquetipo, serie_arquetipo in arquetipos.items():
                try:
                    # Garante que a ordem das colunas no arquétipo seja a mesma das features
                    arquetipo_values_ordered = serie_arquetipo[features_para_cluster.columns].values.reshape(1, -1)
                    # CORREÇÃO: Garante que o resultado da transformação seja uma pd.Series
                    # para manter o índice (nomes das colunas) para a função de similaridade.
                    arquetipos_scaled[nome_arquetipo] = pd.Series(
                        scaler.transform(arquetipo_values_ordered)[0],
                        index=features_para_cluster.columns # Atribui os nomes das colunas à nova série
                    )
                except KeyError as ke:
                    print(f"⚠️ Arquétipo '{nome_arquetipo}' não contém todas as colunas de indicadores usadas para agrupamento. Erro: {ke}. Ignorando este arquétipo.")
                    continue
                except ValueError as ve:
                    print(f"⚠️ Erro ao padronizar arquétipo '{nome_arquetipo}'. Certifique-se de que os valores numéricos estão corretos. Erro: {ve}. Ignorando este arquétipo.")
                    continue


            mapeamento_nomes = classificar_perfis_por_similaridade(cluster_centers_scaled, arquetipos_scaled)
            print(f" -> Mapeamento de perfis: {mapeamento_nomes}")
            df_painel['perfil'] = df_painel['cluster_num'].map(mapeamento_nomes).fillna("Perfil Desconhecido")
            # Usa as cores carregadas do arquivo de arquétipos, com fallback para as cores padrão
            df_painel['cor'] = df_painel['perfil'].map(cores_perfis if cores_perfis else CORES_PERFIS_DEFAULT).fillna("#cccccc")
            print("✅ Clusters classificados com sucesso.")
        else:
            print("⚠️ Nenhum arquivo de arquétipos fornecido. Clusters não serão classificados por perfil.")
            df_painel['perfil'] = "Cluster " + df_painel['cluster_num'].astype(str)
            df_painel['cor'] = "#cccccc" # Cor padrão se não houver classificação por perfil


    except Exception as e:
        print(f"❌ Erro ao executar o K-Means ou classificar clusters: {e}")
        return

    # Salvando os resultados
    output_clustered_data_path = output_dir / "dados_com_clusters_personalizado.csv"
    df_painel.to_csv(output_clustered_data_path, index=False, sep=';', encoding='utf-8-sig')
    print(f"✅ Dados com rótulos de cluster e perfis salvos em: '{output_clustered_data_path}'")

    output_cluster_centers_path = output_dir / "centros_dos_clusters_personalizado.csv"
    cluster_centers_original_scale.to_csv(output_cluster_centers_path, index=True, sep=';', encoding='utf-8-sig')
    print(f"✅ Centros dos clusters (escala original) salvos em: '{output_cluster_centers_path}'")


def main(args):
    """Função principal que orquestra todo o fluxo de trabalho."""

    # --- Configuração Inicial ---
    INPUT_DATA_CSV_PATH = Path(args.input_data_csv_path) # Novo argumento
    UFS_ALVO = args.ufs
    ANOS_ALVO = args.anos
    INDICADORES_SELECIONADOS = args.indicadores
    NUM_CLUSTERS = args.n_clusters
    DIR_SAIDA_ANALISES = Path(args.output_dir)
    ARQUETIPOS_PATH = Path(args.archetypes_path) if args.archetypes_path else None

    DIR_SAIDA_ANALISES.mkdir(parents=True, exist_ok=True)

    print("=" * 60)
    print("🚀 INICIANDO O ORQUESTRADOR K-MEANS PERSONALIZADO 🚀")
    print(f"  Arquivo de Dados de Entrada: {INPUT_DATA_CSV_PATH}") # Novo log
    print(f"  Estados Alvo: {UFS_ALVO}")
    print(f"  Anos Alvo:    {ANOS_ALVO}")
    print(f"  Indicadores Selecionados: {INDICADORES_SELECIONADOS if INDICADORES_SELECIONADOS else 'Todos os numéricos identificados'}")
    print(f"  Número de Clusters (k): {NUM_CLUSTERS}")
    print(f"  Diretório de Saída: {DIR_SAIDA_ANALISES}")
    print(f"  Caminho dos Arquétipos: {ARQUETIPOS_PATH if ARQUETIPOS_PATH else 'Nenhum fornecido'}")
    print("=" * 60)

    # --- ETAPA 1: Carregando e Preparando os Dados de Indicadores ---
    df_painel_integrado = carregar_e_preparar_dados_indicadores(
        input_csv_path=INPUT_DATA_CSV_PATH,
        ufs=UFS_ALVO,
        anos=ANOS_ALVO,
        indicadores_selecionados=INDICADORES_SELECIONADOS
    )

    if df_painel_integrado.empty:
        print("❌ ERRO CRÍTICO: O DataFrame de indicadores está vazio ou não pôde ser carregado/preparado. Pipeline abortada.")
        return

    print(f"✅ Painel de dados integrado e preparado. Shape: {df_painel_integrado.shape}")
    print("\nPrimeiras 5 linhas do Painel Preparado:")
    print(df_painel_integrado.head())

    # --- Carregar Arquétipos (se o caminho for fornecido) ---
    arquetipos_carregados = {}
    cores_perfis_carregadas = {} # Inicializa dicionário para as cores carregadas
    if ARQUETIPOS_PATH:
        # Obtenha as colunas numéricas que serão usadas como features no K-Means
        features_cols_for_archetypes_validation = df_painel_integrado.select_dtypes(include=np.number).columns.tolist()

        # Chama carregar_arquetipos para obter tanto os arquétipos quanto as cores
        arquetipos_carregados, cores_perfis_carregadas = carregar_arquetipos(ARQUETIPOS_PATH, features_cols_for_archetypes_validation)
        if not arquetipos_carregados:
            print("⚠️ Arquétipos não puderam ser carregados ou validados. A classificação por perfil não será aplicada.")
            cores_perfis_carregadas = {} # Garante que cores_perfis_carregadas esteja vazio se os arquétipos falharem

        # Se os arquétipos foram carregados, mas nenhuma cor foi especificada no arquivo,
        # usa as cores padrão internas como fallback.
        if arquetipos_carregados and not cores_perfis_carregadas:
            print("⚠️ Nenhuma cor de perfil carregada do arquivo de arquétipos. Usando cores padrão internas.")
            cores_perfis_carregadas = CORES_PERFIS_DEFAULT # Fallback para cores padrão internas

    # --- ETAPA 3: Executando K-Means Personalizado ---
    executar_kmeans_personalizado(df_painel_integrado, NUM_CLUSTERS, DIR_SAIDA_ANALISES, arquetipos=arquetipos_carregados, cores_perfis=cores_perfis_carregadas)

    print("\n=================================================")
    print("🎉 FLUXO K-MEANS PERSONALIZADO CONCLUÍDO COM SUCESSO! 🎉")
    print("=================================================")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Orquestrador K-Means Personalizado com Seleção de Indicadores e Arquétipos.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )

    # Novo argumento para o caminho do CSV de dados de entrada
    # Caminho padrão ajustado para o exemplo fornecido
    parser.add_argument(
        "--input_data_csv_path",
        type=str,
        default="dados/processados/integrados/master_table_indicadores_TO-GO_2019-2020-2021-2022.csv",
        help="Caminho completo para o arquivo CSV de entrada que contém todos os dados de indicadores (ex: painel_integrado.csv)."
    )
    parser.add_argument(
        "--ufs",
        nargs="+",
        default=[], # Padrão vazio para não filtrar se não especificado
        help="Lista de siglas de UFs a processar. Se não informado, não filtra por UF."
    )
    parser.add_argument(
        "--anos",
        nargs="+",
        type=int,
        default=[], # Padrão vazio para não filtrar se não especificado
        help="Lista de anos a processar. Se não informado, não filtra por ano."
    )
    parser.add_argument(
        "--indicadores",
        nargs="+",
        help="Lista de indicadores específicos a usar para o agrupamento (ex: TMI COBERTURA_PRENATAL). Se não informado, tenta usar todas as colunas numéricas identificadas como indicadores."
    )
    parser.add_argument(
        "--n_clusters",
        type=int,
        default=3,
        help="Número de clusters (k) a serem formados pelo algoritmo K-Means."
    )
    parser.add_argument(
        "--output_dir",
        type=str,
        default="kmeans_custom_outputs",
        help="Diretório de saída para os resultados do K-Means (dados com clusters, centros dos clusters)."
    )
    parser.add_argument(
        "--archetypes_path",
        type=str,
        default="arquetipos.csv",
        help="Caminho completo para o arquivo CSV contendo as definições dos arquétipos. A primeira coluna deve ser o nome do perfil, e as demais devem ser os indicadores usados para agrupamento."
    )

    args = parser.parse_args()
    main(args)
