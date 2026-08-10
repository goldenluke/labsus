# -*- coding: utf-8 -*-
"""
======================================================================
  PIPELINE OTIMIZADO DE ANÁLISE DE JORNADAS DE PACIENTES CRÔNICOS
======================================================================
Este script implementa um pipeline de dados para:
1. Criar identificadores de paciente para SIH e SIA.
2. Identificar uma coorte de pacientes com uma doença crônica específica.
3. Coletar o histórico completo de atendimentos de cada paciente.
4. Treinar um modelo para prever uma futura hospitalização.

Versão otimizada para computadores com recursos limitados de RAM e CPU.
Os dados otimizados são armazenados localmente para evitar downloads e
reprocessamentos desnecessários.
"""

import pandas as pd
import numpy as np
from pathlib import Path
import argparse
from datetime import datetime

from pysus.online_data.SIH import SIH
from pysus.online_data.SIA import SIA

from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, roc_auc_score
import lightgbm as lgb
import shap
import matplotlib.pyplot as plt
import joblib

FEATURE_NAMES = ['N_INTERNACOES_12M', 'TOTAL_DIAS_PERM_12M', 'N_CONSULTAS_AMB_12M', 'IDADE']

# --- FUNÇÃO DE OTIMIZAÇÃO DE MEMÓRIA ---
def otimizar_memoria(df: pd.DataFrame) -> pd.DataFrame:
    """
    Percorre todas as colunas de um DataFrame e modifica o tipo de dados
    para minimizar o uso de memória.
    """
    print(f"   -> Otimizando uso de memória... Shape: {df.shape}")
    memoria_antes = df.memory_usage(deep=True).sum() / 1024**2

    for col in df.columns:
        # Lista de colunas que devem ser mantidas como 'object' (string) se forem strings
        # para evitar que códigos como CID virem números e quebrem operações .str
        cols_to_preserve_as_object = [
            'DIAG_PRINC', 'DIAG_SECUN', 'CAUSABAS', # SIH CIDs
            'PA_CIDPRI', 'PA_CIDSEC', 'PA_CIDCAS', # SIA CIDs
            'CNES', 'CODESTAB', 'PA_CODUNI', # Códigos de estabelecimento
            'CODMUNRES', 'PA_MUNPCN', 'MUNIC_RES', 'MUNIC_MOV', # Códigos de município
            'PROC_REA', 'PA_PROC_ID', # Códigos de procedimento
            'SEXO', 'CS_SEXO', 'PA_SEXO', # Códigos de sexo
            'RACA_COR', 'CS_RACA', 'PA_RACACOR', # Códigos de raça
            'CAR_INT', 'PA_CATEND', # Códigos de caráter da internação
            'TP_UNID', 'PA_TPUPS', # Tipos de unidade
            'NAT_JUR', 'PA_NAT_JUR', # Natureza jurídica
            'ATIVIDAD', 'PA_DOCORIG' # Atividades, documento de origem
        ]

        if col in cols_to_preserve_as_object:
            # Se for uma coluna que precisa ser string, garante que seja e pula otimização numérica
            if df[col].dtype != object:
                df[col] = df[col].astype(str)
            continue # Pula para a próxima coluna

        # Tenta converter a coluna para numérico primeiro, tratando erros.
        df_col = pd.to_numeric(df[col], errors='coerce')

        # Só prossegue com a otimização se a coluna for majoritariamente numérica
        if not df_col.isnull().all():
            col_type = df_col.dtype

            if col_type != object and col_type.name != 'category' and 'datetime' not in str(col_type):
                c_min = df_col.min(); c_max = df_col.max()
                if str(col_type)[:3] == 'int' or str(col_type)[:4] == 'uint':
                    if c_min > np.iinfo(np.int8).min and c_max < np.iinfo(np.int8).max: df[col] = df_col.astype(np.int8)
                    elif c_min > np.iinfo(np.int16).min and c_max < np.iinfo(np.int16).max: df[col] = df_col.astype(np.int16)
                    elif c_min > np.iinfo(np.int32).min and c_max < np.iinfo(np.int32).max: df[col] = df_col.astype(np.int32)
                    elif c_min > np.iinfo(np.int64).min and c_max < np.iinfo(np.int64).max: df[col] = df_col.astype(np.int64)
                else: # float
                    if c_min > np.finfo(np.float32).min and c_max < np.finfo(np.float32).max: df[col] = df_col.astype(np.float32)
                    else: df[col] = df_col.astype(np.float64)

    memoria_depois = df.memory_usage(deep=True).sum() / 1024**2
    print(f"      -> Uso de memória: {memoria_antes:.2f} MB -> {memoria_depois:.2f} MB (Redução de {100 * (memoria_antes - memoria_depois) / memoria_antes:.1f}%)")
    return df

