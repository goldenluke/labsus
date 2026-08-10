# -*- coding: utf-8 -*-
import pandas as pd
import numpy as np
import geopandas as gpd
from pathlib import Path
import argparse
import os
import shap
import lightgbm as lgb
import matplotlib.pyplot as plt
from sklearn.model_selection import train_test_split

from pysus.online_data.CNES import CNES

# Supondo que a função filtrar_populacao está disponível
try:
    from src.utils.dataloaders import filtrar_populacao
except (ModuleNotFoundError, ImportError):
    def filtrar_populacao(arquivo_populacao, uf, ano):
        print(f"AVISO: Usando função 'filtrar_populacao' de fallback. Carregando de '{arquivo_populacao}'")
        try:
            df_pop = pd.read_csv(arquivo_populacao, sep=';', dtype={'cod_mun_ibge_6': str})
            if 'ano' in df_pop.columns: df_pop.rename(columns={'ano': 'ANO'}, inplace=True)
            df_pop_ano = df_pop[(df_pop['UF'] == uf) & (df_pop['ANO'] == ano)].copy()
            df_pop_ano.set_index('cod_mun_ibge_6', inplace=True)
            return df_pop_ano
        except Exception as e:
            print(f"Erro na função de fallback 'filtrar_populacao': {e}")
            return None

def otimizar_memoria(df: pd.DataFrame) -> pd.DataFrame:
    """
    Percorre todas as colunas de um DataFrame e modifica o tipo de dados
    para minimizar o uso de memória.
    """
    print(f"[LOG] Otimizando uso de memória... Shape inicial: {df.shape}")
    memoria_antes = df.memory_usage(deep=True).sum() / 1024**2

    for col in df.columns:
        col_type = df[col].dtype
        if col_type != object and col_type.name != 'category' and 'datetime' not in str(col_type):
            c_min = df[col].min(); c_max = df[col].max()
            if str(col_type)[:3] == 'int' or str(col_type)[:4] == 'uint':
                if c_min > np.iinfo(np.int8).min and c_max < np.iinfo(np.int8).max: df[col] = df[col].astype(np.int8)
                elif c_min > np.iinfo(np.int16).min and c_max < np.iinfo(np.int16).max: df[col] = df[col].astype(np.int16)
                elif c_min > np.iinfo(np.int32).min and c_max < np.iinfo(np.int32).max: df[col] = df[col].astype(np.int32)
                elif c_min > np.iinfo(np.int64).min and c_max < np.iinfo(np.int64).max: df[col] = df[col].astype(np.int64)
            else:
                if c_min > np.finfo(np.float32).min and c_max < np.finfo(np.float32).max: df[col] = df[col].astype(np.float32)
                else: df[col] = df[col].astype(np.float64)

    memoria_depois = df.memory_usage(deep=True).sum() / 1024**2
    print(f"   -> Uso de memória antes: {memoria_antes:.2f} MB")
    print(f"   -> Uso de memória depois: {memoria_depois:.2f} MB")
    print(f"   -> Redução de {100 * (memoria_antes - memoria_depois) / memoria_antes:.1f}%")
    return df

def carregar_dados_contextuais(diretorio_ivs: Path, ufs: list, ano: int):
    """Carrega dados contextuais do IVS e do CNES para os municípios."""
    print("\n--- [ETAPA 1.5] Carregando Dados Contextuais (IVS e CNES) ---")
    dfs_ivs = []; print(f"[LOG] Carregando arquivos IVS do diretório: {diretorio_ivs}")
    for uf in ufs:
        caminho_arquivo_ivs_lower = diretorio_ivs / f"ivs_{uf.lower()}.csv"; caminho_arquivo_ivs_upper = diretorio_ivs / f"ivs_{uf.upper()}.csv"
        caminho_arquivo_ivs = None
        if caminho_arquivo_ivs_lower.exists(): caminho_arquivo_ivs = caminho_arquivo_ivs_lower
        elif caminho_arquivo_ivs_upper.exists(): caminho_arquivo_ivs = caminho_arquivo_ivs_upper
        if caminho_arquivo_ivs:
            try: df_uf = pd.read_csv(caminho_arquivo_ivs); dfs_ivs.append(df_uf)
            except Exception as e: print(f"  -> ⚠️ Aviso: Erro ao ler o arquivo IVS '{caminho_arquivo_ivs}': {e}")
        else: print(f"  -> ⚠️ Aviso: Arquivo IVS para {uf} não encontrado.")
    if not dfs_ivs: print("❌ Erro: Nenhum arquivo IVS pôde ser carregado."); return None
    df_ivs_completo = pd.concat(dfs_ivs, ignore_index=True)
    coluna_municipio_ivs = None; possiveis_nomes = ['municipio', 'codmun7', 'Codmun', 'codigo_ibge', 'cod_mun', 'codmun']
    for nome in possiveis_nomes:
        if nome in df_ivs_completo.columns: coluna_municipio_ivs = nome; break
    if coluna_municipio_ivs is None: print(f"❌ ERRO: Nenhuma coluna de código do município encontrada no CSV do IVS."); return None
    df_ivs_completo[coluna_municipio_ivs] = df_ivs_completo[coluna_municipio_ivs].astype(str)
    df_ivs_mun = df_ivs_completo.rename(columns={coluna_municipio_ivs: 'CODMUNRES'})[['CODMUNRES', 'ivs']]; df_ivs_mun['CODMUNRES'] = df_ivs_mun['CODMUNRES'].str[:6]
    try:
        print(f"[LOG] Carregando dados do CNES para calcular densidade de UBS..."); cnes_db = CNES().load()
        files_cnes = cnes_db.get_files(group='ST', uf=ufs, year=ano, month=12)
        if files_cnes:
            downloaded_data = cnes_db.download(files_cnes)
            if isinstance(downloaded_data, list): df_cnes_st = pd.concat([f.to_dataframe() for f in downloaded_data], ignore_index=True)
            else: df_cnes_st = downloaded_data.to_dataframe()
        else: df_cnes_st = pd.DataFrame()
        if not df_cnes_st.empty:
            df_ubs = df_cnes_st[df_cnes_st['TP_UNID'] == '02']; contagem_ubs = df_ubs.groupby('CODUFMUN').size().rename('N_UBS').reset_index()
            contagem_ubs.rename(columns={'CODUFMUN': 'CODMUNRES'}, inplace=True); contagem_ubs['CODMUNRES'] = contagem_ubs['CODMUNRES'].astype(str)
        else: contagem_ubs = pd.DataFrame(columns=['CODMUNRES', 'N_UBS'])
    except Exception as e: print(f"❌ Erro ao processar CNES para densidade de UBS: {e}"); return None
    df_contexto = pd.merge(df_ivs_mun, contagem_ubs, on='CODMUNRES', how='left'); df_contexto['N_UBS'] = df_contexto['N_UBS'].fillna(0)
    return df_contexto

def preparar_dados_finais(caminho_sobrevida_csv: Path, df_contexto: pd.DataFrame):
    """
    Prepara o dataset final usando processamento em lotes (chunking)
    para lidar com arquivos grandes de forma eficiente em memória.
    """
    print("\n--- [ETAPA 2] Preparando o dataset final (Processamento em Lotes) ---")

    processed_chunks = []
    chunk_size = 50000  # Processa 100.000 linhas de cada vez

    print(f"[LOG] Lendo '{caminho_sobrevida_csv}' em lotes de {chunk_size} linhas...")

    try:
        csv_iterator = pd.read_csv(caminho_sobrevida_csv, sep=';', dtype=str, chunksize=chunk_size)

        for i, chunk in enumerate(csv_iterator):
            print(f"  -> Processando lote {i+1}...")
            if i == 0:
                if 'populacao' not in chunk.columns or 'UF' not in chunk.columns:
                    raise KeyError("As colunas 'populacao' e 'UF' são necessárias.")

            if 'CODMUNRES_6DIG' in chunk.columns:
                if 'CODMUNRES' in chunk.columns: chunk = chunk.drop(columns=['CODMUNRES'])
                chunk.rename(columns={'CODMUNRES_6DIG': 'CODMUNRES'}, inplace=True)

            chunk['CODMUNRES'] = chunk['CODMUNRES'].astype(str).str[:6]
            df_final_chunk = pd.merge(chunk, df_contexto, on='CODMUNRES', how='left')

            df_final_chunk['populacao'] = pd.to_numeric(df_final_chunk['populacao'], errors='coerce')
            df_final_chunk['DENSIDADE_UBS_10K'] = (df_final_chunk['N_UBS'] / df_final_chunk['populacao'] * 10000).fillna(0)

            processed_chunks.append(df_final_chunk)

    except (FileNotFoundError, KeyError) as e:
        print(f"❌ ERRO: {e}. Verifique o caminho e o conteúdo do arquivo CSV de sobrevida."); return None

    if not processed_chunks:
        print("❌ ERRO: Nenhum dado pôde ser processado a partir do arquivo CSV."); return None

    print("[LOG] Consolidando todos os lotes processados...")
    df_final = pd.concat(processed_chunks, ignore_index=True)

    print("✅ Dados de sobrevida enriquecidos com IVS e densidade de UBS.")
    df_final = otimizar_memoria(df_final)

    return df_final