def carregar_dados(ufs: list, anos: list, optimized_data_dir: Path, force_download: bool = False):
    """
    Carrega, otimiza e armazena/recupera múltiplos anos de dados do SIH e SIA.
    """
    print(f"\n--- [ETAPA 1] Carregando dados históricos para {ufs} / Anos: {anos} ---")

    optimized_data_dir.mkdir(exist_ok=True, parents=True)
    ufs_str = '_'.join(ufs).lower()
    anos_str = '_'.join(map(str, anos))
    sih_optimized_path = optimized_data_dir / f"sih_optimized_{ufs_str}_{anos_str}.parquet"
    sia_optimized_path = optimized_data_dir / f"sia_optimized_{ufs_str}_{anos_str}.parquet"

    # --- Tentar carregar dados otimizados se existirem e não forçar download ---
    if not force_download and sih_optimized_path.exists() and sia_optimized_path.exists():
        print(f"[LOG] Carregando dados otimizados existentes de: {optimized_data_dir.name}/")
        try:
            df_sih = pd.read_parquet(sih_optimized_path)
            df_sia = pd.read_parquet(sia_optimized_path)
            print("✅ Dados otimizados carregados com sucesso.")
            return df_sih, df_sia
        except Exception as e:
            print(f"❌ Erro ao carregar arquivos otimizados, forçando novo download: {e}")
            force_download = True

    # --- Se não existirem ou forçar download, proceder com download e otimização ---
    df_sih, df_sia = pd.DataFrame(), pd.DataFrame()

    print("[LOG] Iniciando download e otimização de dados do SIH...")
    try:
        sih_db = SIH().load(); files_sih = sih_db.get_files(group='RD', uf=ufs, year=anos)
        if files_sih:
            df_sih = pd.concat([p.to_dataframe() for p in sih_db.download(files_sih)], ignore_index=True)
            df_sih = otimizar_memoria(df_sih)
            df_sih.to_parquet(sih_optimized_path, index=False) # Salva o otimizado
            print(f"✅ SIH otimizado salvo em: {sih_optimized_path}")
    except Exception as e: print(f"❌ Erro ao carregar SIH: {e}"); return None, None

    print("[LOG] Iniciando download e otimização de dados do SIA...")
    try:
        sia_db = SIA().load(); files_sia = sia_db.get_files(group='PA', uf=ufs, year=anos)
        if files_sia:
            df_sia = pd.concat([p.to_dataframe() for p in sia_db.download(files_sia)], ignore_index=True)
            df_sia = otimizar_memoria(df_sia)
            df_sia.to_parquet(sia_optimized_path, index=False) # Salva o otimizado
            print(f"✅ SIA otimizado salvo em: {sia_optimized_path}")
    except Exception as e: print(f"❌ Erro ao carregar SIA: {e}"); return None, None

    if df_sih.empty or df_sia.empty:
        print("❌ Aviso: Uma ou ambas as bases de dados não puderam ser carregadas/otimizadas."); return None, None

    print(f"✅ Dados carregados e otimizados.")
    return df_sih, df_sia