def treinar_modelo_geografico(df: pd.DataFrame, dir_saida: Path):
    """Treina um modelo incluindo as features contextuais, com tratamento robusto de nulos."""
    print("\n--- [ETAPA 3] Treinando Modelo de Risco Geográfico ---")
    features_modelo = [
        'PESO', 'GESTACAO', 'APGAR5', 'CONSPRENAT', 'IDADEMAE', 'ESCMAE2010', 'RACACORMAE',
        'QTLEIT39', 'ATIVIDAD', 'ivs', 'DENSIDADE_UBS_10K'
    ]
    cols_para_manter = [col for col in features_modelo if col in df.columns] + ['OBITO_INFANTIL', 'CODMUNRES', 'UF']
    df_modelo = df[cols_para_manter].copy()

    for col in features_modelo:
        if col in df_modelo.columns: df_modelo[col] = pd.to_numeric(df_modelo[col], errors='coerce')

    if 'ivs' in df_modelo.columns:
        ivs_median = df_modelo['ivs'].median()
        df_modelo['ivs'].fillna(ivs_median, inplace=True)
        print(f"[LOG] Valores nulos em 'ivs' imputados com a mediana ({ivs_median:.4f}).")

    if 'DENSIDADE_UBS_10K' in df_modelo.columns:
        densidade_median = df_modelo['DENSIDADE_UBS_10K'].median()
        df_modelo['DENSIDADE_UBS_10K'].fillna(densidade_median, inplace=True)
        print(f"[LOG] Valores nulos em 'DENSIDADE_UBS_10K' imputados com a mediana ({densidade_median:.4f}).")

    colunas_clinicas_essenciais = ['PESO', 'GESTACAO', 'APGAR5', 'IDADEMAE', 'CONSPRENAT']
    initial_rows = len(df_modelo)
    df_limpo = df_modelo.dropna(subset=[col for col in colunas_clinicas_essenciais if col in df_modelo.columns])
    print(f"[LOG] {initial_rows - len(df_limpo)} registros removidos devido a valores ausentes em features clínicas essenciais.")

    y = df_limpo['OBITO_INFANTIL'].astype(int)
    cols_para_dropar = [col for col in ['OBITO_INFANTIL', 'CODMUNRES', 'UF'] if col in df_limpo.columns]
    X = df_limpo.drop(columns=cols_para_dropar)

    if X.empty or y.nunique() < 2: print("❌ Dados insuficientes para treinamento."); return None, None

    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.3, random_state=42, stratify=y)

    counts = y_train.value_counts()
    if 0 not in counts or 1 not in counts: print("❌ Erro: O conjunto de treino não contém ambas as classes."); return None, None
    ratio = counts.loc[0] / counts.loc[1]

    modelo = lgb.LGBMClassifier(objective='binary', random_state=42, scale_pos_weight=ratio)
    modelo.fit(X_train, y_train)
    print("✅ Modelo treinado com sucesso.")

    df_com_predicao = df.loc[X_test.index].copy()
    df_com_predicao['RISCO_PREVISTO_OBITO'] = modelo.predict_proba(X_test)[:, 1]

    print("[LOG] Calculando os valores SHAP..."); explainer = shap.TreeExplainer(modelo); shap_values = explainer.shap_values(X_test)
    mapa_rotulos = {
        'PESO': 'Peso ao Nascer (g)', 'GESTACAO': 'Semanas de Gestação', 'APGAR5': 'Apgar (5º Min)',
        'CONSPRENAT': 'Nº Consultas Pré-Natal', 'IDADEMAE': 'Idade da Mãe', 'ESCMAE2010': 'Escolaridade da Mãe',
        'RACACORMAE': 'Raça/Cor da Mãe', 'QTLEIT39': 'Leitos UTI Neonatal (Hospital)',
        'ATIVIDAD': 'Hospital de Ensino', 'ivs': 'Índice de Vulnerabilidade Social (IVS)',
        'DENSIDADE_UBS_10K': 'UBS por 10k Hab (Município)'
    }
    X_test_renomeado = X_test.rename(columns=mapa_rotulos)
    if isinstance(shap_values, list): shap_values_risk = shap_values[1]
    else: shap_values_risk = shap_values
    plt.figure(); shap.summary_plot(shap_values_risk, X_test_renomeado, plot_type="bar", show=False)
    plt.title("Impacto Médio dos Fatores no Risco de Óbito (SHAP)"); plt.tight_layout()
    caminho_fig = dir_saida / "feature_importance_geografico.png"; plt.savefig(caminho_fig, dpi=150, bbox_inches='tight'); plt.close()
    print(f"📈 Gráfico SHAP de barras salvo em: {caminho_fig}")

    # Salva o DataFrame completo df_limpo (com features e alvo) para a análise causal.
    cols_to_save_for_causal = features_modelo + ['OBITO_INFANTIL', 'CODMUNRES', 'UF']
    cols_to_save_for_causal = [col for col in cols_to_save_for_causal if col in df_limpo.columns]

    caminho_csv_analise_causal = dir_saida / "dados_para_analise_causal.csv"
    df_limpo[cols_to_save_for_causal].to_csv(caminho_csv_analise_causal, index=False, sep=';', encoding='utf-8-sig')
    print(f"📄 Dados completos para análise causal salvos em: '{caminho_csv_analise_causal}'")

    return df_com_predicao, modelo