def criar_ids_de_paciente(df_sih: pd.DataFrame, df_sia: pd.DataFrame):
    """
    Cria uma coluna 'ID_PACIENTE' em cada DataFrame usando um pseudo-ID
    demográfico consistente, baseado nas colunas disponíveis.
    """
    print("\n--- [ETAPA 1.5] Criando Identificadores de Paciente ---")

    # Cria o pseudo-ID para o SIH
    df_sih['ID_PACIENTE'] = df_sih['NASC'].astype(str) + '_' + df_sih['SEXO'].astype(str) + '_' + df_sih['MUNIC_RES'].astype(str)

    # Cria um pseudo-ID análogo para o SIA usando PA_IDADE.
    # Certifica-se que PA_DOCORIG, PA_IDADE, PA_SEXO e PA_MUNPCN são strings antes de usar
    required_sia_cols = ['PA_DOCORIG', 'PA_IDADE', 'PA_SEXO', 'PA_MUNPCN', 'PA_CMP']
    if not all(col in df_sia.columns for col in required_sia_cols):
        print(f"❌ Erro: Colunas SIA necessárias para pseudo-ID não encontradas: {set(required_sia_cols) - set(df_sia.columns)}")
        # Cria IDs vazios para não quebrar, mas com aviso grave.
        df_sia['ID_PACIENTE'] = np.nan
    else:
        df_sia_ind = df_sia[df_sia['PA_DOCORIG'].isin(['I', 'P', 'S', 'A', 'R'])].copy()

        # Converte as colunas para string antes da operação de concatenação
        df_sia_ind['ANO_ATENDIMENTO'] = pd.to_datetime(df_sia_ind['PA_CMP'], format='%Y%m', errors='coerce').dt.year
        df_sia_ind['ANO_NASC_APROX'] = df_sia_ind['ANO_ATENDIMENTO'] - pd.to_numeric(df_sia_ind['PA_IDADE'], errors='coerce')

        df_sia_ind['ID_PACIENTE'] = (
            df_sia_ind['ANO_NASC_APROX'].astype(str) + '_' +
            df_sia_ind['PA_SEXO'].astype(str) + '_' +
            df_sia_ind['PA_MUNPCN'].astype(str)
        )

        df_sia = df_sia.merge(df_sia_ind[['ID_PACIENTE']], left_index=True, right_index=True, how='left')

    df_sih.dropna(subset=['ID_PACIENTE'], inplace=True)
    df_sia.dropna(subset=['ID_PACIENTE'], inplace=True)

    print("✅ Coluna 'ID_PACIENTE' criada e padronizada em ambas as bases.")
    return df_sih, df_sia