def gerar_mapa_de_risco(df_risco: pd.DataFrame, uf: str, caminho_shapefile: Path, dir_saida: Path):
    # (Esta função permanece a mesma da versão anterior, sem alterações)
    print(f"\n--- [ETAPA 4] Gerando Mapa de Risco para {uf} ---")
    try:
        gdf = gpd.read_file(caminho_shapefile)
        gdf_uf = gdf[gdf['SIGLA_UF'] == uf].copy()

        risco_por_municipio = df_risco.groupby('CODMUNRES')['RISCO_PREVISTO_OBITO'].mean().reset_index()

        gdf_uf['CD_MUN_6DIG'] = gdf_uf['CD_MUN'].astype(str).str[:6]
        risco_por_municipio['CODMUNRES'] = risco_por_municipio['CODMUNRES'].astype(str).str[:6]

        gdf_mapeado = gdf_uf.merge(risco_por_municipio, left_on='CD_MUN_6DIG', right_on='CODMUNRES', how='left')

        gdf_mapeado['RISCO_PREVISTO_OBITO'] = gdf_mapeado['RISCO_PREVISTO_OBITO'].fillna(0)

        fig, ax = plt.subplots(1, 1, figsize=(12, 12))
        gdf_mapeado.plot(column='RISCO_PREVISTO_OBITO', cmap='YlOrRd', linewidth=0.5, ax=ax, edgecolor='0.8',
                         legend=True, legend_kwds={'label': "Risco Previsto de Óbito Infantil (Probabilidade Média)"})
        ax.axis('off'); ax.set_title(f'Mapa de Risco de Mortalidade Infantil - {uf}', fontsize=16)
        caminho_mapa = dir_saida / f"mapa_risco_{uf.lower()}.png"
        plt.savefig(caminho_mapa, dpi=150, bbox_inches='tight'); plt.close()
        print(f"🗺️ Mapa de risco salvo em: {caminho_mapa}")
    except Exception as e:
        print(f"❌ Erro ao gerar o mapa: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Executa o pipeline de análise de risco geográfico da mortalidade infantil.")
    parser.add_argument("--sobrevida-csv", type=str, required=True, help="Caminho para o CSV gerado por 'analise_sobrevida_infantil.py'.")
    parser.add_argument("--ivs-dir", type=str, default="referencia/ipea", help="Caminho para o DIRETÓRIO contendo os arquivos CSV do IVS por estado.")
    parser.add_argument("--shapefile", type=str, required=True, help="Caminho para o arquivo .shp dos municípios do Brasil.")
    parser.add_argument("--ufs", nargs="+", default=["TO"], help="Lista de UFs a processar.")
    parser.add_argument("--ano", type=int, default=2022, help="Ano da coorte de nascimentos a ser analisada.")
    parser.add_argument("--dir_saida", type=str, default="outputs/risco_geografico", help="Diretório para salvar os resultados.")
    args = parser.parse_args()

    output_dir = Path(args.dir_saida)
    output_dir.mkdir(parents=True, exist_ok=True)

    df_contexto = carregar_dados_contextuais(Path(args.ivs_dir), args.ufs, args.ano)
    if df_contexto is not None:
        df_final_para_modelo = preparar_dados_finais(Path(args.sobrevida_csv), df_contexto)
        if df_final_para_modelo is not None and not df_final_para_modelo.empty:

            # ==========================================================
            # --- ADIÇÃO PARA SALVAR O CSV FINAL ---
            # ==========================================================
            ufs_str = '-'.join(args.ufs).lower()
            nome_arquivo = f"painel_geografico_sobrevida_{ufs_str}_{args.ano}.csv"
            caminho_csv = output_dir / nome_arquivo

            df_final_para_modelo.to_csv(caminho_csv, index=False, sep=';', encoding='utf-8-sig')
            print(f"\n📄 Painel de dados geográfico final salvo em: '{caminho_csv}'")
            # ==========================================================

            df_com_predicao, modelo = treinar_modelo_geografico(df_final_para_modelo, output_dir)
            if df_com_predicao is not None:
                for uf_selecionada in args.ufs:
                    gerar_mapa_de_risco(df_com_predicao[df_com_predicao['UF'] == uf_selecionada], uf_selecionada, Path(args.shapefile), output_dir)
                print("\n" + "="*80); print("🎉 PIPELINE CONCLUÍDO! 🎉"); print("="*80)