def construir_dataset_longitudinal(df_sih: pd.DataFrame, df_sia: pd.DataFrame, cid_doenca: str, ano_snapshot: int):
    """Identifica a coorte e constrói o dataset com features de janela de tempo."""
    print(f"\n--- [ETAPA 2] Construindo Dataset Longitudinal para CID '{cid_doenca}' ---")

    print("[LOG] Identificando coorte de pacientes com o diagnóstico...")
    # Filtra os dataframes ANTES de fazer operações de string e set()
    df_sih_filtrado = df_sih.dropna(subset=['DIAG_PRINC', 'ID_PACIENTE'])
    df_sia_filtrado = df_sia.dropna(subset=['PA_CIDPRI', 'ID_PACIENTE'])

    pacientes_sih = set(df_sih_filtrado[df_sih_filtrado['DIAG_PRINC'].astype(str).str.startswith(cid_doenca, na=False)]['ID_PACIENTE'])
    pacientes_sia = set(df_sia_filtrado[df_sia_filtrado['PA_CIDPRI'].astype(str).str.startswith(cid_doenca, na=False)]['ID_PACIENTE'])

    pacientes_coorte = pacientes_sih | pacientes_sia
    print(f"  -> Coorte identificada: {len(pacientes_coorte)} pacientes únicos.")

    if not pacientes_coorte:
        print("  -> Nenhuma paciente encontrado para a coorte. Abortando.")
        return pd.DataFrame()

    print("[LOG] Preparando dados para análise temporal...")
    df_sih['DATA'] = pd.to_datetime(df_sih['DT_INTER'], format='%Y%m%d', errors='coerce')
    df_sia['DATA'] = pd.to_datetime(df_sia['PA_CMP'], format='%Y%m', errors='coerce')
    df_sih_coorte = df_sih[df_sih['ID_PACIENTE'].isin(pacientes_coorte)].dropna(subset=['DATA'])
    df_sia_coorte = df_sia[df_sia['ID_PACIENTE'].isin(pacientes_coorte)].dropna(subset=['DATA'])

    print(f"[LOG] Gerando features e alvo para o snapshot em {ano_snapshot}-01-01...")
    snapshot_date = pd.to_datetime(f"{ano_snapshot}-01-01")
    history_start_date = snapshot_date - pd.DateOffset(months=12)
    future_end_date = snapshot_date + pd.DateOffset(months=6)

    lista_pacientes_features = []
    for paciente_id in pacientes_coorte:
        hist_sih = df_sih_coorte[(df_sih_coorte['ID_PACIENTE'] == paciente_id) & (df_sih_coorte['DATA'] >= history_start_date) & (df_sih_coorte['DATA'] < snapshot_date)]
        hist_sia = df_sia_coorte[(df_sia_coorte['ID_PACIENTE'] == paciente_id) & (df_sia_coorte['DATA'] >= history_start_date) & (df_sia_coorte['DATA'] < snapshot_date)]

        if hist_sih.empty and hist_sia.empty: continue

        # Tenta obter a idade mais recente e válida
        idade_sih = pd.to_numeric(hist_sih['IDADE'], errors='coerce')
        idade_sia = pd.to_numeric(hist_sia['PA_IDADE'], errors='coerce')

        idade = np.nan
        if not idade_sih.empty and idade_sih.max() is not np.nan:
            idade = idade_sih.max()
        elif not idade_sia.empty and idade_sia.max() is not np.nan:
            idade = idade_sia.max()

        features = {
            'ID_PACIENTE': paciente_id,
            'N_INTERNACOES_12M': len(hist_sih),
            'TOTAL_DIAS_PERM_12M': pd.to_numeric(hist_sih['DIAS_PERM'], errors='coerce').sum(),
            'N_CONSULTAS_AMB_12M': len(hist_sia),
            'IDADE': idade
        }

        futuro_sih = df_sih_coorte[(df_sih_coorte['ID_PACIENTE'] == paciente_id) & (df_sih_coorte['DATA'] >= snapshot_date) & (df_sih_coorte['DATA'] < future_end_date)]
        features['ALVO_HOSPITALIZADO_6M'] = 1 if not futuro_sih.empty else 0

        lista_pacientes_features.append(features)

    df_analitico = pd.DataFrame(lista_pacientes_features)
    print(f"✅ Dataset analítico criado com {len(df_analitico)} pacientes-ano.")
    return df_analitico


def treinar_e_avaliar_modelo_cronicos(df: pd.DataFrame, dir_saida: Path):
    """Treina e avalia um modelo para prever hospitalização de pacientes crônicos."""
    print("\n--- [ETAPA 3] Treinamento do Modelo Preditivo ---")
    dir_saida.mkdir(parents=True, exist_ok=True)
    df.dropna(subset=['IDADE'], inplace=True)
    y = df['ALVO_HOSPITALIZADO_6M']
    X = df.drop(columns=['ID_PACIENTE', 'ALVO_HOSPITALIZADO_6M'])
    if X.empty or y.nunique() < 2: print("❌ Dados insuficientes para treinamento."); return
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.3, random_state=42, stratify=y)
    if y_train.value_counts().get(1, 0) == 0: print("❌ Erro: Não há amostras da classe positiva no conjunto de treino."); return
    counts = y_train.value_counts()
    if 0 not in counts or 1 not in counts: print("❌ Erro: O conjunto de treino não contém ambas as classes."); return
    ratio = counts.loc[0] / counts.loc[1]
    modelo = lgb.LGBMClassifier(objective='binary', random_state=42, scale_pos_weight=ratio)
    print("[LOG] Treinando o modelo LightGBM...")
    modelo.fit(X_train, y_train)
    print("✅ Modelo treinado com sucesso.")
    y_pred_proba = modelo.predict_proba(X_test)[:, 1]
    auc = roc_auc_score(y_test, y_pred_proba)
    print(f"\n--- Performance do Modelo ---"); print(f"Área sob a Curva ROC (AUC): {auc:.4f}")

    caminho_modelo = dir_saida / "modelo_doencas_cronicas.joblib"
    joblib.dump({'model': modelo, 'feature_names': list(X.columns), 'auc': auc}, caminho_modelo)
    print(f"💾 Modelo salvo em: {caminho_modelo}")

    explainer = shap.TreeExplainer(modelo)
    shap_values = explainer.shap_values(X_test)
    if isinstance(shap_values, list):
        shap_values = shap_values[1]
    plt.figure()
    shap.summary_plot(shap_values, X_test, plot_type="bar", show=False)
    plt.title("Fatores Preditivos para Futura Hospitalização")
    plt.tight_layout()
    caminho_fig = dir_saida / "feature_importance_cronicos.png"
    plt.savefig(caminho_fig, dpi=150, bbox_inches='tight'); plt.close()
    print(f"📈 Gráfico SHAP salvo em: {caminho_fig}")

    return modelo


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Executa o pipeline de análise de jornadas de pacientes crônicos.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )

    parser.add_argument("--ufs", nargs="+", default=["TO"], help="Lista de UFs a processar.")
    parser.add_argument("--anos", nargs="+", type=int, default=[2024, 2023, 2022], help="Anos de dados históricos a usar para construir as jornadas.")
    parser.add_argument("--ano_snapshot", type=int, default=2025, help="Ano PARA o qual a previsão será feita. O histórico será os 12 meses ANTES deste ano.")
    parser.add_argument("--cid", type=str, default="I50", help="CID-10 da doença crônica a ser analisada.")
    parser.add_argument("--dir_saida", type=str, default="outputs/analise_cronicos", help="Diretório para salvar os resultados.")
    parser.add_argument("--force_download", action='store_true', help="Força o download e re-otimização dos dados, mesmo que já existam arquivos otimizados.")

    args = parser.parse_args()

    ano_historico_necessario = args.ano_snapshot - 1
    if ano_historico_necessario not in args.anos:
        print("\n" + "="*80); print("❌ ERRO DE CONFIGURAÇÃO LÓGICA ❌"); print(f"Para fazer uma previsão para o ano {args.ano_snapshot}, o script precisa dos dados do ano anterior ({ano_historico_necessario})."); print(f"Você forneceu os anos: {args.anos}."); print("="*80)
        exit()

    df_sih_raw, df_sia_raw = carregar_dados(
        ufs=args.ufs,
        anos=args.anos,
        optimized_data_dir=Path('dados_otimizados'),
        force_download=args.force_download
    )

    if df_sih_raw is not None and df_sia_raw is not None:
        df_sih_linked, df_sia_linked = criar_ids_de_paciente(df_sih_raw, df_sia_raw)
        df_analitico = construir_dataset_longitudinal(df_sih_linked, df_sia_linked, args.cid, args.ano_snapshot)
        if df_analitico is not None and not df_analitico.empty:
            treinar_e_avaliar_modelo_cronicos(df_analitico, Path(args.dir_saida))
            print("\n" + "="*80)
            print("🎉 PIPELINE DE ANÁLISE DE DOENÇAS CRÔNICAS CONCLUÍDO! 🎉")
            print("="*80)
